#!/bin/bash

# Usage: LogProcessingTest.sh [mode]
# Modes: physical, emulator, both, help, html

# Get the script directory (RunScripts)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Go to platform-automation root (one level up)
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
# Set the test directory
TEST_DIR="$ROOT_DIR/FlintAPITest/LogProcessingTest"
# Reports directory
REPORT_DIR="$ROOT_DIR/TestReports"

# Create reports directory if it doesn't exist
mkdir -p "$REPORT_DIR"

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
    echo "  physical        - Run Physical Device Test only"
    echo "  emulator        - Run Emulator Test only"
    echo "  both            - Run both tests"
    echo "  html            - Run both tests with HTML report"
    echo "  help            - Show this help message"
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

# Setup virtual environment only if it doesn't exist
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
fi

if [ ! -f "venv/bin/python" ]; then
    print_error "Failed to create virtual environment"
    exit 1
fi

# Check if dependencies are already installed
if [ ! -f "venv/.installed" ]; then
    print_info "Installing dependencies for the first time..."
    venv/bin/pip install -q pytest pytest-html requests python-dotenv
    touch venv/.installed
    print_success "Dependencies installed"
else
    print_success "Dependencies already installed, skipping..."
fi

# Function to run physical device test
run_physical_test() {
    print_info "Running Physical Device Test..."
    venv/bin/python -m pytest device_log_test.py -v -s
    print_success "Physical Device Test completed!"
}

# Function to run emulator test
run_emulator_test() {
    print_info "Running Emulator Test..."
    venv/bin/python -m pytest emulator_log_test.py -v -s
    print_success "Emulator Test completed!"
}

# Function to run both tests with HTML report
run_html_report() {
    local timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
    local report_file="$REPORT_DIR/LogProcessingTest_Report_$timestamp.html"
    
    print_info "Running both tests with HTML report..."
    print_info "Report will be saved to: $report_file"
    
    venv/bin/python -m pytest device_log_test.py emulator_log_test.py -v -s --html="$report_file" --self-contained-html
    
    print_success "HTML report generated: $report_file"
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
    html)
        run_html_report
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
        echo "4) Run Both Tests with HTML Report"
        echo "5) Exit"
        echo "============================================================"
        printf "Enter choice [1-5]: "
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
                run_html_report
                ;;
            5)
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