# GitHub Actions Troubleshooting

Common issues and solutions for the Wingman GitHub Actions workflow.

## Issue: "Unable to get ACTIONS_ID_TOKEN_REQUEST_URL env variable"

### Error Message
```
Error: Failed to get ID token: Error message: Unable to get ACTIONS_ID_TOKEN_REQUEST_URL env variable
```

### Cause
The workflow is trying to generate build attestations but doesn't have the required permissions.

### Solution 1: Use the Fixed Workflow (Recommended)

The main workflow file has been updated with the correct permissions:

```yaml
permissions:
  contents: read
  packages: write
  id-token: write      # Required for attestations
  attestations: write   # Required for attestations
```

**Just push the updated workflow:**
```bash
git add .github/workflows/build-and-push.yml
git commit -m "Fix GitHub Actions permissions"
git push
```

### Solution 2: Use the Simple Workflow (No Attestations)

If you don't need build attestations, use the simplified workflow:

1. **Disable the main workflow:**
   ```bash
   mv .github/workflows/build-and-push.yml .github/workflows/build-and-push.yml.disabled
   ```

2. **Rename the simple workflow:**
   ```bash
   mv .github/workflows/build-and-push-simple.yml .github/workflows/build-and-push.yml
   ```

3. **Push changes:**
   ```bash
   git add .github/workflows/
   git commit -m "Use simple workflow without attestations"
   git push
   ```

### Solution 3: Enable Permissions in Repository Settings

If the error persists:

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Actions** → **General**
3. Scroll to **Workflow permissions**
4. Select **Read and write permissions**
5. Check **Allow GitHub Actions to create and approve pull requests**
6. Click **Save**
7. Re-run the workflow

---

## Issue: Build Fails on Multi-Architecture

### Error Message
```
ERROR: Multi-platform build is not supported for the docker driver
```

### Solution

The workflow uses `buildx` which is already configured. If you see this error:

1. **Check the workflow uses buildx:**
   ```yaml
   - name: Set up Docker Buildx
     uses: docker/setup-buildx-action@v3
   ```

2. **Verify platforms are correct:**
   ```yaml
   platforms: linux/amd64,linux/arm64
   ```

3. **For single architecture only:**
   ```yaml
   # Remove or comment out the platforms line
   # platforms: linux/amd64,linux/arm64
   ```

---

## Issue: Authentication Failed

### Error Message
```
Error: buildx failed with: ERROR: failed to solve: failed to authorize
```

### Solution

1. **Verify GITHUB_TOKEN has permissions:**
   - The workflow uses `secrets.GITHUB_TOKEN` automatically
   - Ensure workflow permissions are set correctly (see Solution 3 above)

2. **For private repositories:**
   ```yaml
   # The workflow already handles this
   - name: Log in to Container Registry
     if: github.event_name != 'pull_request'
     uses: docker/login-action@v3
     with:
       registry: ${{ env.REGISTRY }}
       username: ${{ github.actor }}
       password: ${{ secrets.GITHUB_TOKEN }}
   ```

3. **Manual login test:**
   ```bash
   echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
   ```

---

## Issue: Workflow Doesn't Trigger

### Solution

1. **Check workflow file location:**
   ```
   .github/workflows/build-and-push.yml
   ```

2. **Verify trigger conditions:**
   ```yaml
   on:
     push:
       branches:
         - main  # Only triggers on main branch
     tags:
       - 'v*'    # Or version tags
   ```

3. **Check GitHub Actions is enabled:**
   - Settings → Actions → General → Actions permissions
   - Enable "Allow all actions and reusable workflows"

4. **Manual trigger:**
   - Go to Actions tab
   - Select "Build and Push Docker Image"
   - Click "Run workflow"

---

## Issue: Image Not Found After Build

### Error Message
```
Error: ghcr.io/username/wingman:latest: not found
```

### Solution

1. **Check if the build succeeded:**
   - Go to Actions tab
   - Check the latest workflow run
   - Look for green checkmark

2. **Verify image was pushed:**
   - Go to your profile → Packages
   - Look for `wingman` package

3. **Check image visibility:**
   - If package exists but you can't pull it
   - Go to Package settings → Change visibility to Public

4. **Correct image name:**
   ```bash
   # Use your actual GitHub username
   docker pull ghcr.io/YOUR-ACTUAL-USERNAME/wingman:latest
   ```

---

## Issue: Cache Issues

### Error Message
```
ERROR: failed to load cache
```

### Solution

1. **Clear GitHub Actions cache:**
   - Settings → Actions → Caches
   - Delete old caches

2. **Disable cache temporarily:**
   ```yaml
   # Comment out cache lines
   # cache-from: type=gha
   # cache-to: type=gha,mode=max
   ```

3. **Force rebuild:**
   ```bash
   git commit --allow-empty -m "Force rebuild"
   git push
   ```

---

## Workflow Comparison

### Full Workflow (with attestations)
**File:** `.github/workflows/build-and-push.yml`

**Pros:**
- Build provenance tracking
- Enhanced security
- Attestations visible in GitHub

**Cons:**
- Requires additional permissions
- Slightly more complex

**Use when:**
- Publishing to public registries
- Security compliance required
- Want provenance tracking

### Simple Workflow (without attestations)
**File:** `.github/workflows/build-and-push-simple.yml`

**Pros:**
- Simpler permission model
- Fewer potential errors
- Faster builds

**Cons:**
- No build attestations
- No provenance tracking

**Use when:**
- Quick setup needed
- Internal use only
- Minimal permission model preferred

---

## Testing Workflows Locally

Use [act](https://github.com/nektos/act) to test workflows locally:

```bash
# Install act
# macOS: brew install act
# Linux: curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Test the workflow
act push

# Test specific job
act -j build-and-push

# With secrets
act -s GITHUB_TOKEN=your_token
```

---

## Monitoring Workflow Runs

### View Logs

1. **GitHub UI:**
   - Go to Actions tab
   - Click on workflow run
   - Click on job name
   - Expand step to see logs

2. **Download logs:**
   - Click ⋮ menu on workflow run
   - Download log archive

3. **GitHub CLI:**
   ```bash
   # List runs
   gh run list

   # View specific run
   gh run view RUN_ID

   # View logs
   gh run view RUN_ID --log
   ```

---

## Best Practices

1. **Always test locally first:**
   ```bash
   docker build -t wingman:test .
   ```

2. **Use descriptive commit messages:**
   ```bash
   git commit -m "fix: Update Dockerfile to fix build error"
   ```

3. **Tag releases properly:**
   ```bash
   git tag -a v2.0.1 -m "Release 2.0.1"
   git push origin v2.0.1
   ```

4. **Monitor first few builds:**
   - Watch Actions tab after pushing
   - Fix issues promptly
   - Document any required changes

5. **Keep workflows updated:**
   ```bash
   # Check for action updates periodically
   # @v4 → @v5 etc.
   ```

---

## Quick Fixes

### Workflow won't run at all
```bash
# Check file is in correct location
ls .github/workflows/build-and-push.yml

# Check YAML syntax
cat .github/workflows/build-and-push.yml | grep -v "^#" | grep -v "^$"
```

### Build succeeds but image not available
```bash
# Check if push condition is met
# Workflow only pushes on non-PR events
# Verify you pushed to main branch, not PR
```

### Permission errors
```bash
# Verify repository settings
# Settings → Actions → General → Workflow permissions
# Should be "Read and write permissions"
```

---

## Getting Help

1. **Check workflow logs** - Most detailed error information
2. **Review this guide** - Common issues covered
3. **GitHub Actions documentation** - https://docs.github.com/actions
4. **Create an issue** - Include workflow logs

---

## Quick Reference

### Main Workflow
```yaml
# .github/workflows/build-and-push.yml
# Full featured with attestations
permissions:
  contents: read
  packages: write
  id-token: write
  attestations: write
```

### Simple Workflow
```yaml
# .github/workflows/build-and-push-simple.yml
# Minimal permissions, no attestations
permissions:
  contents: read
  packages: write
```

### Manual Workflow Trigger
```bash
# Using GitHub CLI
gh workflow run build-and-push.yml

# Check status
gh run list --workflow=build-and-push.yml
```

### Image URLs
```bash
# GitHub Container Registry
ghcr.io/YOUR-USERNAME/wingman:latest
ghcr.io/YOUR-USERNAME/wingman:v2.0.0

# Docker Hub (if you use it instead)
YOUR-USERNAME/wingman:latest
```
