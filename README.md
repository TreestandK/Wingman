# 🎮 Wingman - Game Server Manager

**Automated game server deployment and management system with a beautiful web interface.**

Transform your game server infrastructure management from command-line scripts to a modern, web-based automation platform with real-time monitoring, one-click deployments, and automatic rollback capabilities.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![TrueNAS](https://img.shields.io/badge/TrueNAS-SCALE-green)
![Docker](https://img.shields.io/badge/docker-compose-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

### 🖥️ Modern Web Interface
- Beautiful, responsive dark-themed UI
- Real-time deployment progress tracking
- Interactive deployment dashboard
- Mobile-friendly design

### 🚀 Automated Deployments
- One-click game server deployments
- Automatic Cloudflare DNS configuration
- UniFi port forwarding automation
- Nginx Proxy Manager integration
- Pterodactyl panel support

### 📋 Template Management
- Save server configurations as templates
- Quick deployment from saved templates
- Share templates across your team
- Pre-configured templates for popular games

### 📊 Monitoring & Management
- Real-time deployment monitoring
- Detailed deployment logs
- One-click rollback functionality
- System statistics dashboard
- API connectivity testing

### 🔧 Infrastructure Integration
- **Cloudflare** - Automatic DNS management
- **UniFi** - Port forwarding automation
- **Nginx Proxy Manager** - Reverse proxy setup
- **Pterodactyl** - Game panel integration
- **Let's Encrypt** - Automatic SSL certificates

---

## 🎮 Supported Games

Pre-configured templates included for:

- **Minecraft** (Java & Bedrock)
- **Valheim**
- **Terraria**
- **Palworld**
- **Rust**
- **ARK: Survival Evolved**
- **Custom games** - Configure any game server

---

## 🚀 Quick Start

### For TrueNAS SCALE Users

```bash
# 1. Download install.yaml
wget https://github.com/your-repo/wingman/raw/main/truenas/install.yaml

# 2. Edit credentials
nano install.yaml

# 3. Deploy
kubectl apply -f install.yaml

# 4. Access
# http://your-truenas-ip:30500
```

**📖 See [Quick Start Guide](QUICK_START.md) for detailed 5-minute setup guide**

### For Docker Compose Users

```bash
# 1. Clone repository
git clone https://github.com/your-repo/wingman.git
cd wingman

# 2. Configure
cp .env.example .env
nano .env

# 3. Start
docker-compose up -d

# 4. Access
# http://localhost:5000
```

---

## 📚 Documentation

**📖 [View Complete Documentation Index](docs/README.md)**

### Getting Started
- **[Quick Start Guide](QUICK_START.md)** - Get running in 5 minutes ⚡
- **[Docker Guide](docs/DOCKER.md)** - Complete Docker deployment guide
- **[TrueNAS Guide](docs/TRUENAS.md)** - TrueNAS SCALE installation
- **[Authentication Setup](docs/AUTHENTICATION.md)** - User management & RBAC

### Features & Integration
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Deploy and manage game servers
- **[Pterodactyl Integration](docs/PTERODACTYL.md)** - Configure Pterodactyl panel

### Troubleshooting & Support
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions ⭐
- **[TrueNAS Files Reference](truenas/README.md)** - Kubernetes deployment files

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│           Web Browser (Port 5000/30500)         │
└────────────────────┬────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────┐
│              Flask Web Application              │
│  • REST API                                     │
│  • Real-time monitoring                         │
│  • Template management                          │
└────────────────────┬────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────┐
│           Deployment Manager (Python)           │
│  • Orchestrates all operations                 │
│  • State management                             │
│  • Rollback handling                            │
└──────┬──────┬──────┬──────┬─────────────────────┘
       │      │      │      │
       ↓      ↓      ↓      ↓
    ┌────┐ ┌────┐ ┌──────┐ ┌────────────┐
    │ CF │ │NPM │ │UniFi │ │Pterodactyl │
    └────┘ └────┘ └──────┘ └────────────┘
```

---

## 📦 Installation Options

### Option 1: TrueNAS SCALE (Recommended for Production)

**Kubernetes-based deployment with:**
- Automatic updates
- Health monitoring
- Persistent storage
- Web GUI configuration
- High availability support

**Installation:** See [TrueNAS Guide](docs/TRUENAS.md)

### Option 2: Docker Compose (Recommended for Testing)

**Container-based deployment with:**
- Quick setup
- Easy configuration
- Local development
- Volume persistence

**Installation:** See [Docker Guide](docs/DOCKER.md)

### Option 3: Manual Installation

Deploy individual components manually for custom setups.

---

## ⚙️ Configuration

### Required Services

1. **Cloudflare** (DNS Management)
   - API Token with Zone.DNS edit permissions
   - Zone ID for your domain

2. **Nginx Proxy Manager** (Reverse Proxy)
   - API access credentials
   - Accessible API endpoint

3. **UniFi Controller** (Port Forwarding) - Optional
   - Admin credentials
   - Controller URL

4. **Pterodactyl Panel** (Game Hosting) - Optional
   - Application API key
   - Panel URL

### Environment Variables

```bash
# Domain
DOMAIN=yourdomain.com

# Cloudflare
CF_API_TOKEN=your_token
CF_ZONE_ID=your_zone_id

# Nginx Proxy Manager
NPM_API_URL=http://npm:81/api
NPM_EMAIL=admin@example.com
NPM_PASSWORD=password

# UniFi
UNIFI_URL=https://unifi
UNIFI_USER=admin
UNIFI_PASS=password

# Pterodactyl
PTERO_URL=https://panel.yourdomain.com
PTERO_API_KEY=your_api_key
```

**📖 See [.env.example](.env.example) for complete list**

---

## 🔄 Automatic Updates

### TrueNAS SCALE

Enable automatic updates with GitHub Actions:

```yaml
# .github/workflows/build-and-push.yml
# Automatically builds and publishes on every commit
```

Schedule updates on TrueNAS:

```bash
# Daily updates at 3 AM
0 3 * * * /root/update-script.sh
```

### Docker Compose

```bash
# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d
```

---

## 🔧 Usage

### Deploy a Game Server

1. Navigate to **Deploy Server** tab
2. Fill in server details:
   - Subdomain (e.g., `minecraft`)
   - Server IP address
   - Game type
   - Port configuration
   - Resource allocation
3. Click **Deploy Server**
4. Watch real-time deployment progress
5. Server is ready when deployment completes!

### Create a Template

1. Configure server settings
2. Check **"Save as Template"**
3. Name your template
4. Deploy

Future deployments can use this template for instant configuration!

### Monitor Deployments

- View all deployments in the **Deployments** tab
- Check logs for any deployment
- Roll back failed deployments with one click
- View system statistics in **Monitoring** tab

### Test Configuration

1. Go to **Settings** tab
2. Click **Test All APIs**
3. Verify all services are connected
4. Fix any failing connections

---

## 🛠️ Development

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Node.js (for frontend development)

### Local Development

```bash
# Clone repository
git clone https://github.com/your-repo/wingman.git
cd wingman

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
nano .env

# Run development server
python app.py

# Access at http://localhost:5000
```

### Project Structure

```
wingman/
├── app.py                      # Flask web application
├── deployment_manager.py       # Deployment orchestration
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container image
├── docker-compose.yml          # Docker Compose config
├── templates/                  # HTML templates
│   └── index.html             # Main web interface
├── static/                     # Static assets
│   ├── css/
│   │   └── style.css          # Stylesheet
│   └── js/
│       └── app.js             # Frontend JavaScript
├── truenas/                    # TrueNAS SCALE files
│   ├── install.yaml           # Quick install manifest
│   ├── questions.yaml         # GUI configuration
│   ├── app.yaml               # App metadata
│   ├── update-script.sh       # Auto-update script
│   └── charts/                # Kubernetes manifests
└── .github/
    └── workflows/
        └── build-and-push.yml # CI/CD pipeline
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Original automation script concept by community contributors
- Built with Flask, Docker, and Kubernetes
- Icons by Font Awesome
- Inspired by modern DevOps practices

---

## 📞 Support

### Documentation
- [Quick Start Guide](QUICK_START.md)
- [TrueNAS Installation](docs/TRUENAS.md)
- [Docker Deployment](docs/DOCKER.md)
- [Authentication Setup](docs/AUTHENTICATION.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

### Troubleshooting

**Can't access web interface?**
```bash
# Check if running
kubectl get pods -n wingman  # TrueNAS
docker-compose ps            # Docker

# View logs
kubectl logs -f deployment/wingman -n wingman  # TrueNAS
docker-compose logs -f                         # Docker
```

**API tests failing?**
- Verify credentials in `.env` or Kubernetes secrets
- Check network connectivity to external services
- Review logs for specific error messages

**Deployment fails?**
- Check deployment logs in the UI
- Verify all external services are accessible
- Ensure credentials are correct
- Try rolling back and deploying again

### Getting Help

1. Check the logs (most issues are logged with details)
2. Review documentation for your deployment method
3. Test API connectivity in the Settings tab
4. Check GitHub issues for similar problems
5. Open a new issue with logs and configuration details