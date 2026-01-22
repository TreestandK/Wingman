# GitHub Container Registry Setup

## Problem

When deploying Wingman, you see:
```
Error: Head "https://ghcr.io/v2/treestandk/wingman/manifests/latest": unauthorized
```

This means the Docker image hasn't been pushed to GitHub Container Registry yet, or it's set to private.

## Solution

You have 3 options:

---

## Option 1: Push to GitHub and Make Package Public (Recommended)

### Step 1: Push Your Code

Your code is already pushed. GitHub Actions should automatically build the image.

### Step 2: Check GitHub Actions

1. Go to: https://github.com/treestandk/wingman/actions
2. Look for the "Build and Push Docker Image" workflow
3. If it hasn't run, click "Run workflow" manually
4. Wait for it to complete (takes 2-5 minutes)

### Step 3: Make the Package Public

After the workflow completes:

1. Go to: https://github.com/treestandk?tab=packages
2. Click on the **wingman** package
3. Click **Package settings** (right sidebar)
4. Scroll down to **Danger Zone**
5. Click **Change visibility**
6. Select **Public**
7. Confirm by typing the package name

**Done!** Now TrueNAS can pull the image without authentication.

---

## Option 2: Build Locally and Push

If you prefer to build manually:

### Build and Push Script

Run the included script:

```bash
./build-and-push.sh
```

This will:
1. Build the Docker image
2. Ask if you want to push
3. Help you login to GitHub Container Registry
4. Push the image
5. Remind you to make it public

### Manual Build and Push

Or do it manually:

```bash
# 1. Build the image
docker build -t ghcr.io/treestandk/wingman:latest .

# 2. Login to GitHub Container Registry
# Create a PAT at: https://github.com/settings/tokens
# Needs 'write:packages' permission
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# 3. Push the image
docker push ghcr.io/treestandk/wingman:latest
```

Then make the package public (see Step 3 above).

---

## Option 3: Use Local Build on TrueNAS (Temporary)

If you just want to test quickly:

### On your development machine:

```bash
# Build the image
docker build -t ghcr.io/treestandk/wingman:latest .

# Save to tarball
docker save ghcr.io/treestandk/wingman:latest | gzip > wingman.tar.gz

# Copy to TrueNAS
scp wingman.tar.gz root@YOUR_TRUENAS_IP:/tmp/
```

### On TrueNAS:

```bash
# Load the image
docker load -i /tmp/wingman.tar.gz

# Verify it loaded
docker images | grep wingman
```

Now deploy with your docker-compose file.

**Note:** This is temporary - the image will be lost on TrueNAS reboot unless you make it permanent.

---

## Verifying the Image is Public

After making the package public, test it:

```bash
curl -s https://ghcr.io/v2/treestandk/wingman/manifests/latest
```

If it returns JSON data, it's public! ✅

If it returns `401 Unauthorized`, it's still private. ❌

---

## Common Issues

### "Package not found"

The GitHub Actions workflow hasn't created the package yet. Run it manually:

1. Go to: https://github.com/treestandk/wingman/actions
2. Click "Build and Push Docker Image"
3. Click "Run workflow" → "Run workflow"

### "Insufficient permissions"

Your GitHub Personal Access Token needs these scopes:
- `write:packages`
- `read:packages`
- `delete:packages` (optional)

Create a new token at: https://github.com/settings/tokens/new

### "Image already exists"

If you see this when pushing, it means a previous version exists. Either:
- Use a version tag: `docker build -t ghcr.io/treestandk/wingman:v1.0.0 .`
- Force overwrite by re-pushing `latest`

---

## Next Steps

After the image is public:

1. **Test the pull:**
   ```bash
   docker pull ghcr.io/treestandk/wingman:latest
   ```

2. **Deploy on TrueNAS:**
   - Use the TrueNAS UI to deploy with the docker-compose.yml
   - Or use the command line: `docker-compose up -d`

3. **Access Wingman:**
   - URL: http://YOUR_TRUENAS_IP:5000
   - Login: admin / (your ADMIN_PASSWORD)

---

## Quick Reference

**GitHub Package URL:**
https://github.com/treestandk?tab=packages

**GitHub Actions:**
https://github.com/treestandk/wingman/actions

**Create PAT:**
https://github.com/settings/tokens/new

**Required PAT Scopes:**
- `write:packages`
- `read:packages`
