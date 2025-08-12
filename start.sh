#!/bin/bash
# Linux/Mac Starter für Paperless NGX Integration

# Check if venv exists and activate it
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual Environment nicht gefunden!"
    echo "Erstelle venv mit: python3 -m venv venv"
    exit 1
fi

# Run the universal Python starter
python3 start.py "$@"