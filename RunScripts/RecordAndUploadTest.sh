#!/bin/bash

# Usage: RecordAndUploadTest.sh [mode]
# Modes: android, ios, emulator, all, html, help

# Get the script directory (RunScripts)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Go to platform-automation root (one level up)
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
# Set the test directory
TEST_DIR="$ROOT_DIR/FlintAPITest/RecordAndUploadTest"
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
    echo "  android         - Run Android Recording & APK Upload tests only"
    echo "  ios             - Run iOS IPA Upload tests only"
    echo "  emulator        - Run Emulator Recording & APK Upload tests only"
    echo "  all             - Run all tests (Android, iOS, Emulator)"
    echo "  html            - Run all tests with HTML report"
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

# Change to test directory
cd "$TEST_DIR"

# Setup virtual environment if not exists
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

# Function to run Android Recording & APK tests
run_android_tests() {
    print_info "Running Android Recording & APK Upload tests..."
    echo ""
    echo "============================================================"
    echo "📱 ANDROID TESTS"
    echo "============================================================"
    if [ -f "record_and_upload_test.py" ]; then
        venv/bin/python -m pytest record_and_upload_test.py -v -s
    else
        print_error "record_and_upload_test.py not found!"
    fi
    print_success "Android tests completed!"
}

# Function to run iOS IPA Upload tests
run_ios_tests() {
    print_info "Running iOS IPA Upload tests..."
    echo ""
    echo "============================================================"
    echo "🍎 IOS TESTS"
    echo "============================================================"
    if [ -f "ios_device_upload.py" ]; then
        venv/bin/python -m pytest ios_device_upload.py -v -s
    else
        print_error "ios_device_upload.py not found!"
        echo "   Please create ios_device_upload.py for iOS testing"
    fi
    print_success "iOS tests completed!"
}

# Function to run Emulator tests
run_emulator_tests() {
    print_info "Running Emulator Recording & APK Upload tests..."
    echo ""
    echo "============================================================"
    echo "🤖 EMULATOR TESTS"
    echo "============================================================"
    if [ -f "emulator_record_upload_test.py" ]; then
        venv/bin/python -m pytest emulator_record_upload_test.py -v -s
    else
        print_error "emulator_record_upload_test.py not found!"
        echo "   Please create emulator_record_upload_test.py for Emulator testing"
    fi
    print_success "Emulator tests completed!"
}

# Function to run all tests
run_all_tests() {
    print_info "Running ALL tests..."
    
    echo ""
    echo "============================================================"
    echo "📱 ANDROID TESTS"
    echo "============================================================"
    if [ -f "record_and_upload_test.py" ]; then
        venv/bin/python -m pytest record_and_upload_test.py -v -s
    else
        print_error "record_and_upload_test.py not found!"
    fi
    
    echo ""
    echo "============================================================"
    echo "🍎 IOS TESTS"
    echo "============================================================"
    if [ -f "ios_device_upload.py" ]; then
        venv/bin/python -m pytest ios_device_upload.py -v -s
    else
        print_error "ios_device_upload.py not found!"
    fi
    
    echo ""
    echo "============================================================"
    echo "🤖 EMULATOR TESTS"
    echo "============================================================"
    if [ -f "emulator_record_upload_test.py" ]; then
        venv/bin/python -m pytest emulator_record_upload_test.py -v -s
    else
        print_error "emulator_record_upload_test.py not found!"
    fi
    
    print_success "All tests completed!"
}

# Function to run all tests with HTML report
run_html_report() {
    local timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
    local report_file="$REPORT_DIR/RecordAndUploadTest_Report_$timestamp.html"
    
    print_info "Running ALL tests with HTML report..."
    print_info "Report will be saved to: $report_file"
    
    # Check which test files exist and run them
    local test_files=""
    if [ -f "record_and_upload_test.py" ]; then
        test_files="$test_files record_and_upload_test.py"
    fi
    if [ -f "ios_device_upload.py" ]; then
        test_files="$test_files ios_device_upload.py"
    fi
    if [ -f "emulator_record_upload_test.py" ]; then
        test_files="$test_files emulator_record_upload_test.py"
    fi
    
    if [ -n "$test_files" ]; then
        venv/bin/python -m pytest $test_files -v -s --html="$report_file" --self-contained-html
        print_success "HTML report generated: $report_file"
    else
        print_error "No test files found!"
    fi
}

# Parse command line argument
MODE="${1:-}"

case "$MODE" in
    android)
        run_android_tests
        ;;
    ios)
        run_ios_tests
        ;;
    emulator)
        run_emulator_tests
        ;;
    all)
        run_all_tests
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
        echo "🚀 RECORD & UPLOAD TEST MENU"
        echo "============================================================"
        echo "1) Android - Recording & APK Upload"
        echo "2) iOS - IPA Upload"
        echo "3) Emulators - Recording & APK Upload"
        echo "4) Run All Tests"
        echo "5) Run All Tests with HTML Report"
        echo "6) Exit"
        echo "============================================================"
        printf "Enter choice [1-6]: "
        read choice
        
        case $choice in
            1)
                run_android_tests
                ;;
            2)
                run_ios_tests
                ;;
            3)
                run_emulator_tests
                ;;
            4)
                run_all_tests
                ;;
            5)
                run_html_report
                ;;
            6)
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