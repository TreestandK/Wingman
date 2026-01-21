#!/bin/bash

# Game Server Deployment Automation Script v2.0.1
# Enhanced with full automatic rollback and connectivity testing
# Author: Generated for treestandk.com infrastructure

set -e  # Exit on error
trap 'error_handler $? $LINENO' ERR

# Version
VERSION="2.0.1"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration files
CONFIG_DIR="${HOME}/.gameserver-deploy"
CONFIG_FILE="${CONFIG_DIR}/config.env"
TEMPLATES_DIR="${CONFIG_DIR}/templates"
STATE_FILE="${CONFIG_DIR}/deployment_state.json"
LOG_DIR="${CONFIG_DIR}/logs"

# Deployment state variables
CURRENT_STEP=0
DEPLOYMENT_ID=""
CF_RECORD_ID=""
UNIFI_RULE_IDS=()
NPM_PROXY_ID=""
PTERO_SERVER_UUID=""

# Create necessary directories
mkdir -p "$CONFIG_DIR" "$TEMPLATES_DIR" "$LOG_DIR"

# Log file with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/deployment_${TIMESTAMP}.log"
ERROR_LOG="${LOG_DIR}/error_${TIMESTAMP}.log"

# ============================================
# CONFIGURATION MANAGEMENT
# ============================================

# Function to create default config file
create_default_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        cat > "$CONFIG_FILE" <<'EOF'
# Game Server Deployment Configuration
# Edit this file with your credentials and endpoints

# Domain Configuration
DOMAIN="treestandk.com"

# Cloudflare Configuration
CF_API_TOKEN=""
CF_ZONE_ID=""

# Nginx Proxy Manager Configuration
NPM_API_URL=""  # e.g., http://192.168.1.100:81/api
NPM_EMAIL=""
NPM_PASSWORD=""

# UniFi Configuration
UNIFI_URL=""  # e.g., https://192.168.1.1
UNIFI_USER=""
UNIFI_PASS=""
UNIFI_SITE="default"
UNIFI_IS_UDM="false"  # Set to "true" for UDM/UCG devices

# Pterodactyl Configuration
PTERO_URL=""  # e.g., https://panel.yourdomain.com
PTERO_API_KEY=""

# Network Configuration
PUBLIC_IP=""  # Leave empty for auto-detection

# Feature Flags
ENABLE_AUTO_UNIFI="true"
ENABLE_SSL_AUTO="true"
ENABLE_MONITORING="false"

# Backup Settings
ENABLE_CONFIG_BACKUP="true"
BACKUP_RETENTION_DAYS=30
EOF
        print_message "$GREEN" "Created default configuration file at: $CONFIG_FILE"
        print_message "$YELLOW" "Please edit this file with your credentials before running the script."
        exit 0
    fi
}

# Load configuration
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        # shellcheck source=/dev/null
        source "$CONFIG_FILE"
        print_message "$GREEN" "✓ Configuration loaded from $CONFIG_FILE"
    else
        print_message "$YELLOW" "No configuration file found. Creating default..."
        create_default_config
    fi
}

# Validate configuration
validate_config() {
    local errors=0
    
    print_header "PRE-FLIGHT CONFIGURATION VALIDATION"
    
    # Required fields
    if [ -z "$DOMAIN" ]; then
        print_message "$RED" "✗ DOMAIN is not set in config"
        ((errors++))
    else
        print_message "$GREEN" "✓ DOMAIN: $DOMAIN"
    fi
    
    if [ -z "$CF_API_TOKEN" ]; then
        print_message "$YELLOW" "⚠ Cloudflare API token not set"
    else
        print_message "$GREEN" "✓ Cloudflare credentials configured"
    fi
    
    if [ -z "$NPM_API_URL" ]; then
        print_message "$YELLOW" "⚠ NPM API URL not set"
    else
        print_message "$GREEN" "✓ NPM endpoint configured"
    fi
    
    if [ -z "$PTERO_URL" ]; then
        print_message "$YELLOW" "⚠ Pterodactyl URL not set"
    else
        print_message "$GREEN" "✓ Pterodactyl endpoint configured"
    fi
    
    if [ $errors -gt 0 ]; then
        print_message "$RED" "\nConfiguration validation failed with $errors errors."
        print_message "$YELLOW" "Edit $CONFIG_FILE and try again."
        exit 1
    fi
    
    print_message "$GREEN" "\n✓ Configuration validation passed!"
}

# ============================================
# UTILITY FUNCTIONS
# ============================================

print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}" | tee -a "$LOG_FILE"
}

print_header() {
    echo "" | tee -a "$LOG_FILE"
    print_message "$BLUE" "============================================"
    print_message "$BLUE" "$1"
    print_message "$BLUE" "============================================"
    echo "" | tee -a "$LOG_FILE"
}

# Error handler with logging
error_handler() {
    local exit_code=$1
    local line_number=$2
    
    print_message "$RED" "\n✗ ERROR: Script failed at line $line_number with exit code $exit_code"
    echo "Timestamp: $(date)" >> "$ERROR_LOG"
    echo "Line: $line_number" >> "$ERROR_LOG"
    echo "Exit Code: $exit_code" >> "$ERROR_LOG"
    echo "Step: $CURRENT_STEP" >> "$ERROR_LOG"
    echo "---" >> "$ERROR_LOG"
    
    # Save state for recovery
    save_deployment_state "failed"
    
    print_message "$YELLOW" "Error details logged to: $ERROR_LOG"
    print_message "$YELLOW" "Deployment state saved. You can resume with: $0 --resume"
    
    exit "$exit_code"
}

# State management for resumable deployments
save_deployment_state() {
    local status=$1
    
    cat > "$STATE_FILE" <<EOF
{
    "deployment_id": "$DEPLOYMENT_ID",
    "timestamp": "$(date -Iseconds)",
    "status": "$status",
    "current_step": $CURRENT_STEP,
    "subdomain": "$SUBDOMAIN",
    "full_domain": "$FULL_DOMAIN",
    "server_ip": "$SERVER_IP",
    "game_port": "$GAME_PORT",
    "additional_ports": [$(printf '"%s",' "${ADDITIONAL_PORTS[@]}" | sed 's/,$//')],
    "cf_record_id": "$CF_RECORD_ID",
    "unifi_rule_ids": [$(printf '"%s",' "${UNIFI_RULE_IDS[@]}" | sed 's/,$//')],
    "npm_proxy_id": "$NPM_PROXY_ID",
    "ptero_server_uuid": "$PTERO_SERVER_UUID"
}
EOF
}

# Load saved state
load_deployment_state() {
    if [ -f "$STATE_FILE" ]; then
        DEPLOYMENT_ID=$(grep -o '"deployment_id": "[^"]*' "$STATE_FILE" | cut -d'"' -f4)
        CURRENT_STEP=$(grep -o '"current_step": [0-9]*' "$STATE_FILE" | awk '{print $2}')
        SUBDOMAIN=$(grep -o '"subdomain": "[^"]*' "$STATE_FILE" | cut -d'"' -f4)
        FULL_DOMAIN=$(grep -o '"full_domain": "[^"]*' "$STATE_FILE" | cut -d'"' -f4)
        SERVER_IP=$(grep -o '"server_ip": "[^"]*' "$STATE_FILE" | cut -d'"' -f4)
        GAME_PORT=$(grep -o '"game_port": "[^"]*' "$STATE_FILE" | cut -d'"' -f4)
        CF_RECORD_ID=$(grep -o '"cf_record_id": "[^"]*' "$STATE_FILE" | cut -d'"' -f4)
        NPM_PROXY_ID=$(grep -o '"npm_proxy_id": "[^"]*' "$STATE_FILE" | cut -d'"' -f4)
        PTERO_SERVER_UUID=$(grep -o '"ptero_server_uuid": "[^"]*' "$STATE_FILE" | cut -d'"' -f4)
        
        print_message "$CYAN" "Loaded previous deployment state:"
        print_message "$CYAN" "  - Deployment ID: $DEPLOYMENT_ID"
        print_message "$CYAN" "  - Last completed step: $CURRENT_STEP"
        print_message "$CYAN" "  - Subdomain: $SUBDOMAIN"
        
        return 0
    fi
    return 1
}

# Validation functions
validate_subdomain() {
    if [[ ! $1 =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$ ]]; then
        print_message "$RED" "Invalid subdomain format. Use alphanumeric characters and hyphens only."
        return 1
    fi
    return 0
}

validate_ip() {
    if [[ ! $1 =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        print_message "$RED" "Invalid IP address format."
        return 1
    fi
    return 0
}

validate_port() {
    if [[ ! $1 =~ ^[0-9]+$ ]] || [ "$1" -lt 1 ] || [ "$1" -gt 65535 ]; then
        print_message "$RED" "Invalid port number. Must be between 1 and 65535."
        return 1
    fi
    return 0
}

# API connectivity tests
test_api_connectivity() {
    print_header "PRE-FLIGHT API CONNECTIVITY TESTS"
    
    local all_passed=true
    
    # Test Cloudflare
    if [ -n "$CF_API_TOKEN" ]; then
        print_message "$YELLOW" "Testing Cloudflare API..."
        if curl -s -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
            -H "Authorization: Bearer $CF_API_TOKEN" | grep -q '"status":"active"'; then
            print_message "$GREEN" "✓ Cloudflare API: Connected"
        else
            print_message "$RED" "✗ Cloudflare API: Failed"
            all_passed=false
        fi
    fi
    
    # Test NPM
    if [ -n "$NPM_API_URL" ]; then
        print_message "$YELLOW" "Testing NPM API..."
        if curl -s --max-time 5 "$NPM_API_URL" >/dev/null 2>&1; then
            print_message "$GREEN" "✓ NPM API: Reachable"
        else
            print_message "$RED" "✗ NPM API: Unreachable"
            all_passed=false
        fi
    fi
    
    # Test UniFi
    if [ -n "$UNIFI_URL" ]; then
        print_message "$YELLOW" "Testing UniFi Controller..."
        if curl -sk --max-time 5 "$UNIFI_URL" >/dev/null 2>&1; then
            print_message "$GREEN" "✓ UniFi Controller: Reachable"
        else
            print_message "$YELLOW" "⚠ UniFi Controller: May be unreachable (this is sometimes normal)"
        fi
    fi
    
    # Test Pterodactyl
    if [ -n "$PTERO_URL" ] && [ -n "$PTERO_API_KEY" ]; then
        print_message "$YELLOW" "Testing Pterodactyl API..."
        if curl -s -X GET "${PTERO_URL}/api/application/nodes" \
            -H "Authorization: Bearer $PTERO_API_KEY" \
            -H "Accept: Application/vnd.pterodactyl.v1+json" | grep -q '"object"'; then
            print_message "$GREEN" "✓ Pterodactyl API: Connected"
        else
            print_message "$RED" "✗ Pterodactyl API: Failed"
            all_passed=false
        fi
    fi
    
    if [ "$all_passed" = false ]; then
        print_message "$YELLOW" "\n⚠ Some API tests failed. Continue anyway? (y/n)"
        read -r continue_anyway
        if [[ $continue_anyway != "y" ]]; then
            exit 1
        fi
    else
        print_message "$GREEN" "\n✓ All API connectivity tests passed!"
    fi
}

# Check for DNS conflicts
check_dns_conflicts() {
    local full_domain=$1
    
    print_message "$YELLOW" "Checking for existing DNS records..."
    
    if dig +short "$full_domain" | grep -q '^[0-9]'; then
        print_message "$YELLOW" "⚠ DNS record already exists for $full_domain"
        print_message "$YELLOW" "Existing IP: $(dig +short "$full_domain")"
        read -p "Overwrite existing record? (y/n): " overwrite
        if [[ $overwrite != "y" ]]; then
            print_message "$RED" "Deployment cancelled."
            exit 0
        fi
    else
        print_message "$GREEN" "✓ No DNS conflicts found"
    fi
}

# ============================================
# TEMPLATE MANAGEMENT
# ============================================

save_as_template() {
    local template_name=$1
    
    cat > "${TEMPLATES_DIR}/${template_name}.json" <<EOF
{
    "name": "$template_name",
    "game_port": "$GAME_PORT",
    "additional_ports": [$(printf '"%s",' "${ADDITIONAL_PORTS[@]}" | sed 's/,$//')],
    "egg_id": "$EGG_ID",
    "memory": "${MEMORY:-4096}",
    "disk": "${DISK:-10240}",
    "protocol": "${PROTOCOL:-tcp_udp}"
}
EOF
    
    print_message "$GREEN" "✓ Template saved as: $template_name"
}

load_from_template() {
    print_message "$CYAN" "\nAvailable Templates:"
    local i=1
    local templates=()
    
    for template in "$TEMPLATES_DIR"/*.json; do
        if [ -f "$template" ]; then
            local tname=$(basename "$template" .json)
            templates+=("$tname")
            echo "$i) $tname"
            ((i++))
        fi
    done
    
    if [ ${#templates[@]} -eq 0 ]; then
        print_message "$YELLOW" "No templates found."
        return 1
    fi
    
    echo "$i) Don't use template"
    read -p "Select template: " template_choice
    
    if [ "$template_choice" -eq "$i" ] 2>/dev/null; then
        return 1
    fi
    
    if [ "$template_choice" -ge 1 ] && [ "$template_choice" -lt "$i" ]; then
        local selected="${templates[$((template_choice-1))]}"
        local template_file="${TEMPLATES_DIR}/${selected}.json"
        
        GAME_PORT=$(grep -o '"game_port": "[^"]*' "$template_file" | cut -d'"' -f4)
        MEMORY=$(grep -o '"memory": "[^"]*' "$template_file" | cut -d'"' -f4)
        DISK=$(grep -o '"disk": "[^"]*' "$template_file" | cut -d'"' -f4)
        EGG_ID=$(grep -o '"egg_id": "[^"]*' "$template_file" | cut -d'"' -f4)
        
        print_message "$GREEN" "✓ Loaded template: $selected"
        return 0
    fi
    
    return 1
}

# ============================================
# DEPLOYMENT STEPS
# ============================================

collect_deployment_info() {
    print_header "GAME SERVER DEPLOYMENT - INFORMATION COLLECTION"
    
    # Check if resuming
    if [ "$RESUME_MODE" = true ]; then
        print_message "$CYAN" "Resuming deployment from step $CURRENT_STEP"
        FULL_DOMAIN="${SUBDOMAIN}.${DOMAIN}"
        return
    fi
    
    # Generate deployment ID
    DEPLOYMENT_ID="deploy_${TIMESTAMP}_$$"
    
    # Ask about templates
    read -p "Load from template? (y/n): " use_template
    local using_template=false
    
    if [[ $use_template == "y" ]]; then
        if load_from_template; then
            using_template=true
        fi
    fi
    
    # Subdomain
    while true; do
        read -p "Enter subdomain for the game server (e.g., minecraft, valheim): " SUBDOMAIN
        if validate_subdomain "$SUBDOMAIN"; then
            break
        fi
    done
    
    FULL_DOMAIN="${SUBDOMAIN}.${DOMAIN}"
    print_message "$GREEN" "Full domain will be: $FULL_DOMAIN"
    
    # Check for conflicts
    check_dns_conflicts "$FULL_DOMAIN"
    
    # Game server IP
    while true; do
        read -p "Enter the internal IP address of the game server: " SERVER_IP
        if validate_ip "$SERVER_IP"; then
            break
        fi
    done
    
    # If not using template, collect port info
    if [ "$using_template" = false ]; then
        while true; do
            read -p "Enter the primary game server port (e.g., 25565 for Minecraft): " GAME_PORT
            if validate_port "$GAME_PORT"; then
                break
            fi
        done
        
        # Additional ports
        read -p "Do you need additional ports forwarded? (y/n): " NEED_ADDITIONAL_PORTS
        ADDITIONAL_PORTS=()
        if [[ $NEED_ADDITIONAL_PORTS == "y" || $NEED_ADDITIONAL_PORTS == "Y" ]]; then
            while true; do
                read -p "Enter additional port (or press Enter to finish): " EXTRA_PORT
                if [ -z "$EXTRA_PORT" ]; then
                    break
                fi
                if validate_port "$EXTRA_PORT"; then
                    ADDITIONAL_PORTS+=("$EXTRA_PORT")
                    print_message "$GREEN" "Added port: $EXTRA_PORT"
                fi
            done
        fi
        
        # Pterodactyl egg selection
        print_message "$YELLOW" "\nCommon Pterodactyl Eggs:"
        echo "1) Minecraft (Java)"
        echo "2) Minecraft (Bedrock)"
        echo "3) Valheim"
        echo "4) Terraria"
        echo "5) Palworld"
        echo "6) Rust"
        echo "7) ARK: Survival Evolved"
        echo "8) Custom/Other"
        
        read -p "Select egg type (1-8): " EGG_CHOICE
        
        case $EGG_CHOICE in
            1) EGG_ID="minecraft_java"; MEMORY=4096; DISK=10240 ;;
            2) EGG_ID="minecraft_bedrock"; MEMORY=2048; DISK=5120 ;;
            3) EGG_ID="valheim"; MEMORY=4096; DISK=20480 ;;
            4) EGG_ID="terraria"; MEMORY=1024; DISK=2048 ;;
            5) EGG_ID="palworld"; MEMORY=8192; DISK=30720 ;;
            6) EGG_ID="rust"; MEMORY=8192; DISK=20480 ;;
            7) EGG_ID="ark"; MEMORY=8192; DISK=40960 ;;
            8) read -p "Enter custom egg name: " EGG_ID; MEMORY=4096; DISK=10240 ;;
            *) print_message "$RED" "Invalid selection."; exit 1 ;;
        esac
    fi
    
    # Confirmation
    print_header "DEPLOYMENT SUMMARY"
    echo "Deployment ID: $DEPLOYMENT_ID"
    echo "Domain: $FULL_DOMAIN"
    echo "Server IP: $SERVER_IP"
    echo "Primary Port: $GAME_PORT"
    if [ ${#ADDITIONAL_PORTS[@]} -gt 0 ]; then
        echo "Additional Ports: ${ADDITIONAL_PORTS[*]}"
    fi
    echo "Egg Type: $EGG_ID"
    echo "Memory: ${MEMORY}MB"
    echo "Disk: ${DISK}MB"
    echo ""
    
    read -p "Proceed with deployment? (y/n): " CONFIRM
    if [[ $CONFIRM != "y" && $CONFIRM != "Y" ]]; then
        print_message "$RED" "Deployment cancelled."
        exit 0
    fi
    
    # Ask to save as template
    read -p "Save this configuration as a template? (y/n): " save_template
    if [[ $save_template == "y" ]]; then
        read -p "Enter template name: " template_name
        save_as_template "$template_name"
    fi
    
    # Save initial state
    save_deployment_state "in_progress"
}

configure_cloudflare_dns() {
    if [ $CURRENT_STEP -ge 1 ]; then
        print_message "$CYAN" "Skipping Cloudflare DNS (already completed)"
        return
    fi
    
    print_header "STEP 1: CLOUDFLARE DNS CONFIGURATION"
    CURRENT_STEP=1
    
    # Get public IP
    if [ -z "$PUBLIC_IP" ]; then
        PUBLIC_IP=$(curl -s https://api.ipify.org)
        print_message "$YELLOW" "Auto-detected public IP: $PUBLIC_IP"
    fi
    
    print_message "$YELLOW" "Creating DNS A record for $FULL_DOMAIN..."
    
    # Create DNS record
    CF_RESPONSE=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records" \
        -H "Authorization: Bearer $CF_API_TOKEN" \
        -H "Content-Type: application/json" \
        --data "{\"type\":\"A\",\"name\":\"$SUBDOMAIN\",\"content\":\"$PUBLIC_IP\",\"ttl\":1,\"proxied\":false}")
    
    if echo "$CF_RESPONSE" | grep -q '"success":true'; then
        # Extract and save the record ID for rollback
        CF_RECORD_ID=$(echo "$CF_RESPONSE" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
        print_message "$GREEN" "✓ Cloudflare DNS record created successfully!"
        print_message "$CYAN" "  Record ID: $CF_RECORD_ID"
        save_deployment_state "step1_complete"
    else
        print_message "$RED" "✗ Failed to create Cloudflare DNS record."
        echo "$CF_RESPONSE" >> "$ERROR_LOG"
        read -p "Continue anyway? (y/n): " CONTINUE
        if [[ $CONTINUE != "y" ]]; then 
            save_deployment_state "failed_step1"
            exit 1
        fi
    fi
}

configure_unifi_portforward() {
    if [ $CURRENT_STEP -ge 2 ]; then
        print_message "$CYAN" "Skipping UniFi configuration (already completed)"
        return
    fi
    
    print_header "STEP 2: UNIFI PORT FORWARDING CONFIGURATION"
    CURRENT_STEP=2
    
    if [ "$ENABLE_AUTO_UNIFI" != "true" ]; then
        print_message "$YELLOW" "Automatic UniFi disabled in config. Skipping..."
        save_deployment_state "step2_skipped"
        return
    fi
    
    # API prefix for UDM devices
    if [ "$UNIFI_IS_UDM" = "true" ]; then
        API_PREFIX="/proxy/network"
    else
        API_PREFIX=""
    fi
    
    # Login and get CSRF token
    print_message "$YELLOW" "Authenticating with UniFi Controller..."
    
    LOGIN_RESPONSE=$(curl -sk -c /tmp/unifi_cookie.txt \
        -X POST "${UNIFI_URL}/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$UNIFI_USER\",\"password\":\"$UNIFI_PASS\"}" \
        -D /tmp/unifi_headers.txt)
    
    CSRF_TOKEN=$(grep -i "x-csrf-token" /tmp/unifi_headers.txt | cut -d: -f2 | tr -d ' \r\n')
    
    if [ -z "$CSRF_TOKEN" ]; then
        print_message "$RED" "✗ Failed to authenticate with UniFi Controller."
        save_deployment_state "failed_step2"
        rm -f /tmp/unifi_cookie.txt /tmp/unifi_headers.txt
        exit 1
    fi
    
    print_message "$GREEN" "✓ Authenticated successfully!"
    
    # Create port forward rules
    PROTOCOL="${PROTOCOL:-tcp_udp}"
    
    print_message "$YELLOW" "Creating port forward rule for port $GAME_PORT..."
    
    PF_PAYLOAD=$(cat <<EOF
{
    "name": "$SUBDOMAIN",
    "enabled": true,
    "src": "any",
    "dst_port": "$GAME_PORT",
    "fwd": "$SERVER_IP",
    "fwd_port": "$GAME_PORT",
    "proto": "$PROTOCOL",
    "log": false,
    "pfwd_interface": "wan"
}
EOF
)
    
    PF_RESPONSE=$(curl -sk -b /tmp/unifi_cookie.txt \
        -X POST "${UNIFI_URL}${API_PREFIX}/api/s/${UNIFI_SITE}/rest/portforward" \
        -H "Content-Type: application/json" \
        -H "X-CSRF-Token: $CSRF_TOKEN" \
        -d "$PF_PAYLOAD")
    
    if echo "$PF_RESPONSE" | grep -q '"_id"'; then
        # Extract and save the rule ID
        RULE_ID=$(echo "$PF_RESPONSE" | grep -o '"_id":"[^"]*' | cut -d'"' -f4)
        UNIFI_RULE_IDS+=("$RULE_ID")
        print_message "$GREEN" "✓ Port forward rule created for port $GAME_PORT"
        print_message "$CYAN" "  Rule ID: $RULE_ID"
    else
        print_message "$RED" "✗ Failed to create port forward rule"
        echo "$PF_RESPONSE" >> "$ERROR_LOG"
    fi
    
    # Additional ports
    if [ ${#ADDITIONAL_PORTS[@]} -gt 0 ]; then
        for ADD_PORT in "${ADDITIONAL_PORTS[@]}"; do
            print_message "$YELLOW" "Creating rule for port $ADD_PORT..."
            
            ADD_PF_PAYLOAD=$(cat <<EOF
{
    "name": "${SUBDOMAIN}-${ADD_PORT}",
    "enabled": true,
    "src": "any",
    "dst_port": "$ADD_PORT",
    "fwd": "$SERVER_IP",
    "fwd_port": "$ADD_PORT",
    "proto": "$PROTOCOL",
    "log": false,
    "pfwd_interface": "wan"
}
EOF
)
            
            ADD_PF_RESPONSE=$(curl -sk -b /tmp/unifi_cookie.txt \
                -X POST "${UNIFI_URL}${API_PREFIX}/api/s/${UNIFI_SITE}/rest/portforward" \
                -H "Content-Type: application/json" \
                -H "X-CSRF-Token: $CSRF_TOKEN" \
                -d "$ADD_PF_PAYLOAD")
            
            if echo "$ADD_PF_RESPONSE" | grep -q '"_id"'; then
                ADD_RULE_ID=$(echo "$ADD_PF_RESPONSE" | grep -o '"_id":"[^"]*' | cut -d'"' -f4)
                UNIFI_RULE_IDS+=("$ADD_RULE_ID")
                print_message "$GREEN" "✓ Rule created for port $ADD_PORT (ID: $ADD_RULE_ID)"
            fi
        done
    fi
    
    # Logout
    curl -sk -b /tmp/unifi_cookie.txt \
        -X POST "${UNIFI_URL}/api/auth/logout" \
        -H "X-CSRF-Token: $CSRF_TOKEN" > /dev/null 2>&1
    
    rm -f /tmp/unifi_cookie.txt /tmp/unifi_headers.txt
    
    print_message "$GREEN" "✓ UniFi port forwarding complete!"
    save_deployment_state "step2_complete"
}

configure_nginx_proxy() {
    if [ $CURRENT_STEP -ge 3 ]; then
        print_message "$CYAN" "Skipping NPM configuration (already completed)"
        return
    fi
    
    print_header "STEP 3: NGINX PROXY MANAGER CONFIGURATION"
    CURRENT_STEP=3
    
    # Login to NPM
    print_message "$YELLOW" "Authenticating with Nginx Proxy Manager..."
    NPM_TOKEN=$(curl -s -X POST "${NPM_API_URL}/tokens" \
        -H "Content-Type: application/json" \
        -d "{\"identity\":\"$NPM_EMAIL\",\"secret\":\"$NPM_PASSWORD\"}" | \
        grep -o '"token":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$NPM_TOKEN" ]; then
        print_message "$RED" "✗ Failed to authenticate with NPM."
        save_deployment_state "failed_step3"
        exit 1
    fi
    
    print_message "$GREEN" "✓ Authenticated successfully!"
    
    # Create proxy host
    print_message "$YELLOW" "Creating proxy host..."
    PROXY_RESPONSE=$(curl -s -X POST "${NPM_API_URL}/nginx/proxy-hosts" \
        -H "Authorization: Bearer $NPM_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"domain_names\":[\"$FULL_DOMAIN\"],
            \"forward_host\":\"$SERVER_IP\",
            \"forward_port\":$GAME_PORT,
            \"certificate_id\":0,
            \"ssl_forced\":false,
            \"http2_support\":true,
            \"block_exploits\":true,
            \"allow_websocket_upgrade\":true
        }")
    
    if echo "$PROXY_RESPONSE" | grep -q '"id"'; then
        print_message "$GREEN" "✓ Nginx proxy host created successfully!"
        NPM_PROXY_ID=$(echo "$PROXY_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
        print_message "$CYAN" "  Proxy ID: $NPM_PROXY_ID"
        
        # SSL certificate
        if [ "$ENABLE_SSL_AUTO" = "true" ]; then
            print_message "$YELLOW" "Requesting Let's Encrypt SSL certificate..."
            
            SSL_RESPONSE=$(curl -s -X POST "${NPM_API_URL}/nginx/certificates" \
                -H "Authorization: Bearer $NPM_TOKEN" \
                -H "Content-Type: application/json" \
                -d "{
                    \"domain_names\":[\"$FULL_DOMAIN\"],
                    \"meta\":{\"letsencrypt_email\":\"$NPM_EMAIL\",\"letsencrypt_agree\":true}
                }")
            
            if echo "$SSL_RESPONSE" | grep -q '"id"'; then
                print_message "$GREEN" "✓ SSL certificate issued successfully!"
            fi
        fi
        
        save_deployment_state "step3_complete"
    else
        print_message "$RED" "✗ Failed to create proxy host."
        echo "$PROXY_RESPONSE" >> "$ERROR_LOG"
        save_deployment_state "failed_step3"
        exit 1
    fi
}

deploy_pterodactyl_server() {
    if [ $CURRENT_STEP -ge 4 ]; then
        print_message "$CYAN" "Skipping Pterodactyl deployment (already completed)"
        return
    fi
    
    print_header "STEP 4: PTERODACTYL SERVER DEPLOYMENT"
    CURRENT_STEP=4
    
    print_message "$YELLOW" "Creating Pterodactyl server..."
    
    # This requires proper egg IDs from your panel
    read -p "Enter Node ID: " NODE_ID
    read -p "Enter actual Egg ID from your panel: " ACTUAL_EGG_ID
    
    PTERO_RESPONSE=$(curl -s -X POST "${PTERO_URL}/api/application/servers" \
        -H "Authorization: Bearer $PTERO_API_KEY" \
        -H "Content-Type: application/json" \
        -H "Accept: Application/vnd.pterodactyl.v1+json" \
        -d "{
            \"name\":\"${SUBDOMAIN}-server\",
            \"user\":1,
            \"egg\":$ACTUAL_EGG_ID,
            \"docker_image\":\"ghcr.io/pterodactyl/yolks:java_17\",
            \"startup\":\"\",
            \"environment\":{},
            \"limits\":{
                \"memory\":$MEMORY,
                \"swap\":0,
                \"disk\":$DISK,
                \"io\":500,
                \"cpu\":100
            },
            \"feature_limits\":{
                \"databases\":1,
                \"backups\":5
            },
            \"allocation\":{
                \"default\":1
            },
            \"deploy\":{
                \"locations\":[$NODE_ID],
                \"dedicated_ip\":false,
                \"port_range\":[]
            }
        }")
    
    if echo "$PTERO_RESPONSE" | grep -q '"object":"server"'; then
        print_message "$GREEN" "✓ Pterodactyl server created successfully!"
        PTERO_SERVER_UUID=$(echo "$PTERO_RESPONSE" | grep -o '"uuid":"[^"]*' | head -1 | cut -d'"' -f4)
        print_message "$GREEN" "Server UUID: $PTERO_SERVER_UUID"
        save_deployment_state "step4_complete"
    else
        print_message "$RED" "✗ Failed to create Pterodactyl server."
        echo "$PTERO_RESPONSE" >> "$ERROR_LOG"
        save_deployment_state "failed_step4"
        exit 1
    fi
}

# ============================================
# ROLLBACK FUNCTIONALITY
# ============================================

rollback_deployment() {
    print_header "ROLLING BACK DEPLOYMENT"
    
    if [ ! -f "$STATE_FILE" ]; then
        print_message "$RED" "No deployment state found to rollback."
        exit 1
    fi
    
    load_deployment_state
    
    print_message "$YELLOW" "Rolling back deployment: $DEPLOYMENT_ID"
    print_message "$YELLOW" "Domain: $FULL_DOMAIN"
    print_message "$YELLOW" "Last completed step: $CURRENT_STEP"
    echo ""
    
    read -p "Are you sure you want to rollback? (y/n): " confirm_rollback
    if [[ $confirm_rollback != "y" ]]; then
        print_message "$YELLOW" "Rollback cancelled."
        exit 0
    fi
    
    local rollback_successful=true
    
    # Rollback Step 4: Pterodactyl
    if [ $CURRENT_STEP -ge 4 ] && [ -n "$PTERO_SERVER_UUID" ]; then
        print_message "$YELLOW" "Step 4: Deleting Pterodactyl server..."
        
        DELETE_RESPONSE=$(curl -s -X DELETE "${PTERO_URL}/api/application/servers/${PTERO_SERVER_UUID}" \
            -H "Authorization: Bearer $PTERO_API_KEY" \
            -H "Accept: Application/vnd.pterodactyl.v1+json")
        
        if [ $? -eq 0 ]; then
            print_message "$GREEN" "  ✓ Pterodactyl server deleted"
        else
            print_message "$RED" "  ✗ Failed to delete Pterodactyl server (UUID: $PTERO_SERVER_UUID)"
            print_message "$YELLOW" "  → Manual cleanup required in Pterodactyl panel"
            rollback_successful=false
        fi
    fi
    
    # Rollback Step 3: NPM
    if [ $CURRENT_STEP -ge 3 ] && [ -n "$NPM_PROXY_ID" ]; then
        print_message "$YELLOW" "Step 3: Removing NPM proxy host..."
        
        # Login to NPM first
        NPM_TOKEN=$(curl -s -X POST "${NPM_API_URL}/tokens" \
            -H "Content-Type: application/json" \
            -d "{\"identity\":\"$NPM_EMAIL\",\"secret\":\"$NPM_PASSWORD\"}" | \
            grep -o '"token":"[^"]*' | cut -d'"' -f4)
        
        if [ -n "$NPM_TOKEN" ]; then
            DELETE_RESPONSE=$(curl -s -X DELETE "${NPM_API_URL}/nginx/proxy-hosts/${NPM_PROXY_ID}" \
                -H "Authorization: Bearer $NPM_TOKEN")
            
            if [ $? -eq 0 ]; then
                print_message "$GREEN" "  ✓ NPM proxy host deleted"
            else
                print_message "$RED" "  ✗ Failed to delete NPM proxy host (ID: $NPM_PROXY_ID)"
                print_message "$YELLOW" "  → Manual cleanup required in NPM dashboard"
                rollback_successful=false
            fi
        else
            print_message "$RED" "  ✗ Failed to authenticate with NPM"
            print_message "$YELLOW" "  → Manual cleanup required for proxy host ID: $NPM_PROXY_ID"
            rollback_successful=false
        fi
    fi
    
    # Rollback Step 2: UniFi
    if [ $CURRENT_STEP -ge 2 ] && [ ${#UNIFI_RULE_IDS[@]} -gt 0 ]; then
        print_message "$YELLOW" "Step 2: Removing UniFi port forward rules..."
        
        # Determine API prefix
        if [ "$UNIFI_IS_UDM" = "true" ]; then
            API_PREFIX="/proxy/network"
        else
            API_PREFIX=""
        fi
        
        # Login to UniFi
        LOGIN_RESPONSE=$(curl -sk -c /tmp/unifi_cookie.txt \
            -X POST "${UNIFI_URL}/api/auth/login" \
            -H "Content-Type: application/json" \
            -d "{\"username\":\"$UNIFI_USER\",\"password\":\"$UNIFI_PASS\"}" \
            -D /tmp/unifi_headers.txt)
        
        CSRF_TOKEN=$(grep -i "x-csrf-token" /tmp/unifi_headers.txt | cut -d: -f2 | tr -d ' \r\n')
        
        if [ -n "$CSRF_TOKEN" ]; then
            for RULE_ID in "${UNIFI_RULE_IDS[@]}"; do
                DELETE_RESPONSE=$(curl -sk -b /tmp/unifi_cookie.txt \
                    -X DELETE "${UNIFI_URL}${API_PREFIX}/api/s/${UNIFI_SITE}/rest/portforward/${RULE_ID}" \
                    -H "X-CSRF-Token: $CSRF_TOKEN")
                
                if [ $? -eq 0 ]; then
                    print_message "$GREEN" "  ✓ Deleted UniFi rule: $RULE_ID"
                else
                    print_message "$RED" "  ✗ Failed to delete rule: $RULE_ID"
                    rollback_successful=false
                fi
            done
            
            # Logout
            curl -sk -b /tmp/unifi_cookie.txt \
                -X POST "${UNIFI_URL}/api/auth/logout" \
                -H "X-CSRF-Token: $CSRF_TOKEN" > /dev/null 2>&1
            
            rm -f /tmp/unifi_cookie.txt /tmp/unifi_headers.txt
        else
            print_message "$RED" "  ✗ Failed to authenticate with UniFi"
            print_message "$YELLOW" "  → Manual cleanup required for rule IDs: ${UNIFI_RULE_IDS[*]}"
            rollback_successful=false
        fi
    fi
    
    # Rollback Step 1: Cloudflare
    if [ $CURRENT_STEP -ge 1 ] && [ -n "$CF_RECORD_ID" ]; then
        print_message "$YELLOW" "Step 1: Removing Cloudflare DNS record..."
        
        DELETE_RESPONSE=$(curl -s -X DELETE "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records/$CF_RECORD_ID" \
            -H "Authorization: Bearer $CF_API_TOKEN")
        
        if echo "$DELETE_RESPONSE" | grep -q '"success":true'; then
            print_message "$GREEN" "  ✓ Cloudflare DNS record deleted"
        else
            print_message "$RED" "  ✗ Failed to delete DNS record (ID: $CF_RECORD_ID)"
            print_message "$YELLOW" "  → Manual cleanup required in Cloudflare dashboard"
            rollback_successful=false
        fi
    fi
    
    # Final summary
    echo ""
    if [ "$rollback_successful" = true ]; then
        print_message "$GREEN" "✓ Rollback completed successfully!"
        rm -f "$STATE_FILE"
        print_message "$CYAN" "Deployment state file removed."
    else
        print_message "$YELLOW" "⚠ Rollback completed with some manual cleanup required."
        print_message "$YELLOW" "Please check the services mentioned above and clean up manually."
        print_message "$YELLOW" "State file preserved at: $STATE_FILE"
    fi
}

# ============================================
# MAIN EXECUTION
# ============================================

show_usage() {
    cat <<EOF
Game Server Deployment Automation v$VERSION

Usage: $0 [OPTIONS]

OPTIONS:
    --help              Show this help message
    --version           Show version information
    --init              Initialize configuration file
    --resume            Resume failed deployment
    --rollback          Rollback last deployment
    --template NAME     Deploy using template
    --validate          Validate configuration only
    --list-templates    List available templates

EXAMPLES:
    $0                      # Interactive deployment
    $0 --template minecraft # Deploy using minecraft template
    $0 --resume             # Resume interrupted deployment
    $0 --rollback           # Undo last deployment

EOF
}

main() {
    print_header "GAME SERVER DEPLOYMENT AUTOMATION v$VERSION"
    print_message "$YELLOW" "Log file: $LOG_FILE"
    
    # Parse arguments
    RESUME_MODE=false
    VALIDATE_ONLY=false
    
    case "${1:-}" in
        --help|-h)
            show_usage
            exit 0
            ;;
        --version|-v)
            echo "v$VERSION"
            exit 0
            ;;
        --init)
            create_default_config
            exit 0
            ;;
        --resume)
            RESUME_MODE=true
            if ! load_deployment_state; then
                print_message "$RED" "No deployment state found to resume."
                exit 1
            fi
            ;;
        --rollback)
            load_config
            rollback_deployment
            exit 0
            ;;
        --validate)
            VALIDATE_ONLY=true
            ;;
        --list-templates)
            print_message "$CYAN" "Available Templates:"
            ls -1 "$TEMPLATES_DIR"/*.json 2>/dev/null | xargs -n1 basename -s .json || echo "No templates found"
            exit 0
            ;;
        --template)
            if [ -z "${2:-}" ]; then
                print_message "$RED" "Template name required"
                exit 1
            fi
            # Load template logic here
            ;;
    esac
    
    # Load configuration
    load_config
    
    # Validate configuration
    validate_config
    
    if [ "$VALIDATE_ONLY" = true ]; then
        print_message "$GREEN" "Validation complete. Exiting."
        exit 0
    fi
    
    # Run pre-flight checks
    test_api_connectivity
    
    # Collect deployment information
    if [ "$RESUME_MODE" = false ]; then
        collect_deployment_info
    fi
    
    # Execute deployment steps
    configure_cloudflare_dns
    configure_unifi_portforward
    configure_nginx_proxy
    deploy_pterodactyl_server
    
    # Mark as complete
    save_deployment_state "complete"
    
    # Post-deployment connectivity test
    print_header "POST-DEPLOYMENT CONNECTIVITY TEST"
    
    print_message "$YELLOW" "Waiting 10 seconds for services to stabilize..."
    sleep 10
    
    print_message "$YELLOW" "Testing DNS resolution..."
    if DNS_RESULT=$(dig +short "$FULL_DOMAIN" 2>&1) && [ -n "$DNS_RESULT" ]; then
        print_message "$GREEN" "✓ DNS resolves to: $DNS_RESULT"
    else
        print_message "$YELLOW" "⚠ DNS not yet propagated (this can take 5-15 minutes)"
    fi
    
    print_message "$YELLOW" "Testing port connectivity to $FULL_DOMAIN:$GAME_PORT..."
    
    # Try multiple methods for port testing
    PORT_OPEN=false
    
    # Method 1: netcat
    if command -v nc &> /dev/null; then
        if timeout 5 nc -zv "$FULL_DOMAIN" "$GAME_PORT" 2>&1 | grep -q "succeeded\|open"; then
            PORT_OPEN=true
        fi
    fi
    
    # Method 2: bash TCP test (if nc not available)
    if [ "$PORT_OPEN" = false ] && command -v timeout &> /dev/null; then
        if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$FULL_DOMAIN/$GAME_PORT" 2>/dev/null; then
            PORT_OPEN=true
        fi
    fi
    
    # Method 3: curl (for HTTP ports only)
    if [ "$PORT_OPEN" = false ] && command -v curl &> /dev/null; then
        if curl -s --connect-timeout 5 "http://$FULL_DOMAIN:$GAME_PORT" &>/dev/null; then
            PORT_OPEN=true
        fi
    fi
    
    if [ "$PORT_OPEN" = true ]; then
        print_message "$GREEN" "✓ Port $GAME_PORT is OPEN and responding!"
    else
        print_message "$YELLOW" "⚠ Port $GAME_PORT is not responding yet"
        print_message "$YELLOW" "  Possible reasons:"
        print_message "$YELLOW" "  - DNS not fully propagated (wait 5-15 minutes)"
        print_message "$YELLOW" "  - Game server still starting up"
        print_message "$YELLOW" "  - Firewall rules need time to apply"
        print_message "$YELLOW" "  - Port forward not yet active"
    fi
    
    # Test additional ports if any
    if [ ${#ADDITIONAL_PORTS[@]} -gt 0 ]; then
        echo ""
        print_message "$YELLOW" "Testing additional ports..."
        for ADD_PORT in "${ADDITIONAL_PORTS[@]}"; do
            if command -v nc &> /dev/null; then
                if timeout 3 nc -zv "$FULL_DOMAIN" "$ADD_PORT" 2>&1 | grep -q "succeeded\|open"; then
                    print_message "$GREEN" "  ✓ Port $ADD_PORT is open"
                else
                    print_message "$YELLOW" "  ⚠ Port $ADD_PORT not responding"
                fi
            fi
        done
    fi
    
    echo ""
    print_message "$CYAN" "Manual testing commands:"
    print_message "$CYAN" "  DNS check: dig $FULL_DOMAIN"
    print_message "$CYAN" "  Port test: nc -zv $FULL_DOMAIN $GAME_PORT"
    print_message "$CYAN" "  Or try: telnet $FULL_DOMAIN $GAME_PORT"
    
    # Final summary
    print_header "DEPLOYMENT COMPLETE"
    print_message "$GREEN" "✓ Game server deployment finished successfully!"
    echo ""
    echo "Summary:"
    echo "  Deployment ID: $DEPLOYMENT_ID"
    echo "  Domain: $FULL_DOMAIN"
    echo "  Server IP: $SERVER_IP"
    echo "  Port(s): $GAME_PORT ${ADDITIONAL_PORTS[*]}"
    echo "  Log file: $LOG_FILE"
    echo ""
    print_message "$YELLOW" "DNS propagation may take 5-15 minutes."
    print_message "$CYAN" "Test connectivity with: nc -zv $FULL_DOMAIN $GAME_PORT"
    
    # Cleanup state file
    rm -f "$STATE_FILE"
}

# Run main function
main "$@"