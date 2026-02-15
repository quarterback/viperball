#!/bin/bash
# Viperball Dynasty Manager Launcher

echo "🏈 Launching Viperball Dynasty Manager..."
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Check Tkinter
python3 -c "import tkinter" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Tkinter available"
else
    echo "❌ Tkinter not found"
    echo ""
    echo "Please install Tkinter:"
    echo "  Ubuntu/Debian: sudo apt-get install python3-tk"
    echo "  macOS: (should be included with Python)"
    echo "  Windows: (should be included with Python)"
    exit 1
fi

echo ""
echo "Starting GUI..."
python3 viperball_gui.py
