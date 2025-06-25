#!/bin/bash

# MCP Factory Simplified Audit Script
# Clean implementation without hardcoded configurations

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEFAULT_CONFIG="$SCRIPT_DIR/audit_config.yaml"
AUDIT_SCRIPT="$SCRIPT_DIR/audit.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Utility functions
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Help function
show_help() {
    cat << EOF
MCP Factory Simplified Audit Tool

Usage: $0 [OPTIONS]

Options:
    --full          Run complete audit (default)
    --quick         Run quick audit (reduced timeout)
    --static        Run static analysis only
    --config FILE   Specify configuration file
    --output DIR    Specify output directory
    --deps-check    Check dependencies only
    --deps-install  Install missing dependencies
    --help          Show this help

Examples:
    $0                              # Full audit
    $0 --quick                      # Quick audit
    $0 --static                     # Static analysis only
    $0 --deps-check                 # Check dependencies
    $0 --output /tmp/audit          # Custom output directory

EOF
}

# Check if Python script exists
check_audit_script() {
    if [[ ! -f "$AUDIT_SCRIPT" ]]; then
        print_error "Audit script not found: $AUDIT_SCRIPT"
        exit 1
    fi
    
    if [[ ! -x "$AUDIT_SCRIPT" ]]; then
        print_info "Making audit script executable..."
        chmod +x "$AUDIT_SCRIPT"
    fi
}

# Check configuration file
check_config_file() {
    local config_file="$1"
    
    if [[ ! -f "$config_file" ]]; then
        print_error "Configuration file not found: $config_file"
        print_info "Available configurations:"
        find "$SCRIPT_DIR" -name "*.yaml" -o -name "*.yml" | while read -r file; do
            echo "  - $(basename "$file")"
        done
        exit 1
    fi
    
    # Validate YAML syntax
    if command -v python3 >/dev/null 2>&1; then
        if ! python3 -c "import yaml; yaml.safe_load(open('$config_file'))" 2>/dev/null; then
            print_error "Invalid YAML configuration file: $config_file"
            exit 1
        fi
    fi
}

# Check dependencies using unified checker
check_dependencies() {
    local install_flag="$1"
    
    print_info "Checking dependencies..."
    
    if [[ "$install_flag" == "install" ]]; then
        python3 "$SCRIPT_DIR/dependency_checker.py" --install --project-root "$PROJECT_ROOT"
    else
        python3 "$SCRIPT_DIR/dependency_checker.py" --project-root "$PROJECT_ROOT"
    fi
}

# Run audit with specified parameters
run_audit() {
    local mode="$1"
    local config_file="$2"
    local output_dir="$3"
    
    print_info "Starting $mode audit..."
    print_info "Project root: $PROJECT_ROOT"
    print_info "Configuration: $config_file"
    
    # Build command arguments
    local cmd_args=()
    cmd_args+=("--mode" "$mode")
    cmd_args+=("--config" "$config_file")
    cmd_args+=("--project-root" "$PROJECT_ROOT")
    
    if [[ -n "$output_dir" ]]; then
        cmd_args+=("--output" "$output_dir")
        print_info "Output directory: $output_dir"
    fi
    
    # Execute audit
    if python3 "$AUDIT_SCRIPT" "${cmd_args[@]}"; then
        print_success "$mode audit completed successfully"
        return 0
    else
        print_error "$mode audit failed"
        return 1
    fi
}

# Main execution
main() {
    local mode="full"
    local config_file="$DEFAULT_CONFIG"
    local output_dir=""
    local deps_only=false
    local deps_install=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --full)
                mode="full"
                shift
                ;;
            --quick)
                mode="quick"
                shift
                ;;
            --static)
                mode="static"
                shift
                ;;
            --config)
                config_file="$2"
                shift 2
                ;;
            --output)
                output_dir="$2"
                shift 2
                ;;
            --deps-check)
                deps_only=true
                shift
                ;;
            --deps-install)
                deps_install=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Handle dependencies-only modes
    if [[ "$deps_only" == true ]]; then
        check_dependencies "check"
        exit $?
    fi
    
    if [[ "$deps_install" == true ]]; then
        check_dependencies "install"
        exit $?
    fi
    
    # Pre-flight checks
    check_audit_script
    check_config_file "$config_file"
    
    # Run audit
    if run_audit "$mode" "$config_file" "$output_dir"; then
        print_success "Audit process completed successfully"
        
        # Show output location
        if [[ -n "$output_dir" ]]; then
            print_info "Results available at: $output_dir"
        else
            print_info "Results available at: $PROJECT_ROOT/audit_results"
        fi
        
        exit 0
    else
        print_error "Audit process failed"
        exit 1
    fi
}

# Execute main function with all arguments
main "$@" 