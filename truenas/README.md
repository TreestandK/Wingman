# TrueNAS SCALE Deployment Files

This directory contains all necessary files for deploying Wingman on TrueNAS SCALE.

## Files Overview

### Configuration Files

- **`app.yaml`** - TrueNAS app metadata and configuration
- **`questions.yaml`** - GUI form for easy configuration in TrueNAS interface
- **`install.yaml`** - Complete Kubernetes manifest for quick deployment

### Kubernetes Manifests (charts/)

- **`deployment.yaml`** - Kubernetes Deployment configuration
- **`service.yaml`** - Kubernetes Service definition
- **`pvc.yaml`** - PersistentVolumeClaim definitions
- **`secret.yaml`** - Secret management for credentials
- **`values.yaml`** - Default values for Helm-style templating

### Automation

- **`update-script.sh`** - Automatic update script for cron jobs

## Quick Start

### 1. YAML Installation (Fastest)

```bash
# Copy the install file
scp install.yaml root@truenas-ip:/tmp/

# SSH to TrueNAS
ssh root@truenas-ip

# Edit credentials
nano /tmp/install.yaml

# Deploy
kubectl apply -f /tmp/install.yaml

# Check status
kubectl get pods -n wingman
```

Access at: `http://your-truenas-ip:30500`

### 2. Custom App Installation (GUI)

Use the `questions.yaml` file to configure Wingman through the TrueNAS web interface:

1. Navigate to **Apps** → **Custom App**
2. Fill in the form (questions.yaml defines the fields)
3. Install

### 3. Manual Kubernetes Deployment

Deploy individual manifests:

```bash
# Create namespace
kubectl create namespace wingman

# Apply all manifests
kubectl apply -f charts/secret.yaml -n wingman
kubectl apply -f charts/pvc.yaml -n wingman
kubectl apply -f charts/deployment.yaml -n wingman
kubectl apply -f charts/service.yaml -n wingman
```

## Automatic Updates

### Setup Cron Job

```bash
# Copy update script
scp update-script.sh root@truenas-ip:/root/
ssh root@truenas-ip chmod +x /root/update-script.sh

# Add to crontab (daily at 3 AM)
crontab -e
# Add: 0 3 * * * /root/update-script.sh >> /var/log/wingman-update.log 2>&1
```

### Manual Update

```bash
kubectl rollout restart deployment/wingman -n wingman
```

## Configuration

### Update Environment Variables

```bash
kubectl edit deployment wingman -n wingman
```

### Update Secrets

```bash
kubectl create secret generic wingman-secrets \
  --from-literal=cf-api-token=new-token \
  --from-literal=npm-password=new-password \
  --dry-run=client -o yaml | kubectl apply -f - -n wingman
```

## Monitoring

### View Logs

```bash
kubectl logs -f deployment/wingman -n wingman
```

### Check Status

```bash
kubectl get all -n wingman
```

### Health Check

```bash
curl http://localhost:30500/health
```

## Documentation

See [TRUENAS-INSTALL.md](../TRUENAS-INSTALL.md) for complete installation and troubleshooting guide.

## Directory Structure

```
truenas/
├── app.yaml              # TrueNAS app metadata
├── questions.yaml        # TrueNAS GUI configuration
├── install.yaml          # Complete Kubernetes deployment
├── update-script.sh      # Auto-update script
├── charts/               # Kubernetes manifests
│   ├── deployment.yaml   # Main deployment
│   ├── service.yaml      # Service definition
│   ├── pvc.yaml          # Storage claims
│   ├── secret.yaml       # Secrets template
│   └── values.yaml       # Default values
└── README.md            # This file
```

## Support

For issues:
1. Check logs: `kubectl logs -f deployment/wingman -n wingman`
2. Check events: `kubectl get events -n wingman`
3. Review [TRUENAS-INSTALL.md](../TRUENAS-INSTALL.md)
4. Test configuration in the Settings tab of the web UI
