#!/bin/bash

# Usage: LogProcessingTest.sh [mode]
# Modes: physical, emulator, both, help

# Get the script directory (RunScripts)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Go to platform-automation root (one level up)
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
# Set the test directory - LogProcessingTest is directly under FlintAPITest
TEST_DIR="$ROOT_DIR/FlintAPITest/LogProcessingTest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_info() { echo -e "${YELLOW}📢 $1${NC}"; }

# Function to show usage
show_usage() {
    echo "Usage: $0 [mode]"
    echo ""
    echo "Modes:"
    echo "  physical    - Run Physical Device Test only"
    echo "  emulator    - Run Emulator Test only"
    echo "  both        - Run both tests"
    echo "  help        - Show this help message"
    echo ""
    echo "If no mode is provided, interactive menu will be shown."
}

# Check if test directory exists
if [ ! -d "$TEST_DIR" ]; then
    print_error "Test directory not found: $TEST_DIR"
    exit 1
fi

# Check if .env file exists
if [ ! -f "$TEST_DIR/.env" ]; then
    print_error ".env file not found in $TEST_DIR"
    echo "   Please create .env file with:"
    echo "   FLINT_API_TOKEN=your_token_here"
    echo "   WAIT_TIME_FOR_LOGS=20"
    exit 1
fi

# Load environment variables
set -a
. "$TEST_DIR/.env"
set +a

# Check if token is set
if [ -z "${FLINT_API_TOKEN:-}" ] || [ "${FLINT_API_TOKEN:-}" = "your_token_here" ]; then
    print_error "FLINT_API_TOKEN not set in $TEST_DIR/.env"
    exit 1
fi

print_success "Configuration loaded"
print_info "API Base URL: ${FLINT_API_BASE:-https://staging.api.flintlab.io}"
print_info "Wait Time: ${WAIT_TIME_FOR_LOGS:-20} seconds"

# Change to test directory
cd "$TEST_DIR"

# Setup virtual environment if not exists
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
fi

# Check if venv was created successfully
if [ ! -f "venv/bin/python" ]; then
    print_error "Failed to create virtual environment"
    exit 1
fi

# Install requirements using venv pip directly
if [ -f "requirements.txt" ]; then
    print_info "Installing dependencies..."
    venv/bin/pip install -r requirements.txt -q --disable-pip-version-check
    print_success "Dependencies installed"
fi

# Function to run physical device test
run_physical_test() {
    print_info "Running Physical Device Test..."
    venv/bin/python device_log_test.py
    print_success "Physical Device Test completed!"
}

# Function to run emulator test
run_emulator_test() {
    print_info "Running Emulator Test..."
    venv/bin/python emulator_log_test.py
    print_success "Emulator Test completed!"
}

# Parse command line argument
MODE="${1:-}"

case "$MODE" in
    physical)
        run_physical_test
        ;;
    emulator)
        run_emulator_test
        ;;
    both)
        run_physical_test
        echo ""
        echo "============================================================"
        run_emulator_test
        ;;
    help|--help|-h)
        show_usage
        exit 0
        ;;
    "")
        # Interactive menu
        echo ""
        echo "============================================================"
        echo "Select test to run:"
        echo "============================================================"
        echo "1) Physical Device Test"
        echo "2) Emulator Test"
        echo "3) Run Both Tests"
        echo "4) Exit"
        echo "============================================================"
        printf "Enter choice [1-4]: "
        read choice
        
        case $choice in
            1)
                run_physical_test
                ;;
            2)
                run_emulator_test
                ;;
            3)
                run_physical_test
                echo ""
                echo "============================================================"
                run_emulator_test
                ;;
            4)
                print_info "Exiting..."
                exit 0
                ;;
            *)
                print_error "Invalid choice"
                exit 1
                ;;
        esac
        ;;
    *)
        print_error "Unknown mode: $MODE"
        show_usage
        exit 1
        ;;
esac

echo ""
print_success "Test execution completed!"