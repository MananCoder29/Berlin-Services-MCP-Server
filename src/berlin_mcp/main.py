import os
from .server import mcp
from .config import logger, CACHE_DURATION_SECONDS, CACHE_FILE
# Import tools and resources to register them
from . import tools
from . import resources

def main():
    logger.info("Starting Berlin Services MCP Server (Modular)")
    logger.info(f"Cache TTL: {CACHE_DURATION_SECONDS}s")
    logger.info(f"Cache file: {CACHE_FILE}")
    
    port = os.environ.get("PORT")
    if port:
        logger.info(f"Cloud mode: Starting on port {port}")
        mcp.run(transport="streamable-http", port=int(port), host="0.0.0.0")
    else:
        logger.info("Local mode: Using stdio")
        mcp.run()

if __name__ == "__main__":
    main()
