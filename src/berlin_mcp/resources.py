import json
from .server import mcp
from .models import ServiceCategory, FormType
from .services.api_client import fetch_services_data
from .services.form_logic import download_filled_form_logic, get_file_sync_instance
from .tools import get_api_status

@mcp.resource("berlin://categories")
async def get_categories() -> str:
    """Get all available service categories"""
    return json.dumps([{"name": c.name, "value": c.value} for c in ServiceCategory], indent=2)

@mcp.resource("berlin://status")
async def get_status() -> str:
    """Get system status as a resource"""
    status = await get_api_status()
    sync_manager = get_file_sync_instance()
    if isinstance(status, dict):
        status["sync_manifest_size"] = len(sync_manager.manifest)
    return json.dumps(status, indent=2, ensure_ascii=False)

@mcp.resource("berlin://form-types")
async def get_form_types() -> str:
    """Get all available form types"""
    return json.dumps([{"name": f.name, "value": f.value} for f in FormType], indent=2)

@mcp.resource("berlin://files/manifest")
async def get_files_manifest() -> str:
    """Get manifest of all available files on the remote server."""
    return json.dumps(get_file_sync_instance().manifest, indent=2, ensure_ascii=False)

@mcp.resource("berlin://files/sync/{file_id}")
async def sync_file_to_client(file_id: str) -> str:
    """Resource endpoint for syncing specific file to local client as Base64."""
    sync_manager = get_file_sync_instance()
    if file_id not in sync_manager.manifest:
        return json.dumps({"error": f"File {file_id} not found"})
    file_info = sync_manager.manifest[file_id]
    content = sync_manager.get_file_as_base64(file_info["path"])
    return json.dumps({"success": True, "file_id": file_id, "content_base64": content}, ensure_ascii=False)

@mcp.resource("berlin://forms/{filename}")
async def get_filled_form_resource(filename: str) -> str:
    """Access a filled form as an MCP Resource."""
    result = await download_filled_form_logic(filename, delete_after_read=True)
    if not result["success"]: return f"Error: {result['error']}"
    return f"Filename: {filename}\nSize: {result['size_bytes']}\nData: {result.get('content_base64')}"
