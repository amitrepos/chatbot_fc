# Cursor PDF Viewer Setup Guide

## Problem
When opening PDF files in Cursor, they display as raw binary/ASCII data instead of visual content. This guide provides solutions to view PDFs properly within Cursor.

## Solution 1: PDF Reader MCP Server (Recommended)

The **PDF Reader MCP Server** integrates with Cursor to enable proper PDF viewing and text extraction.

### Installation Steps

1. **Install the PDF Reader MCP Server:**
   ```bash
   # Install Node.js if not already installed (required for MCP server)
   # On Rocky Linux:
   sudo dnf install nodejs npm
   
   # Clone or install the PDF Reader MCP Server
   # Option A: Use the official MCP PDF Reader
   npm install -g @modelcontextprotocol/server-pdf-reader
   
   # Option B: Or clone from GitHub
   git clone https://github.com/modelcontextprotocol/servers.git
   cd servers/src/pdf-reader
   npm install
   npm run build
   ```

2. **Configure in Cursor:**
   - Open Cursor Settings: `File` > `Preferences` > `Settings` (or `Ctrl+,`)
   - Navigate to: `Features` > `MCP`
   - Click: `+ Add New MCP Server`
   - Configure:
     - **Name:** `PDF Reader` (or any name you prefer)
     - **Type:** `stdio` (standard input/output)
     - **Command:** 
       ```bash
       node /path/to/mcp-pdf-reader/build/index.js
       ```
       Or if installed globally:
       ```bash
       mcp-server-pdf-reader
       ```

3. **Restart Cursor** to load the MCP server

4. **Usage:**
   - After setup, Cursor will automatically use the PDF Reader tool when you open PDF files
   - The Composer Agent will utilize PDF reading capabilities
   - You can explicitly request PDF reading by mentioning it in your prompts

### Alternative: Quick Setup Script

Run the setup script:
```bash
bash scripts/setup_pdf_mcp_server.sh
```

## Solution 2: Convert PDF to Images (Alternative)

If MCP server setup is not preferred, you can convert PDF pages to images that Cursor can display.

### Quick Conversion Script

```bash
# Convert PDF pages to PNG images
python scripts/pdf_to_images_viewer.py "data/documents/Generic_Wire_ISO_MX_v2_pages_1-2.pdf"
```

This will create:
- `data/documents/Generic_Wire_ISO_MX_v2_pages_1-2_images/`
  - `page_001.png`
  - `page_002.png`
  - etc.

Then you can view the PNG files in Cursor (which displays images properly).

## Solution 3: External PDF Viewer

For quick viewing, use your system's default PDF viewer:

```bash
# On Rocky Linux (if evince is installed)
evince "data/documents/Generic_Wire_ISO_MX_v2_pages_1-2.pdf"

# Or use xdg-open (opens with default viewer)
xdg-open "data/documents/Generic_Wire_ISO_MX_v2_pages_1-2.pdf"
```

## Recommended Approach

**For Development:** Use Solution 1 (MCP Server) - integrates seamlessly with Cursor  
**For Quick Viewing:** Use Solution 2 (Convert to Images) - simple and works immediately  
**For System Files:** Use Solution 3 (External Viewer) - fastest for one-off viewing

## Troubleshooting

### MCP Server Not Working
1. Check Node.js is installed: `node --version`
2. Verify MCP server path is correct in Cursor settings
3. Check Cursor logs: `Help` > `Toggle Developer Tools` > `Console`
4. Restart Cursor after configuration changes

### PDF to Images Conversion Fails
1. Ensure PyMuPDF is installed: `pip install PyMuPDF`
2. Check PDF file is not corrupted
3. Verify write permissions in output directory

## References

- [PDF Reader MCP Server](https://cursor.directory/mcp/pdf-reader)
- [MCP Documentation](https://modelcontextprotocol.io/)
- [Cursor MCP Guide](https://docs.cursor.com/mcp)


