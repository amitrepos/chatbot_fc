#!/bin/bash
#
# Setup Script for PDF Reader MCP Server in Cursor
#
# This script helps install and configure the PDF Reader MCP Server
# for viewing PDFs properly in Cursor IDE.
#

set -e

echo "=========================================="
echo "PDF Reader MCP Server Setup for Cursor"
echo "=========================================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed."
    echo ""
    echo "Installing Node.js..."
    
    # Detect OS
    if [ -f /etc/redhat-release ]; then
        # Rocky Linux / RHEL / CentOS
        echo "Detected Rocky Linux / RHEL"
        sudo dnf install -y nodejs npm
    elif [ -f /etc/debian_version ]; then
        # Debian / Ubuntu
        echo "Detected Debian / Ubuntu"
        sudo apt-get update
        sudo apt-get install -y nodejs npm
    else
        echo "⚠️  Please install Node.js manually: https://nodejs.org/"
        exit 1
    fi
fi

echo "✅ Node.js version: $(node --version)"
echo "✅ npm version: $(npm --version)"
echo ""

# Check if MCP server package exists
echo "Checking for PDF Reader MCP Server..."
echo ""

# Option 1: Try to install via npm (if available as package)
if npm list -g @modelcontextprotocol/server-pdf-reader &> /dev/null; then
    echo "✅ PDF Reader MCP Server already installed globally"
    MCP_SERVER_PATH=$(npm list -g @modelcontextprotocol/server-pdf-reader | grep server-pdf-reader | head -1 | awk '{print $NF}')
else
    echo "📦 Installing PDF Reader MCP Server..."
    
    # Try to install from npm
    if npm install -g @modelcontextprotocol/server-pdf-reader 2>/dev/null; then
        echo "✅ Installed via npm"
        MCP_SERVER_PATH=$(npm list -g @modelcontextprotocol/server-pdf-reader | grep server-pdf-reader | head -1 | awk '{print $NF}')
    else
        echo "⚠️  Package not found in npm registry"
        echo ""
        echo "Alternative: Clone from GitHub"
        echo "Would you like to clone from GitHub? (y/n)"
        read -r response
        
        if [[ "$response" =~ ^[Yy]$ ]]; then
            CLONE_DIR="$HOME/mcp-servers"
            mkdir -p "$CLONE_DIR"
            cd "$CLONE_DIR"
            
            if [ -d "servers" ]; then
                echo "📁 Updating existing repository..."
                cd servers
                git pull
            else
                echo "📥 Cloning MCP servers repository..."
                git clone https://github.com/modelcontextprotocol/servers.git
                cd servers
            fi
            
            if [ -d "src/pdf-reader" ]; then
                cd src/pdf-reader
                echo "📦 Installing dependencies..."
                npm install
                echo "🔨 Building..."
                npm run build
                
                MCP_SERVER_PATH="$(pwd)/build/index.js"
                echo "✅ Built at: $MCP_SERVER_PATH"
            else
                echo "❌ PDF reader server not found in repository"
                exit 1
            fi
        else
            echo "❌ Installation cancelled"
            exit 1
        fi
    fi
fi

echo ""
echo "=========================================="
echo "Configuration Instructions"
echo "=========================================="
echo ""
echo "The PDF Reader MCP Server is ready!"
echo ""
echo "To configure in Cursor:"
echo "1. Open Cursor Settings: File > Preferences > Settings (or Ctrl+,)"
echo "2. Navigate to: Features > MCP"
echo "3. Click: '+ Add New MCP Server'"
echo "4. Configure:"
echo "   - Name: PDF Reader"
echo "   - Type: stdio"
echo "   - Command: node $MCP_SERVER_PATH"
echo "5. Restart Cursor"
echo ""
echo "After setup, Cursor will be able to read and display PDFs properly!"
echo ""
echo "=========================================="


