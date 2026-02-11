# Berlin Services MCP Server - Enhanced

A production-grade Model Context Protocol (MCP) server for Berlin city services (Dienstleistungen). It features resilient caching, advanced search, PDF form discovery, and filling capabilities.

## Features
- **Comprehensive Tools**: Search, browse, and get detailed information on Berlin services.
- **Form Management**: Discover, analyze, and fill PDF forms for various services.
- **Resilient Caching**: Optimized for performance with intelligent fallback for offline use.
- **Remote Sync**: Supports both local and remote (Cloud) deployments.

## Prerequisites
- Python 3.11 or higher
- `uv` (recommended) or `pip`

## Local Setup

### Using `uv` (Recommended)
1. Install dependencies and sync the environment:
   ```bash
   uv sync
   ```
2. Run the server as a module:
   ```bash
   export PYTHONPATH=$PYTHONPATH:$(pwd)/src && uv run python -m berlin_mcp.main
   ```
   *Note: If you've installed the package via `uv sync`, you can also just run:*
   ```bash
   uv run berlin-mcp
   ```

### Using `pip`
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the server:
   ```bash
   export PYTHONPATH=$PYTHONPATH:$(pwd)/src && python -m berlin_mcp.main
   ```

## Claude Desktop Configuration

Add the following to your Claude Desktop configuration file. Replace `/Users/mananshah/Desktop/Berlin-Services-MCP-Server` with the actual absolute path to the folder.

### macOS
File location: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "berlin-services": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/mananshah/Desktop/Berlin-Services-MCP-Server",
        "python",
        "-m",
        "berlin_mcp.main"
      ],
      "env": {
        "PYTHONPATH": "src"
      }
    }
  }
}
```

### Windows
File location: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "berlin-services": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\Users\\YourUser\\Desktop\\Berlin-Services-MCP-Server",
        "python",
        "-m",
        "berlin_mcp.main"
      ],
      "env": {
        "PYTHONPATH": "src"
      }
    }
  }
}
```

## Tools and Resources

The server exposes the following tools to help you navigate and manage Berlin city services:

| Tool | Description |
|------|-------------|
| `search_services` | Advanced search for Berlin services with paging and filters. |
| `get_service_details` | Get complete details about a service including forms and prerequisites. |
| `get_service_forms` | Get all forms associated with a service with detailed metadata. |
| `search_forms` | Search for forms across all services. |
| `get_forms_by_type` | Get all forms of a specific type across services. |
| `get_service_prerequisites` | Get all prerequisites and requirements for a service. |
| `get_service_checklist` | Get a comprehensive checklist for completing a service application. |
| `analyze_form_for_filling` | Download a PDF form and extract its fillable fields. |
| `perform_form_filling` | Fill a PDF form and save locally. |
| `download_filled_form` | Retrieve a filled PDF form. |
| `get_form_visual_preview` | Render a page of a filled PDF as an image. |
| `open_file_locally` | Open a file on the user's local system (Local setup only). |
| `delete_filled_form` | Manually delete a filled form from the server. |
| `browse_services_by_category` | Browse services by category. |
| `find_online_services` | Find all services available online. |
| `get_service_locations` | Get all locations for a service. |
| `get_api_status` | Get API and cache status diagnostics. |
| `clear_cache` | Clear the service cache and force refresh. |

## Security Note

PDF forms filled on remote servers should be downloaded and then deleted using the `delete_filled_form` tool to ensure data privacy.