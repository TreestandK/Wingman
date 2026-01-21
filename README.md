# Complete Deployment Example - Start to Finish

This guide shows a real-world deployment from scratch, including what you'll see and what to expect.

## Scenario

**Goal:** Deploy a Minecraft Java server accessible at `minecraft.treestandk.com:25565`

**Infrastructure:**
- Game server VM: 192.168.1.50
- TrueNAS with NPM: 192.168.1.100
- UniFi Controller: 192.168.1.1
- Pterodactyl Panel: https://panel.treestandk.com

---

## Step 1: First-Time Setup (One Time Only)

```bash
# Download and setup script
cd ~
wget https://your-repo/gameserver-deploy.sh
chmod +x gameserver-deploy.sh

# Initialize configuration
./gameserver-deploy.sh --init
```

**Output:**
```
Created default configuration file at: /home/user/.gameserver-deploy/config.env
Please edit this file with your credentials before running the script.
```

---

## Step 2: Configure Credentials

```bash
nano ~/.gameserver-deploy/config.env
```

**Edit the file:**
```bash
DOMAIN="yourdomain.com"

# Cloudflare
CF_API_TOKEN="your_actual_token_here"
CF_ZONE_ID="your_zone_id_here"

# NPM
NPM_API_URL="http://npm_ip:81/api"
NPM_EMAIL="admin@treestandk.com"
NPM_PASSWORD="your_npm_password"

# UniFi
UNIFI_URL="https://unifi_ip"
UNIFI_USER="admin"
UNIFI_PASS="your_unifi_password"
UNIFI_SITE="default"
UNIFI_IS_UDM="false"

# Pterodactyl
PTERO_URL="https://YOUR_PANEL.com"
PTERO_API_KEY="ptla_your_api_key_here"

# Features
ENABLE_AUTO_UNIFI="true"
ENABLE_SSL_AUTO="true"
```

Save and exit (Ctrl+X, Y, Enter)

---

## Step 3: Validate Configuration

```bash
./gameserver-deploy.sh --validate
```

**Output:**
```
============================================
PRE-FLIGHT CONFIGURATION VALIDATION
============================================

✓ DOMAIN: treestandk.com
✓ Cloudflare credentials configured
✓ NPM endpoint configured
✓ Pterodactyl endpoint configured

✓ Configuration validation passed!

============================================
PRE-FLIGHT API CONNECTIVITY TESTS
============================================

Testing Cloudflare API...
✓ Cloudflare API: Connected

Testing NPM API...
✓ NPM API: Reachable

Testing UniFi Controller...
✓ UniFi Controller: Reachable

Testing Pterodactyl API...
✓ Pterodactyl API: Connected

✓ All API connectivity tests passed!
```

---

## Step 4: Deploy Your Server

```bash
./gameserver-deploy.sh
```

### Interactive Prompts

**Prompt 1: Templates**
```
Load from template? (y/n): n
```
*(First time, we don't have templates yet)*

**Prompt 2: Subdomain**
```
Enter subdomain for the game server (e.g., minecraft, valheim): minecraft
Full domain will be: minecraft.treestandk.com
Checking for existing DNS records...
✓ No DNS conflicts found
```

**Prompt 3: Server IP**
```
Enter the internal IP address of the game server: 192.168.1.50
```

**Prompt 4: Port**
```
Enter the primary game server port (e.g., 25565 for Minecraft): 25565
```

**Prompt 5: Additional Ports**
```
Do you need additional ports forwarded? (y/n): y
Enter additional port (or press Enter to finish): 25575
Added port: 25575
Enter additional port (or press Enter to finish): [Enter]
```

**Prompt 6: Game Type**
```
Common Pterodactyl Eggs:
1) Minecraft (Java)
2) Minecraft (Bedrock)
3) Valheim
...
Select egg type (1-8): 1
```

**Prompt 7: Confirmation**
```
============================================
DEPLOYMENT SUMMARY
============================================
Deployment ID: deploy_20260121_143052_12345
Domain: minecraft.treestandk.com
Server IP: 192.168.1.50
Primary Port: 25565
Additional Ports: 25575
Egg Type: minecraft_java
Memory: 4096MB
Disk: 10240MB

Proceed with deployment? (y/n): y
```

**Prompt 8: Save Template**
```
Save this configuration as a template? (y/n): y
Enter template name: minecraft-standard
✓ Template saved as: minecraft-standard
```

---

## Step 5: Deployment Progress

### Step 1: Cloudflare DNS
```
============================================
STEP 1: CLOUDFLARE DNS CONFIGURATION
============================================

Auto-detected public IP: 203.0.113.1
Creating DNS A record for minecraft.treestandk.com...
✓ Cloudflare DNS record created successfully!
  Record ID: abc123def456...
```

### Step 2: UniFi Port Forwarding
```
============================================
STEP 2: UNIFI PORT FORWARDING CONFIGURATION
============================================

Authenticating with UniFi Controller...
✓ Authenticated successfully!
Creating port forward rule for port 25565...
✓ Port forward rule created for port 25565
  Rule ID: 507f1f77bcf86cd799439011
Creating rule for port 25575...
✓ Rule created for port 25575 (ID: 507f191e810c19729de860ea)
✓ UniFi port forwarding complete!
```

### Step 3: Nginx Proxy Manager
```
============================================
STEP 3: NGINX PROXY MANAGER CONFIGURATION
============================================

Authenticating with Nginx Proxy Manager...
✓ Authenticated successfully!
Creating proxy host...
✓ Nginx proxy host created successfully!
  Proxy ID: 42
Requesting Let's Encrypt SSL certificate...
✓ SSL certificate issued successfully!
```

### Step 4: Pterodactyl Server
```
============================================
STEP 4: PTERODACTYL SERVER DEPLOYMENT
============================================

Creating Pterodactyl server...
Enter Node ID: 1
Enter actual Egg ID from your panel: 5
✓ Pterodactyl server created successfully!
Server UUID: 8a3d2f1e-4b6c-7d8e-9f0a-1b2c3d4e5f6a
```

---

## Step 6: Connectivity Testing

```
============================================
POST-DEPLOYMENT CONNECTIVITY TEST
============================================

Waiting 10 seconds for services to stabilize...

Testing DNS resolution...
✓ DNS resolves to: 203.0.113.1

Testing port connectivity to minecraft.treestandk.com:25565...
✓ Port 25565 is OPEN and responding!

Testing additional ports...
  ✓ Port 25575 is open

Manual testing commands:
  DNS check: dig minecraft.treestandk.com
  Port test: nc -zv minecraft.treestandk.com 25565
  Or try: telnet minecraft.treestandk.com 25565
```

---

## Step 7: Deployment Complete

```
============================================
DEPLOYMENT COMPLETE
============================================

✓ Game server deployment finished successfully!

Summary:
  Deployment ID: deploy_20260121_143052_12345
  Domain: minecraft.treestandk.com
  Server IP: 192.168.1.50
  Port(s): 25565 25575
  Log file: /home/user/.gameserver-deploy/logs/deployment_20260121_143052.log

DNS propagation may take 5-15 minutes.
Test connectivity with: nc -zv minecraft.treestandk.com 25565
```

---

## Step 8: Verify in Pterodactyl

1. Log into Pterodactyl panel: https://panel.treestandk.com
2. Navigate to your server: minecraft-server
3. Click "Start"
4. Wait for server to boot (check console)
5. Test connection: `minecraft.treestandk.com:25565`

---

## Next Time: Using the Template

For your second server, it's much faster:

```bash
./gameserver-deploy.sh

Load from template? (y/n): y

Available Templates:
1) minecraft-standard
Select template: 1

✓ Loaded template: minecraft-standard

Enter subdomain: minecraft2
Enter server IP: 192.168.1.51

[Rest auto-filled from template]
```

---

## If Something Goes Wrong

### Scenario: Network Hiccup During Deployment

```
Step 3: NPM configuration fails due to network timeout

✗ Failed to create proxy host.

# Fix network issue, then:
./gameserver-deploy.sh --resume

Loaded previous deployment state:
  - Deployment ID: deploy_20260121_143052_12345
  - Last completed step: 2
  - Subdomain: minecraft

Skipping Cloudflare DNS (already completed)
Skipping UniFi configuration (already completed)

# Continues from Step 3
```

### Scenario: Need to Undo Deployment

```bash
./gameserver-deploy.sh --rollback
```

**Output:**
```
============================================
ROLLING BACK DEPLOYMENT
============================================

Domain: minecraft.treestandk.com
Are you sure? (y/n): y

Step 4: Deleting Pterodactyl server...
  ✓ Pterodactyl server deleted

Step 3: Removing NPM proxy host...
  ✓ NPM proxy host deleted

Step 2: Removing UniFi port forward rules...
  ✓ Deleted UniFi rule: 507f1f77bcf86cd799439011
  ✓ Deleted UniFi rule: 507f191e810c19729de860ea

Step 1: Removing Cloudflare DNS record...
  ✓ Cloudflare DNS record deleted

✓ Rollback completed successfully!
```

---

## Troubleshooting Common Issues

### Issue 1: "Port not responding" in connectivity test

**Possible causes:**
1. DNS not propagated yet (wait 15 minutes)
2. Pterodactyl server still starting
3. Game server not configured to listen on correct port

**Solution:**
```bash
# Wait a bit, then test manually
sleep 300  # 5 minutes
nc -zv minecraft.treestandk.com 25565

# Check Pterodactyl console
# Verify server started successfully
```

### Issue 2: "Failed to authenticate with [Service]"

**Solution:**
```bash
# Re-validate configuration
./gameserver-deploy.sh --validate

# If test fails, check credentials
nano ~/.gameserver-deploy/config.env

# Test specific service manually
curl -X POST https://api.cloudflare.com/client/v4/user/tokens/verify \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Issue 3: "DNS record already exists"

**Two options:**

**Option A:** Let script overwrite
```
⚠ DNS record already exists for minecraft.treestandk.com
Overwrite existing record? (y/n): y
```

**Option B:** Delete manually first
```bash
# Delete from Cloudflare dashboard, then retry
```

---

## Pro Tips

### 1. Keep a Deployment Log
```bash
# Create a simple tracking file
echo "$(date): minecraft.treestandk.com deployed to 192.168.1.50" >> ~/deployments.log
```

### 2. Test Locally First
```bash
# Before deploying, test the server internally
nc -zv 192.168.1.50 25565
```

### 3. Batch Deploy Multiple Servers
```bash
# Create CSV: servers.csv
minecraft1,192.168.1.50,25565,minecraft-standard
minecraft2,192.168.1.51,25565,minecraft-standard
valheim,192.168.1.52,2456,valheim

# Deploy all (future feature, or loop manually)
for server in $(cat servers.csv); do
    IFS=',' read -r sub ip port tpl <<< "$server"
    # Use template deployment
done
```

### 4. Monitor Your Deployments
```bash
# Check recent deployments
ls -lt ~/.gameserver-deploy/logs/ | head -5

# Search for errors
grep -i error ~/.gameserver-deploy/logs/*.log

# View last deployment
tail -100 $(ls -t ~/.gameserver-deploy/logs/deployment_*.log | head -1)
```

---
