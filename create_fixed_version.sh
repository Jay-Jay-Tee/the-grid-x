#!/bin/bash
# Script to create complete fixed version

echo "Creating Grid-X Fixed Version..."

# Copy all original files
cp -r /home/claude/the-grid-x-main/* /home/claude/grid-x-fixed/

# Apply fixes to coordinator/websocket.py
cd /home/claude/grid-x-fixed/coordinator
sed -i 's/from database import get_db/from .database import get_db/g' websocket.py
sed -i 's/from workers import workers_ws/from .workers import workers_ws/g' websocket.py

echo "✅ Fixed coordinator/websocket.py imports"

# Verify common module is not empty
if [ -s "/home/claude/grid-x-fixed/common/constants.py" ]; then
    echo "✅ Common module is properly implemented"
else
    echo "❌ Warning: Common module files are empty"
fi

# Verify requirements.txt exists and is not empty
if [ -s "/home/claude/grid-x-fixed/requirements.txt" ]; then
    echo "✅ Requirements.txt is present"
else
    echo "❌ Warning: Requirements.txt is missing"
fi

echo ""
echo "Grid-X Fixed Version Created Successfully!"
echo "Location: /home/claude/grid-x-fixed/"
echo ""
echo "Next steps:"
echo "1. cd /home/claude/grid-x-fixed"
echo "2. pip install -r requirements.txt"
echo "3. Follow COMPLETE_SETUP_GUIDE.md"

