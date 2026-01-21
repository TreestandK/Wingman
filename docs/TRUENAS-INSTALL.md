# Wingman - TrueNAS SCALE Installation Guide

This guide covers installing Wingman Game Server Manager on TrueNAS SCALE with automatic updates.

## Installation Methods

There are three ways to install Wingman on TrueNAS SCALE:

1. **YAML Installation** (Recommended) - Direct Kubernetes deployment
2. **Custom App via GUI** - Using TrueNAS web interface
3. **Helm Chart** - Using Helm package manager

---

## Method 1: YAML Installation (Recommended)

This method allows you to deploy Wingman directly using Kubernetes YAML files.

### Prerequisites

- TrueNAS SCALE 22.12 or later
- kubectl access to your TrueNAS cluster
- SSH access to TrueNAS

### Step 1: Prepare the Installation File

1. Copy the `truenas/install.yaml` file to your TrueNAS system:

```bash
scp truenas/install.yaml root@your-truenas-ip:/tmp/
```

Or create it manually on TrueNAS:

```bash
ssh root@your-truenas-ip
nano /tmp/wingman-install.yaml
# Paste the contents of truenas/install.yaml
```

### Step 2: Edit Configuration

Edit the YAML file to add your credentials:

```bash
nano /tmp/wingman-install.yaml
```

Update the following sections:

```yaml
# In the Secret section, replace:
stringData:
  cf-api-token: "YOUR_CLOUDFLARE_API_TOKEN"
  npm-password: "YOUR_NPM_PASSWORD"
  unifi-password: "YOUR_UNIFI_PASSWORD"
  ptero-api-key: "YOUR_PTERODACTYL_API_KEY"
  flask-secret-key: "CHANGE_THIS_TO_RANDOM_SECRET_KEY"

# In the Deployment section, update environment variables:
- name: DOMAIN
  value: "your-domain.com"
- name: CF_ZONE_ID
  value: "YOUR_CLOUDFLARE_ZONE_ID"
- name: NPM_API_URL
  value: "http://YOUR_NPM_IP:81/api"
- name: NPM_EMAIL
  value: "your-email@example.com"
- name: UNIFI_URL
  value: "https://YOUR_UNIFI_IP"
- name: PTERO_URL
  value: "https://YOUR_PTERODACTYL_URL"
```

### Step 3: Deploy Wingman

Apply the configuration:

```bash
kubectl apply -f /tmp/wingman-install.yaml
```

### Step 4: Verify Installation

Check the deployment status:

```bash
# Check if pods are running
kubectl get pods -n wingman

# Check service
kubectl get svc -n wingman

# View logs
kubectl logs -f deployment/wingman -n wingman
```

### Step 5: Access the Web Interface

Once the pod is running, access Wingman at:

```
http://your-truenas-ip:30500
```

---

## Method 2: Custom App via TrueNAS GUI

### Step 1: Access TrueNAS Apps

1. Log in to TrueNAS SCALE web interface
2. Navigate to **Apps** → **Available Applications**
3. Click **Custom App**

### Step 2: Configure the App

Fill in the following details:

**Application Name:** `wingman`

**Image Configuration:**
- Image repository: `ghcr.io/your-username/wingman`
- Image Tag: `latest`
- Image Pull Policy: `Always`

**Networking:**
- Add a Container Port:
  - Container Port: `5000`
  - Node Port: `30500`
  - Protocol: `TCP`

**Storage:**

Add three Host Path Volumes:

1. **Data Volume**
   - Host Path: `/mnt/your-pool/wingman/data`
   - Mount Path: `/app/data`

2. **Logs Volume**
   - Host Path: `/mnt/your-pool/wingman/logs`
   - Mount Path: `/app/logs`

3. **Templates Volume**
   - Host Path: `/mnt/your-pool/wingman/templates`
   - Mount Path: `/app/templates/saved`

**Environment Variables:**

Add the following environment variables:

| Variable | Value |
|----------|-------|
| DOMAIN | your-domain.com |
| CF_API_TOKEN | your_cloudflare_api_token |
| CF_ZONE_ID | your_cloudflare_zone_id |
| NPM_API_URL | http://npm-ip:81/api |
| NPM_EMAIL | admin@example.com |
| NPM_PASSWORD | your_npm_password |
| UNIFI_URL | https://unifi-ip |
| UNIFI_USER | admin |
| UNIFI_PASS | your_unifi_password |
| UNIFI_SITE | default |
| UNIFI_IS_UDM | false |
| PTERO_URL | https://panel.yourdomain.com |
| PTERO_API_KEY | your_pterodactyl_api_key |
| ENABLE_AUTO_UNIFI | true |
| ENABLE_SSL_AUTO | true |
| FLASK_SECRET_KEY | random-secret-key-here |

**Resources:**
- Memory Limit: `512Mi`
- CPU Limit: `1000m`

### Step 3: Install

Click **Install** and wait for the deployment to complete.

### Step 4: Access

Navigate to `http://your-truenas-ip:30500`

---

## Method 3: Helm Chart Installation

If you have Helm installed:

```bash
# Add the repository (when published)
helm repo add wingman https://your-repo-url
helm repo update

# Install with custom values
helm install wingman wingman/wingman \
  --namespace wingman \
  --create-namespace \
  --set config.domain=your-domain.com \
  --set secrets.cfApiToken=your-token \
  --set secrets.npmPassword=your-password \
  --set secrets.unifiPassword=your-password \
  --set secrets.pteroApiKey=your-key
```

---

## Automatic Updates

### Option 1: Scheduled Updates with Cron

1. Copy the update script to TrueNAS:

```bash
scp truenas/update-script.sh root@your-truenas-ip:/root/
ssh root@your-truenas-ip chmod +x /root/update-script.sh
```

2. Create a cron job for automatic updates:

```bash
ssh root@your-truenas-ip
crontab -e
```

Add this line to check for updates daily at 3 AM:

```
0 3 * * * /root/update-script.sh >> /var/log/wingman-update.log 2>&1
```

### Option 2: Manual Updates

Update the deployment manually:

```bash
# Using kubectl
kubectl rollout restart deployment/wingman -n wingman

# Or pull latest image and restart
kubectl set image deployment/wingman wingman=ghcr.io/your-username/wingman:latest -n wingman
kubectl rollout status deployment/wingman -n wingman
```

### Option 3: GitHub Actions Auto-build

The included GitHub Actions workflow (`.github/workflows/build-and-push.yml`) automatically:

- Builds Docker images on every push to main
- Tags images with version numbers
- Pushes to GitHub Container Registry
- Builds for multiple architectures (amd64, arm64)

To use this:

1. Push your code to GitHub
2. Enable GitHub Actions
3. Images will automatically build and push to `ghcr.io/your-username/wingman:latest`

With `imagePullPolicy: Always`, TrueNAS will automatically pull new images when the pod restarts.

---

## Configuration via TrueNAS GUI

If you installed via YAML or want to reconfigure:

### Update Environment Variables

```bash
# Edit the deployment
kubectl edit deployment wingman -n wingman

# Or use kubectl set env
kubectl set env deployment/wingman -n wingman \
  DOMAIN=new-domain.com \
  CF_API_TOKEN=new-token
```

### Update Secrets

```bash
# Update secrets
kubectl create secret generic wingman-secrets \
  --from-literal=cf-api-token=new-token \
  --from-literal=npm-password=new-password \
  --from-literal=unifi-password=new-password \
  --from-literal=ptero-api-key=new-key \
  --from-literal=flask-secret-key=new-secret \
  --dry-run=client -o yaml | kubectl apply -f - -n wingman

# Restart to pick up new secrets
kubectl rollout restart deployment/wingman -n wingman
```

---

## Storage Configuration

### Using TrueNAS Datasets

Create datasets for better management:

```bash
# Create datasets
zfs create your-pool/wingman
zfs create your-pool/wingman/data
zfs create your-pool/wingman/logs
zfs create your-pool/wingman/templates

# Set permissions
chmod -R 755 /mnt/your-pool/wingman
```

### Using PVCs (Recommended)

The YAML installation automatically creates PersistentVolumeClaims:

- `wingman-data` - 1Gi
- `wingman-logs` - 2Gi
- `wingman-templates` - 512Mi

To resize:

```bash
# Edit PVC
kubectl edit pvc wingman-data -n wingman

# Change storage size
spec:
  resources:
    requests:
      storage: 5Gi
```

---

## Monitoring and Troubleshooting

### View Logs

```bash
# Real-time logs
kubectl logs -f deployment/wingman -n wingman

# Last 100 lines
kubectl logs --tail=100 deployment/wingman -n wingman

# Logs from specific pod
kubectl logs -f pod/wingman-xxxxx-xxxxx -n wingman
```

### Check Pod Status

```bash
# Get pod status
kubectl get pods -n wingman

# Describe pod for details
kubectl describe pod wingman-xxxxx-xxxxx -n wingman

# Check events
kubectl get events -n wingman --sort-by='.lastTimestamp'
```

### Access Pod Shell

```bash
kubectl exec -it deployment/wingman -n wingman -- /bin/bash
```

### Check Service

```bash
# Get service details
kubectl get svc wingman -n wingman

# Test connectivity from within TrueNAS
curl http://localhost:30500/health
```

### Common Issues

**Pod won't start:**
```bash
# Check pod events
kubectl describe pod wingman-xxxxx-xxxxx -n wingman

# Check if image can be pulled
kubectl get events -n wingman | grep -i pull
```

**Can't access web interface:**
```bash
# Check if service is running
kubectl get svc -n wingman

# Check if pod is ready
kubectl get pods -n wingman

# Verify port is listening
netstat -tlnp | grep 30500
```

**Storage issues:**
```bash
# Check PVC status
kubectl get pvc -n wingman

# Check if volumes are mounted
kubectl describe pod wingman-xxxxx-xxxxx -n wingman | grep -A5 Mounts
```

---

## Backup and Restore

### Backup Configuration

```bash
# Backup all Wingman resources
kubectl get all,secrets,pvc -n wingman -o yaml > wingman-backup.yaml

# Backup just the data
kubectl exec deployment/wingman -n wingman -- tar czf /tmp/backup.tar.gz /app/data /app/templates/saved
kubectl cp wingman/wingman-xxxxx-xxxxx:/tmp/backup.tar.gz ./wingman-backup.tar.gz
```

### Restore from Backup

```bash
# Restore resources
kubectl apply -f wingman-backup.yaml

# Restore data
kubectl cp ./wingman-backup.tar.gz wingman/wingman-xxxxx-xxxxx:/tmp/
kubectl exec deployment/wingman -n wingman -- tar xzf /tmp/backup.tar.gz -C /
```

---

## Uninstallation

### Complete Removal

```bash
# Delete all resources
kubectl delete namespace wingman

# Or if using default namespace
kubectl delete -f /tmp/wingman-install.yaml

# Remove data directories (if using host paths)
rm -rf /mnt/your-pool/wingman
```

### Keep Data, Remove Application

```bash
# Delete deployment and service only
kubectl delete deployment wingman -n wingman
kubectl delete service wingman -n wingman

# PVCs remain for later use
```

---

## Performance Tuning

### Resource Limits

Adjust based on your workload:

```bash
kubectl set resources deployment wingman -n wingman \
  --limits=cpu=2000m,memory=1Gi \
  --requests=cpu=500m,memory=256Mi
```

### Horizontal Scaling

Not recommended for Wingman (stateful app), but possible:

```bash
kubectl scale deployment wingman -n wingman --replicas=2
```

---

## Security Best Practices

1. **Use Secrets**: Never put passwords in environment variables directly
2. **Network Policies**: Restrict access to Wingman pod
3. **RBAC**: Use proper service accounts
4. **TLS**: Put Wingman behind a reverse proxy with SSL
5. **Updates**: Keep the image updated regularly

---

## Getting Help

- Check logs: `kubectl logs -f deployment/wingman -n wingman`
- Check events: `kubectl get events -n wingman`
- Test configuration: Use the Settings tab in the web UI
- Review this guide: Ensure all steps were followed

---

## Next Steps

After installation:

1. Access the web interface at `http://your-truenas-ip:30500`
2. Go to **Settings** tab and test API connectivity
3. Create your first game server deployment
4. Set up templates for frequently used configurations
5. Schedule automatic updates (optional)

Enjoy automated game server management with Wingman!
