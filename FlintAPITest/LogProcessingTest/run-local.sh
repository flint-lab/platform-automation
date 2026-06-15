#!/bin/bash

# FlintLab Log Automation - Local Run Script

echo "============================================================"
echo "🚀 FlintLab Log Automation"
echo "============================================================"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "   Please copy .env.example to .env and add your token"
    exit 1
fi

# Load environment variables
source .env

# Check if token is set
if [ -z "$FLINT_API_TOKEN" ] || [ "$FLINT_API_TOKEN" = "your_token_here" ]; then
    echo "❌ FLINT_API_TOKEN not set in .env file"
    echo "   Please add your actual token to .env"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update requirements
echo "📦 Installing dependencies..."
pip install -r requirements.txt -q

echo ""
echo "============================================================"
echo "Select test to run:"
echo "============================================================"
echo "1) Physical Device Test"
echo "2) Emulator Test"
echo "3) Run Both Tests"
echo "4) Exit"
echo "============================================================"
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo ""
        echo "▶️ Running Physical Device Test..."
        python device_log_test.py
        ;;
    2)
        echo ""
        echo "▶️ Running Emulator Test..."
        python emulator_log_test.py
        ;;
    3)
        echo ""
        echo "▶️ Running Physical Device Test..."
        python device_log_test.py
        
        echo ""
        echo "============================================================"
        echo "▶️ Running Emulator Test..."
        echo "============================================================"
        python emulator_log_test.py
        ;;
    4)
        echo "👋 Exiting..."
        exit 0
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

# Deactivate virtual environment
deactivate

echo ""
echo "============================================================"
echo "✅ Done!"
echo "============================================================"