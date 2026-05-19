#!/bin/bash

# Configuration
INPUT_FILE="index.html"
OUTPUT_FILE="TrashUQ_presentation.pdf"
ABS_INPUT_PATH="$(pwd)/$INPUT_FILE"

echo "--------------------------------------------------"
echo "TrashUQ Presentation PDF Export"
echo "--------------------------------------------------"

# Check if node/npx is available
if ! command -v npx &> /dev/null; then
    echo "Error: npx is not installed. Please install Node.js."
    exit 1
fi

echo "Generating PDF using Playwright (Node API)..."
echo "This might take a moment..."

# Run the node script using npx to ensure playwright is available
# We use -y to skip confirmation
npx -y playwright install chromium
npx -y node export_pdf.js

if [ $? -eq 0 ]; then
    echo "--------------------------------------------------"
    echo "Success! PDF generated: $OUTPUT_FILE"
    echo "--------------------------------------------------"
else
    echo "--------------------------------------------------"
    echo "Automatic export failed."
    echo "Trying fallback CLI method..."
    npx -y playwright pdf "file://$ABS_INPUT_PATH" "$OUTPUT_FILE" --paper-format Letter --wait-for-timeout 5000
    
    if [ $? -eq 0 ]; then
        echo "Success! (Fallback method used, check orientation)"
    else
        echo "Manual Export Instructions:"
        echo "1. Open index.html in Chrome/Edge/Firefox"
        echo "2. Add '?print-pdf' to the URL: index.html?print-pdf"
        echo "3. Press Ctrl+P (Print)"
        echo "4. Set Destination to 'Save as PDF'"
        echo "5. Set Layout to 'Landscape'"
        echo "6. Enable 'Background graphics' in Options"
        echo "--------------------------------------------------"
    fi
fi
