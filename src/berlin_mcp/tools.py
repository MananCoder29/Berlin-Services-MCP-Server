import json
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path
from .server import mcp
from .config import logger, FILLED_FORMS_DIR, IS_CLOUD, HAS_OPEN_CMD
from .models import ServiceCategory, FormType
from .utils import expand_query
from .services.api_client import fetch_services_data, get_cache_instance
from .services.service_logic import categorize_service
from .services.form_logic import (
    analyze_form_for_filling_logic, 
    perform_form_filling_logic, 
    download_filled_form_logic, 
    get_form_visual_preview_logic,
    detect_form_type
)
import mcp.types as types

@mcp.tool()
async def search_services(
    query: str,
    page: int = 1,
    page_size: int = 20,
    category: Optional[str] = None,
    online_only: bool = False,
    has_forms: Optional[bool] = None
) -> Dict[str, Any]:
    """Advanced search for Berlin services with paging and filters."""
    try:
        page = max(1, min(page, 1000))
        page_size = max(1, min(page_size, 50))
        query = query.strip()
        
        if not query or len(query) < 2:
            return {"success": False, "error": "Query must be at least 2 characters"}
        
        data, source = await fetch_services_data()
        services = data.get("data", [])
        
        if category:
            try:
                cat = ServiceCategory[category.upper()]
                services = [s for s in services if categorize_service(s) == cat]
            except KeyError:
                pass
        
        if online_only:
            services = [s for s in services if s.get("onlineservices") or s.get("onlineprocessing")]
        
        if has_forms is not None:
            if has_forms:
                services = [s for s in services if s.get("forms")]
            else:
                services = [s for s in services if not s.get("forms")]
        
        search_terms = expand_query(query)
        matches = []
        for s in services:
            fields = [s.get("name", "").lower(), s.get("description", "").lower(), s.get("meta", {}).get("keywords", "").lower()]
            if all(any(term in field for field in fields) for term in search_terms):
                matches.append(s)
        
        if not matches and len(search_terms) > 1:
            for s in services:
                fields = [s.get("name", "").lower(), s.get("description", "").lower(), s.get("meta", {}).get("keywords", "").lower()]
                if any(any(term in field for field in fields) for term in search_terms):
                    matches.append(s)
                    
        total = len(matches)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = matches[start:end]
        
        return {
            "success": True,
            "query": query,
            "page": page,
            "page_size": page_size,
            "total_results": total,
            "has_next": end < total,
            "has_previous": page > 1,
            "data_source": source,
            "results": [
                {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "description": s.get("description", "")[:150],
                    "url": s.get("meta", {}).get("url"),
                    "category": categorize_service(s).value,
                    "has_online": bool(s.get("onlineservices")),
                    "fees": s.get("fees", "Not specified"),
                    "forms_count": len(s.get("forms", [])),
                    "has_prerequisites": bool(s.get("prerequisites"))
                }
                for s in page_items
            ]
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
async def get_service_details(service_id: str) -> Dict[str, Any]:
    """Get complete details about a service including forms and prerequisites."""
    try:
        data, source = await fetch_services_data()
        services = data.get("data", [])
        for service in services:
            if service.get("id") == service_id:
                return {
                    "success": True,
                    "data_source": source,
                    "service": {
                        "id": service.get("id"),
                        "name": service.get("name"),
                        "description": service.get("description"),
                        "category": categorize_service(service).value,
                        "url": service.get("meta", {}).get("url"),
                        "keywords": service.get("meta", {}).get("keywords"),
                        "last_updated": service.get("meta", {}).get("lastupdate"),
                        "requirements": service.get("requirements", []),
                        "prerequisites": service.get("prerequisites", []),
                        "fees": service.get("fees"),
                        "process_time": service.get("process_time"),
                        "forms": service.get("forms", []),
                        "forms_count": len(service.get("forms", [])),
                        "responsibility": service.get("responsibility"),
                        "online_processing": bool(service.get("onlineprocessing")),
                        "online_services": service.get("onlineservices", []),
                        "locations_count": len(service.get("locations", [])),
                        "authorities": service.get("authorities", []),
                        "links": service.get("links", []),
                        "legal_basis": service.get("legal", [])
                    }
                }
        return {"success": False, "error": f"Service {service_id} not found"}
    except Exception as e:
        logger.error(f"Get details error: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
async def get_service_forms(service_id: str, include_metadata: bool = True) -> Dict[str, Any]:
    """Get all forms associated with a service with detailed metadata."""
    try:
        data, source = await fetch_services_data()
        services = data.get("data", [])
        for service in services:
            if service.get("id") == service_id:
                forms = service.get("forms", [])
                if not forms:
                    return {"success": True, "service_id": service_id, "service_name": service.get("name"), "message": "No forms available", "forms": []}
                processed_forms = []
                for idx, form in enumerate(forms, 1):
                    form_data = {"position": idx, "name": form.get("name"), "download_link": form.get("link"), "has_description": bool(form.get("description")), "description": form.get("description")}
                    if include_metadata:
                        form_data["detected_type"] = detect_form_type(form.get("name", "")).value
                        form_data["is_pdf"] = form.get("link", "").lower().endswith(".pdf")
                        if form.get("link"):
                            form_data["filename"] = form.get("link").split("/")[-1].split("?")[0]
                    processed_forms.append(form_data)
                return {"success": True, "service_id": service_id, "service_name": service.get("name"), "data_source": source, "total_forms": len(processed_forms), "forms": processed_forms}
        return {"success": False, "error": f"Service {service_id} not found"}
    except Exception as e:
        logger.error(f"Get forms error: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
async def search_forms(query: str, form_type: Optional[str] = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """Search for forms across all services."""
    try:
        data, source = await fetch_services_data()
        services = data.get("data", [])
        search_terms = expand_query(query)
        results = []
        for service in services:
            for form in service.get("forms", []):
                form_name = form.get("name", "").lower()
                if all(term in form_name for term in search_terms):
                    if form_type:
                        try:
                            if detect_form_type(form_name) != FormType[form_type.upper()]: continue
                        except KeyError: pass
                    results.append({"form_name": form.get("name"), "download_link": form.get("link"), "form_type": detect_form_type(form.get("name")).value, "service_id": service.get("id"), "service_name": service.get("name")})
        
        total = len(results)
        start = (max(1, page) - 1) * max(1, min(page_size, 50))
        end = start + max(1, min(page_size, 50))
        return {"success": True, "query": query, "page": page, "page_size": page_size, "total_results": total, "has_next": end < total, "data_source": source, "results": results[start:end]}
    except Exception as e:
        logger.error(f"Search forms error: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
async def get_forms_by_type(form_type: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """Get all forms of a specific type across services."""
    try:
        target_type = FormType[form_type.upper()]
        data, source = await fetch_services_data()
        results = []
        for service in data.get("data", []):
            for form in service.get("forms", []):
                if detect_form_type(form.get("name", "")) == target_type:
                    results.append({"form_name": form.get("name"), "download_link": form.get("link"), "service_id": service.get("id"), "service_name": service.get("name")})
        total = len(results)
        start = (max(1, page) - 1) * max(1, min(page_size, 50))
        end = start + max(1, min(page_size, 50))
        return {"success": True, "form_type": target_type.value, "page": page, "page_size": page_size, "total_results": total, "has_next": end < total, "results": results[start:end]}
    except KeyError:
        return {"success": False, "error": f"Invalid form type. Choose from: {', '.join([t.name for t in FormType])}"}
    except Exception as e:
        logger.error(f"Get forms by type error: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
async def get_service_prerequisites(service_id: str) -> Dict[str, Any]:
    """Get all prerequisites and requirements for a service."""
    try:
        data, _ = await fetch_services_data()
        for s in data.get("data", []):
            if s.get("id") == service_id:
                return {"success": True, "service_id": service_id, "service_name": s.get("name"), "prerequisites": [{"name": p.get("name"), "description": p.get("description"), "link": p.get("link")} for p in s.get("prerequisites", [])], "requirements": s.get("requirements", []), "total_prerequisites": len(s.get("prerequisites", [])), "total_requirements": len(s.get("requirements", []))}
        return {"success": False, "error": f"Service {service_id} not found"}
    except Exception as e:
        logger.error(f"Get prerequisites error: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
async def get_service_checklist(service_id: str) -> Dict[str, Any]:
    """Get a comprehensive checklist for completing a service application."""
    try:
        data, _ = await fetch_services_data()
        for s in data.get("data", []):
            if s.get("id") == service_id:
                forms_by_type = {}
                for f in s.get("forms", []):
                    ft = detect_form_type(f.get("name", "")); forms_by_type.setdefault(ft.value, []).append({"name": f.get("name"), "link": f.get("link")})
                return {"success": True, "service_id": service_id, "service_name": s.get("name"), "checklist": {"fees": s.get("fees", "Not specified"), "process_time": s.get("process_time"), "prerequisites": s.get("prerequisites", []), "requirements": s.get("requirements", []), "forms_to_complete": forms_by_type, "online_available": bool(s.get("onlineprocessing"))}}
        return {"success": False, "error": f"Service {service_id} not found"}
    except Exception as e:
        logger.error(f"Get checklist error: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
async def analyze_form_for_filling(form_url: str) -> Dict[str, Any]:
    """Download a PDF form and extract its fillable fields."""
    return await analyze_form_for_filling_logic(form_url)

@mcp.tool()
async def perform_form_filling(form_url: str, field_data: Dict[str, str], output_filename: Optional[str] = None, flatten: bool = False, force_recompute: bool = False) -> Dict[str, Any]:
    """Fill a PDF form and save locally."""
    return await perform_form_filling_logic(form_url, field_data, output_filename, flatten, force_recompute)

@mcp.tool()
async def download_filled_form(filename: str, delete_after_read: Optional[bool] = None, only_preview: bool = False, ignore_size_limit: bool = False) -> List[Any]:
    """Retrieve a filled PDF form."""
    res = await download_filled_form_logic(filename, delete_after_read, only_preview, ignore_size_limit)
    if not res.get("success"): return [types.TextContent(type="text", text=f"Error: {res.get('error')}")]
    info_text = f"Form Retrieval: '{res['filename']}' ({res.get('size_bytes', 0)} bytes).\n"
    if "saved_path" in res: info_text += f"\n LOCAL SUCCESS: {res['saved_path']}"
    elif "warning" in res: info_text += f"\n REMOTE DOWNLOAD READY: berlin://forms/{res['filename']}"
    else: info_text += "\n REMOTE SUCCESS: Attached below."
    content = [types.TextContent(type="text", text=info_text)]
    if "content_base64" in res: content.append(types.TextContent(type="text", text=f"--- PDF BASE64 DATA ---\n{res['content_base64']}\n--- END ---"))
    return content

@mcp.tool()
async def get_form_visual_preview(filename: str, page_num: int = 0) -> List[Any]:
    """Render a page of a filled PDF as an image."""
    res = await get_form_visual_preview_logic(filename, page_num)
    if not res.get("success"): return [types.TextContent(type="text", text=f"Error: {res.get('error')}")]
    return [types.TextContent(type="text", text=f"Preview of {res['filename']}"), types.ImageContent(type="image", data=res["image_base64"], mimeType="image/jpeg")]

@mcp.tool()
async def open_file_locally(file_path: str) -> Dict[str, Any]:
    """Open a file on the user's local system."""
    if IS_CLOUD: return {"success": False, "error": "Cannot open on cloud."}
    if not HAS_OPEN_CMD: return {"success": False, "error": "Open command not found."}
    try:
        path = Path(file_path)
        if not path.exists(): return {"success": False, "error": "File not found."}
        subprocess.run(["open", str(path.absolute())])
        return {"success": True, "message": "Opened successfully."}
    except Exception as e: return {"success": False, "error": str(e)}

@mcp.tool()
async def delete_filled_form(filename: str) -> Dict[str, Any]:
    """Manually delete a filled form."""
    try:
        p = FILLED_FORMS_DIR / Path(filename).name
        if p.exists(): p.unlink(); return {"success": True, "message": "Deleted."}
        return {"success": False, "error": "Not found."}
    except Exception as e: return {"success": False, "error": str(e)}

@mcp.tool()
async def browse_services_by_category(category: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """Browse services by category."""
    try:
        cat = ServiceCategory[category.upper()]
        data, source = await fetch_services_data()
        matches = [s for s in data.get("data", []) if categorize_service(s) == cat]
        total = len(matches)
        start = (max(1, page) - 1) * max(1, min(page_size, 50))
        end = start + max(1, min(page_size, 50))
        return {"success": True, "category": cat.value, "page": page, "results": [{"id": s.get("id"), "name": s.get("name")} for s in matches[start:end]]}
    except KeyError: return {"success": False, "error": "Invalid category."}
    except Exception as e: return {"success": False, "error": str(e)}

@mcp.tool()
async def find_online_services(page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """Find all services available online."""
    try:
        data, _ = await fetch_services_data()
        online = [s for s in data.get("data", []) if s.get("onlineservices") or s.get("onlineprocessing")]
        total = len(online)
        start = (max(1, page) - 1) * max(1, min(page_size, 50))
        return {"success": True, "results": [{"id": s.get("id"), "name": s.get("name")} for s in online[start:start+max(1, min(page_size, 50))]]}
    except Exception as e: return {"success": False, "error": str(e)}

@mcp.tool()
async def get_service_locations(service_id: str) -> Dict[str, Any]:
    """Get all locations for a service."""
    try:
        data, _ = await fetch_services_data()
        for s in data.get("data", []):
            if s.get("id") == service_id:
                return {"success": True, "locations": [{"id": l.get("location"), "appointments": l.get("appointment", {}).get("allowed")} for l in s.get("locations", [])]}
        return {"success": False, "error": "Not found."}
    except Exception as e: return {"success": False, "error": str(e)}

@mcp.tool()
async def get_api_status() -> Dict[str, Any]:
    """Get API and cache status diagnostics."""
    try:
        data, source = await fetch_services_data()
        services = data.get("data", [])
        return {"success": True, "data_source": source, "total_services": len(services)}
    except Exception as e: return {"success": False, "error": str(e)}

@mcp.tool()
async def clear_cache() -> Dict[str, Any]:
    """Clear the service cache."""
    try:
        get_cache_instance().clear()
        return {"success": True, "message": "Cache cleared."}
    except Exception as e: return {"success": False, "error": str(e)}
