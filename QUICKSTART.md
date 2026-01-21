# Wingman - Quick Start Guide

Get Wingman running on TrueNAS SCALE in under 10 minutes!

## Choose Your Path

### Path A: TrueNAS SCALE (YAML) - 5 minutes ⚡
**Best for:** Production deployment with automatic updates

### Path B: Docker Compose - 3 minutes 🐳
**Best for:** Local testing and development

---

## Path A: TrueNAS SCALE Installation

### Step 1: Edit Configuration (2 minutes)

Download and edit `truenas/install.yaml`:

```bash
# Replace these values:
# 1. YOUR_CLOUDFLARE_API_TOKEN
# 2. YOUR_NPM_PASSWORD
# 3. YOUR_UNIFI_PASSWORD
# 4. YOUR_PTERODACTYL_API_KEY
# 5. CHANGE_THIS_TO_RANDOM_SECRET_KEY
# 6. YOUR_CLOUDFLARE_ZONE_ID
# 7. Your domain and IP addresses
```

### Step 2: Deploy (1 minute)

```bash
# Copy to TrueNAS
scp truenas/install.yaml root@YOUR-TRUENAS-IP:/tmp/

# SSH and deploy
ssh root@YOUR-TRUENAS-IP
kubectl apply -f /tmp/install.yaml
```

### Step 3: Access (30 seconds)

Open your browser:
```
http://YOUR-TRUENAS-IP:30500
```

### Step 4: Verify (1 minute)

In the Wingman web interface:
1. Go to **Settings** tab
2. Click **Test All APIs**
3. Verify all services are connected ✓

**Done!** 🎉

---

## Path B: Docker Compose Installation

### Step 1: Configure (2 minutes)

```bash
# Clone or download the repository
cd wingman

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### Step 2: Start (30 seconds)

```bash
docker-compose up -d
```

### Step 3: Access (30 seconds)

```
http://localhost:5000
```

**Done!** 🎉

---

## First Deployment

### Deploy Your First Game Server (2 minutes)

1. **Go to Deploy Server tab**

2. **Fill in the form:**
   - Subdomain: `minecraft`
   - Server IP: `192.168.1.100`
   - Game Type: Select `Minecraft (Java)`
   - Port: `25565` (auto-filled)

3. **Click "Deploy Server"**

4. **Watch the progress:**
   - ✓ Cloudflare DNS
   - ✓ UniFi Port Forwarding
   - ✓ Nginx Proxy Manager
   - ✓ Deployment Complete!

5. **Access your server:**
   ```
   minecraft.yourdomain.com:25565
   ```

### Create a Template (1 minute)

Save this configuration as a template:

1. Check **"Save as Template"**
2. Enter template name: `minecraft-default`
3. Deploy

Next time, just select this template from the **Templates** tab!

---

## Common Tasks

### Deploy Another Server

**Using Template:**
1. Templates tab → Use Template
2. Change subdomain and IP
3. Deploy

**From Scratch:**
1. Deploy Server tab
2. Fill form
3. Deploy

### View Deployments

**Deployments** tab shows:
- All active servers
- Deployment status
- Logs for each deployment
- Rollback option

### Rollback a Deployment

1. Go to **Deployments** tab
2. Find the deployment
3. Click **Rollback**
4. Confirm

All resources are automatically cleaned up!

### Check Monitoring

**Monitoring** tab shows:
- Total deployments
- Active servers
- Failed deployments
- Average deploy time

---

## Auto-Updates (TrueNAS Only)

### Enable Automatic Updates (5 minutes)

```bash
# Copy update script to TrueNAS
scp truenas/update-script.sh root@YOUR-TRUENAS-IP:/root/

# SSH to TrueNAS
ssh root@YOUR-TRUENAS-IP

# Make executable
chmod +x /root/update-script.sh

# Test it
/root/update-script.sh

# Schedule daily updates (3 AM)
crontab -e
# Add this line:
0 3 * * * /root/update-script.sh >> /var/log/wingman-update.log 2>&1
```

Now Wingman will automatically update every night!

---

## Troubleshooting

### Can't Access Web Interface

**Check if running:**
```bash
# TrueNAS
kubectl get pods -n wingman

# Docker Compose
docker-compose ps
```

**Check logs:**
```bash
# TrueNAS
kubectl logs -f deployment/wingman -n wingman

# Docker Compose
docker-compose logs -f
```

### API Tests Fail

1. Go to **Settings** tab
2. Click **Test All APIs**
3. Fix any failing services:
   - **Cloudflare**: Check API token and Zone ID
   - **NPM**: Verify URL and credentials
   - **UniFi**: Check if controller is accessible
   - **Pterodactyl**: Verify URL and API key

### Deployment Fails

1. Go to **Deployments** tab
2. Click **Logs** on the failed deployment
3. Review error message
4. Fix the issue (usually credentials or connectivity)
5. Try again or rollback

### Port Already in Use (Docker Compose)

Edit `docker-compose.yml`:
```yaml
ports:
  - "8080:5000"  # Change 5000 to any available port
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

---

## Next Steps

### Production Hardening

1. **Set up SSL/TLS:**
   - Put Wingman behind Nginx Proxy Manager
   - Enable automatic SSL certificates
   - Force HTTPS

2. **Backup Configuration:**
   ```bash
   # TrueNAS
   kubectl get all,secrets,pvc -n wingman -o yaml > wingman-backup.yaml
   ```

3. **Monitor Resources:**
   - Check memory/CPU usage
   - Adjust limits if needed
   - Enable monitoring features

4. **Security:**
   - Change default Flask secret key
   - Use strong passwords
   - Restrict network access
   - Regular updates

### Advanced Features

**Template Library:**
- Create templates for all your game types
- Share templates with team members
- Version control your templates

**Monitoring:**
- Enable advanced monitoring
- Set up alerts (future feature)
- Track deployment history

**API Integration:**
- Use the REST API for automation
- Build custom tools
- Integrate with other systems

---

## Support & Resources

### Documentation

- **[TRUENAS-INSTALL.md](TRUENAS-INSTALL.md)** - Complete TrueNAS guide
- **[README-DOCKER.md](README-DOCKER.md)** - Docker Compose guide
- **[BUILD-AND-PUBLISH.md](BUILD-AND-PUBLISH.md)** - Building custom images

### Getting Help

1. **Check the logs** (most issues are logged)
2. **Test connectivity** in Settings tab
3. **Review documentation** for your specific issue
4. **Check TrueNAS events:** `kubectl get events -n wingman`

### Common Issues

| Issue | Solution |
|-------|----------|
| Can't connect | Check firewall, verify port 30500 is open |
| API fails | Verify credentials in Settings tab |
| Deployment hangs | Check logs, verify external services are up |
| Out of memory | Increase resource limits in deployment |
| Storage full | Increase PVC size or clean old logs |

---

## Quick Reference

### TrueNAS Commands

```bash
# View all resources
kubectl get all -n wingman

# View logs
kubectl logs -f deployment/wingman -n wingman

# Restart deployment
kubectl rollout restart deployment/wingman -n wingman

# Update to latest image
kubectl set image deployment/wingman wingman=ghcr.io/YOUR-USERNAME/wingman:latest -n wingman

# Delete everything
kubectl delete namespace wingman
```

### Docker Compose Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Update
docker-compose pull
docker-compose up -d

# Remove everything including volumes
docker-compose down -v
```

### API Endpoints

```bash
# Health check
curl http://localhost:5000/health

# List deployments
curl http://localhost:5000/api/deployments

# Get deployment status
curl http://localhost:5000/api/deploy/DEPLOYMENT_ID/status

# List templates
curl http://localhost:5000/api/templates
```

---

## Success Checklist

After installation, you should have:

- ✅ Wingman web interface accessible
- ✅ All API tests passing (Settings tab)
- ✅ At least one successful deployment
- ✅ Template created and working
- ✅ Automatic updates configured (TrueNAS)
- ✅ Monitoring dashboard showing stats

**Congratulations!** You're now running Wingman! 🎮🚀

---

## What's Next?

1. **Deploy your game servers** - Start with your most common games
2. **Create templates** - Save time on future deployments
3. **Set up monitoring** - Keep track of your infrastructure
4. **Automate updates** - Keep Wingman current
5. **Share feedback** - Help improve Wingman

Enjoy automated game server management! 🎮
