import hashlib
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
import httpx
import fitz  # PyMuPDF
from ..config import logger, FORMS_CACHE_DIR, FILLED_FORMS_DIR, CONFIG, IS_REMOTE, IS_CLOUD, DEDUPE_FILE
from ..models import FormType
from .loop_protector import LoopProtector
from .file_sync import RemoteFileSyncManager

_protector = LoopProtector(DEDUPE_FILE)
_file_sync = RemoteFileSyncManager()

def detect_form_type(form_name: str) -> FormType:
    """Detect form type from name"""
    name_lower = form_name.lower()
    
    if any(word in name_lower for word in ["antrag", "application"]):
        return FormType.APPLICATION
    elif any(word in name_lower for word in ["bescheinigung", "nachweis", "certificate"]):
        return FormType.CERTIFICATE
    elif any(word in name_lower for word in ["hinweis", "merkblatt", "information", "info"]):
        return FormType.INFORMATION
    elif any(word in name_lower for word in ["verdienst", "einkommen", "income"]):
        return FormType.INCOME_PROOF
    elif any(word in name_lower for word in ["checkliste", "checklist", "liste"]):
        return FormType.CHECKLIST
    elif any(word in name_lower for word in ["extrablatt", "anlage", "supplement"]):
        return FormType.SUPPORTING_DOC
    
    return FormType.UNKNOWN

async def analyze_form_for_filling_logic(form_url: str) -> Dict[str, Any]:
    """Internal logic for PDF analysis."""
    try:
        url_hash = hashlib.md5(form_url.encode()).hexdigest()
        local_path = FORMS_CACHE_DIR / f"{url_hash}.pdf"
        
        if not local_path.exists():
            logger.info(f"Downloading form for analysis: {form_url}")
            async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
                response = await client.get(form_url)
                response.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(response.content)
        
        doc = fitz.open(str(local_path))
        extracted_fields = []
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            for widget in page.widgets():
                extracted_fields.append({
                    "name": widget.field_name,
                    "type": widget.field_type_string,
                    "value": widget.field_value,
                    "label": widget.field_label or widget.field_name,
                    "page": page_num + 1
                })
        
        doc.close()
        
        if not extracted_fields:
            return {
                "success": False,
                "error": "No fillable fields found in this PDF.",
                "local_path": str(local_path)
            }
            
        return {
            "success": True,
            "form_url": form_url,
            "total_fields": len(extracted_fields),
            "fields": extracted_fields,
            "instructions": "Please ask the user for data for these fields. Use the 'name' key when calling perform_form_filling."
        }
        
    except Exception as e:
        logger.error(f"Analyze form error (fitz): {e}")
        return {"success": False, "error": str(e)}

async def perform_form_filling_logic(
    form_url: str, 
    field_data: Dict[str, str], 
    output_filename: Optional[str] = None,
    flatten: bool = False,
    force_recompute: bool = False
) -> Dict[str, Any]:
    """Highly optimized PDF filling with O(1) lookups and persistent loop protection."""
    
    data_str = json.dumps(field_data, sort_keys=True)
    request_key = hashlib.md5(f"{form_url}:{data_str}".encode()).hexdigest()
    
    lookup = _protector.check(request_key)
    if lookup and not force_recompute:
        last_path, last_file_id = lookup
        logger.info(f"Deduplication triggered for {request_key}. Stopping loop.")
        filename = Path(last_path).name
        instructions = "The task is ALREADY finished. "
        if IS_REMOTE:
            instructions += (
                f"Access the previous result via 'berlin://files/sync/{last_file_id}' "
                f"or 'berlin://forms/{filename}'. "
            )
        else:
            instructions += f"Document is already at {last_path}."

        return {
            "success": True,
            "status": "ALREADY_COMPLETED",
            "message": "Form was already filled. Skipping re-execution to prevent tool loop.",
            "saved_path": last_path,
            "filename": filename,
            "file_id": last_file_id,
            "instructions": instructions + " DO NOT run this tool again.",
            "sync_resource": f"berlin://files/sync/{last_file_id}" if IS_REMOTE else None
        }

    telemetry = {}
    total_start = datetime.now()
    
    if not field_data:
        return {"success": False, "error": "No field data provided."}

    try:
        step_start = datetime.now()
        url_hash = hashlib.md5(form_url.encode()).hexdigest()
        input_path = FORMS_CACHE_DIR / f"{url_hash}.pdf"
        
        if not input_path.exists():
            logger.info(f"Downloading PDF from {form_url}")
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(form_url)
                response.raise_for_status()
                with open(input_path, "wb") as f:
                    f.write(response.content)
            telemetry["download_ms"] = round((datetime.now() - step_start).total_seconds() * 1000, 2)
        else:
            telemetry["cache_hit"] = True
            telemetry["download_ms"] = 0
                    
        if not output_filename:
            output_filename = f"filled_{datetime.now().strftime('%H%M%S')}.pdf"
        if not output_filename.endswith(".pdf"):
            output_filename += ".pdf"
        final_output_path = FILLED_FORMS_DIR / output_filename
        
        step_start = datetime.now()
        doc = fitz.open(str(input_path))
        telemetry["open_ms"] = round((datetime.now() - step_start).total_seconds() * 1000, 2)
        
        step_start = datetime.now()
        widgets = []
        widget_map = {}
        for page in doc:
            for widget in page.widgets():
                if widget.field_name:
                    widgets.append(widget)
                    widget_map[widget.field_name] = widget
        telemetry["index_ms"] = round((datetime.now() - step_start).total_seconds() * 1000, 2)
        
        filled_count = 0
        unmatched_keys = set(field_data.keys())
        matched_fields_info = {}
        
        step_start_phase = datetime.now()
        for key in list(unmatched_keys):
            if key in widget_map:
                w = widget_map[key]
                val = str(field_data[key])
                if w.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                    w.field_value = "Yes" if val.lower() in ['yes', 'true', '1', 'on', 'x'] else "Off"
                else:
                    w.field_value = val
                w.update()
                filled_count += 1
                unmatched_keys.discard(key)
                matched_fields_info[key] = w.field_name
        
        if unmatched_keys:
            COMMON_MAPPINGS = {
                "männlich": ["geschlecht"], "weiblich": ["geschlecht"], "divers": ["geschlecht"],
                "ledig": ["familienstand"], "einzugsdatum": ["tag des einzugs"],
                "postleitzahl": ["plz", "postleitzahl"], "straße": ["strasse", "straße"],
            }
            for key in list(unmatched_keys):
                k_low = key.lower()
                found_match = False
                for w in widgets:
                    name_low = w.field_name.lower()
                    label_low = (w.field_label or "").lower()
                    if k_low in name_low or k_low in label_low:
                        found_match = True
                    elif k_low in COMMON_MAPPINGS:
                        for frag in COMMON_MAPPINGS[k_low]:
                            if frag in name_low or frag in label_low:
                                found_match = True; break
                    
                    if found_match:
                        val = str(field_data[key])
                        if w.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                            is_checked = val.lower() in ['yes', 'true', 'x'] or val.lower() in name_low
                            w.field_value = "Yes" if is_checked else "Off"
                        else:
                            w.field_value = val
                        w.update()
                        filled_count += 1
                        unmatched_keys.discard(key)
                        matched_fields_info[key] = w.field_name
                        break
        telemetry["match_fill_ms"] = round((datetime.now() - step_start_phase).total_seconds() * 1000, 2)

        step_start = datetime.now()
        doc.save(
            str(final_output_path), 
            appearance=CONFIG["appearance"], 
            incremental=False, 
            deflate=CONFIG["deflate"]
        )
        doc.close()
        telemetry["save_ms"] = round((datetime.now() - step_start).total_seconds() * 1000, 2)
        telemetry["total_ms"] = round((datetime.now() - total_start).total_seconds() * 1000, 2)
        
        file_size = final_output_path.stat().st_size
        file_id = hashlib.md5(f"{output_filename}:{total_start.isoformat()}".encode()).hexdigest()[:12]
        _file_sync.register_file(file_id, final_output_path, file_size)
        _protector.save(request_key, str(final_output_path.absolute()), file_id)
        
        instructions = " Form filling complete. "
        sync_resource = None
        
        if IS_REMOTE:
            sync_resource = f"berlin://files/sync/{file_id}"
            instructions = (
                f" REMOTE SERVER DETECTED!\n\n"
                f"1. Retrieve your file using logic: 'read_resource(\"{sync_resource}\")' or 'download_filled_form(filename=\"{output_filename}\")'.\n"
                f"2. IMPORTANT: After verifying the file, call 'delete_filled_form(filename=\"{output_filename}\")' to wipe sensitive data from the remote server."
            )
        else:
            instructions = (
                f" LOCAL SERVER DETECTED!\n\n"
                f"File saved to: {final_output_path.absolute()}\n"
                f" Run 'open_file_locally(file_path=\"{final_output_path.absolute()}\")' to open it now."
            )

        return {
            "success": filled_count > 0,
            "status": "COMPLETED",
            "message": f"Form filling process finished. {filled_count} fields matched and filled." if filled_count > 0 else "Form processed but no fields were matched.",
            "filename": output_filename,
            "saved_path": str(final_output_path.absolute()),
            "file_id": file_id,
            "field_mappings": matched_fields_info,
            "is_remote": IS_REMOTE,
            "telemetry": telemetry,
            "unmatched_fields": list(unmatched_keys),
            "instructions": instructions,
            "sync_resource": sync_resource
        }
        
    except Exception as e:
        logger.error(f"Critical form filling error: {e}")
        return {"success": False, "error": f"Internal error during form filling: {str(e)}"}

async def download_filled_form_logic(
    filename: str, 
    delete_after_read: Optional[bool] = None,
    only_preview: bool = False,
    ignore_size_limit: bool = False
) -> Dict[str, Any]:
    """Refined logic for downloading a filled form."""
    try:
        if delete_after_read is None:
            delete_after_read = IS_CLOUD
        
        if only_preview:
            delete_after_read = False
            
        safe_filename = Path(filename).name
        file_path = FILLED_FORMS_DIR / safe_filename
        
        if not file_path.exists():
            return {"success": False, "error": f"File '{filename}' not found on server."}
        
        file_size = file_path.stat().st_size
        
        if not IS_CLOUD and not IS_REMOTE:
            return {
                "success": True,
                "filename": safe_filename,
                "size_bytes": file_size,
                "saved_path": str(file_path.absolute()),
                "message": f"File '{safe_filename}' is available on your local system.",
                "instructions": f"Use 'open_file_locally(file_path=\"{file_path.absolute()}\")' to view it."
            }

        summary = {}
        try:
            doc = fitz.open(file_path)
            for page in doc:
                for widget in page.widgets():
                    if widget.field_value:
                        summary[widget.field_name] = widget.field_value
            doc.close()
        except: pass
        
        SAFE_THRESHOLD = 200 * 1024
        is_too_large = file_size > SAFE_THRESHOLD
        
        if is_too_large and not ignore_size_limit and not only_preview:
            return {
                "success": True,
                "filename": safe_filename,
                "size_bytes": file_size,
                "field_preview": summary,
                "warning": "FILE READY FOR DOWNLOAD",
                "message": f"File '{safe_filename}' is ready for retrieval.",
                "instructions": f"Use resource 'berlin://forms/{safe_filename}'"
            }

        with open(file_path, "rb") as f:
            file_bytes = f.read()
            encoded = base64.b64encode(file_bytes).decode('utf-8')
            
        if delete_after_read:
            file_path.unlink()
            
        response = {
            "success": True,
            "filename": safe_filename,
            "field_preview": summary,
            "size_bytes": file_size,
            "message": f"Successfully retrieved '{safe_filename}'."
        }

        if only_preview:
            response["instructions"] = "Preview only."
        else:
            response["content_base64"] = encoded
            response["instructions"] = "Decode 'content_base64' and save as .pdf."

        return response
    except Exception as e:
        logger.error(f"Download error: {e}")
        return {"success": False, "error": str(e)}

async def get_form_visual_preview_logic(filename: str, page_num: int = 0) -> Dict[str, Any]:
    """Renders PDF page to a HIGHLY COMPRESSED JPEG for safe chat preview."""
    try:
        safe_filename = Path(filename).name
        file_path = FILLED_FORMS_DIR / safe_filename
        
        if not file_path.exists():
            return {"success": False, "error": f"File '{filename}' not found."}
            
        doc = fitz.open(file_path)
        if page_num < 0 or page_num >= len(doc):
            total = len(doc)
            doc.close()
            return {"success": False, "error": f"Page index {page_num} out of range (0-{total-1})."}
            
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
        img_bytes = pix.tobytes("jpg", jpg_quality=75)
        total_pages = len(doc)
        doc.close()
        
        encoded = base64.b64encode(img_bytes).decode('utf-8')
        
        return {
            "success": True,
            "filename": safe_filename,
            "page": page_num + 1,
            "total_pages": total_pages,
            "image_base64": encoded,
            "format": "jpg",
            "size_bytes": len(img_bytes),
            "message": f"Rendered page {page_num + 1} of '{safe_filename}'."
        }
    except Exception as e:
        logger.error(f"Visual preview error: {e}")
        return {"success": False, "error": str(e)}

def get_file_sync_instance() -> RemoteFileSyncManager:
    return _file_sync
