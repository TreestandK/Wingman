# Favicon and Branding Guide

## Current Implementation

Wingman now includes a complete favicon and PWA (Progressive Web App) setup!

### Files Included

- **`static/favicon.svg`** - SVG favicon (works in modern browsers)
- **`static/manifest.json`** - Web app manifest for PWA support
- **Meta tags in HTML** - Added to both `index.html` and `login.html`

### Features

✅ **SVG Favicon** - Scalable, works at any size
✅ **PWA Support** - Can be installed as a standalone app
✅ **Apple Touch Icon** - Looks great on iOS home screen
✅ **Theme Color** - Branded blue (#4a90e2) for browser UI
✅ **Mobile Optimized** - Full mobile web app support

## Current Design

The favicon features a **gamepad/wing hybrid design** representing:
- 🎮 **Gaming** - Gamepad shape for game server management
- ✈️ **Wingman** - Wing shapes flanking the center
- 🔵 **Blue Theme** - Matches the primary application color

## How to Customize

### Option 1: Edit the SVG (Simple)

1. Open `static/favicon.svg` in a text editor
2. Modify the SVG code:
   - Change `fill="#4a90e2"` to your brand color
   - Adjust shapes in the `<path>` elements
   - Modify the design completely
3. Save and refresh your browser

**Example: Change to green theme:**
```xml
<circle cx="50" cy="50" r="48" fill="#2ecc71"/>
```

### Option 2: Replace with Custom Image

If you have a custom logo (PNG, SVG, or ICO):

1. **Copy your favicon file** to `/app/static/`:
   ```bash
   docker cp your-favicon.svg wingman:/app/static/favicon.svg
   # or
   docker cp your-favicon.ico wingman:/app/static/favicon.ico
   ```

2. **Update HTML templates** if using a different format:
   - Edit `templates/index.html`
   - Edit `templates/login.html`
   - Change `favicon.svg` to your filename

3. **Update manifest.json**:
   ```json
   {
     "icons": [
       {
         "src": "/static/your-icon.png",
         "sizes": "512x512",
         "type": "image/png"
       }
     ]
   }
   ```

### Option 3: Generate PNG Favicons (Advanced)

For maximum compatibility, generate multiple PNG sizes:

**Using Online Tool:**
1. Go to https://realfavicongenerator.net/
2. Upload your SVG or PNG logo
3. Download the generated files
4. Copy to `static/` folder
5. Update HTML meta tags

**Using ImageMagick (if available):**
```bash
# Convert SVG to multiple PNG sizes
convert static/favicon.svg -resize 32x32 static/favicon-32x32.png
convert static/favicon.svg -resize 16x16 static/favicon-16x16.png
convert static/favicon.svg -resize 180x180 static/apple-touch-icon.png
convert static/favicon.svg -resize 192x192 static/android-chrome-192x192.png
convert static/favicon.svg -resize 512x512 static/android-chrome-512x512.png
```

Then update `manifest.json`:
```json
{
  "icons": [
    {
      "src": "/static/android-chrome-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/android-chrome-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

And add to HTML `<head>`:
```html
<link rel="icon" type="image/png" sizes="32x32" href="{{ url_for('static', filename='favicon-32x32.png') }}">
<link rel="icon" type="image/png" sizes="16x16" href="{{ url_for('static', filename='favicon-16x16.png') }}">
<link rel="apple-touch-icon" sizes="180x180" href="{{ url_for('static', filename='apple-touch-icon.png') }}">
```

## Web App Manifest

The `manifest.json` file enables PWA features:

```json
{
  "name": "Wingman Game Server Manager",
  "short_name": "Wingman",
  "description": "Automated Game Server Deployment & Management",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#1a1a2e",
  "theme_color": "#4a90e2",
  "icons": [...]
}
```

### Customize the Manifest

**Change Colors:**
- `background_color` - Splash screen background
- `theme_color` - Browser UI color (address bar, task switcher)

**Change Display Mode:**
- `standalone` - Looks like a native app (current)
- `fullscreen` - Full screen mode
- `minimal-ui` - Minimal browser UI
- `browser` - Regular browser tab

**Change Names:**
- `name` - Full app name (used in app drawer)
- `short_name` - Short name (used on home screen)

## Testing

### Test Favicon

1. **Desktop Browser:**
   - Open http://localhost:5000
   - Check browser tab for favicon
   - Look for blue gamepad/wing icon

2. **Mobile Browser:**
   - Open on mobile device
   - Tap "Add to Home Screen"
   - Icon should appear with your favicon

3. **Developer Tools:**
   - Open DevTools (F12)
   - Go to Application tab → Manifest
   - Verify manifest loads correctly

### Clear Browser Cache

If favicon doesn't update:

**Chrome/Edge:**
```
Ctrl+Shift+Delete → Clear cached images
```

**Firefox:**
```
Ctrl+Shift+Delete → Cached Web Content
```

**Force Refresh:**
```
Ctrl+F5 or Ctrl+Shift+R
```

## Browser Support

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| SVG Favicon | ✅ | ✅ | ✅ | ✅ |
| PNG Favicon | ✅ | ✅ | ✅ | ✅ |
| Web Manifest | ✅ | ✅ | ⚠️ | ✅ |
| PWA Install | ✅ | ✅ | ⚠️ | ✅ |
| Theme Color | ✅ | ✅ | ✅ | ✅ |

⚠️ = Limited support

## Example Custom Designs

### Simple Letter Icon

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="48" fill="#4a90e2"/>
  <text x="50" y="70" font-size="60" font-weight="bold" fill="white" text-anchor="middle">W</text>
</svg>
```

### Minimalist Icon

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" fill="#4a90e2" rx="15"/>
  <circle cx="50" cy="50" r="20" fill="white"/>
  <circle cx="50" cy="50" r="10" fill="#4a90e2"/>
</svg>
```

## Troubleshooting

### Favicon Not Showing

1. **Clear browser cache** (Ctrl+Shift+Delete)
2. **Hard refresh** (Ctrl+F5)
3. **Check file exists**:
   ```bash
   docker exec wingman ls -la /app/static/favicon.svg
   ```
4. **Check DevTools Console** for 404 errors

### Wrong Icon Displays

- Old favicon cached by browser
- Try incognito/private window
- Check HTML meta tags are correct

### PWA Install Not Available

- Requires HTTPS in production
- Check manifest.json is valid
- Verify all required icons exist
- Open DevTools → Application → Manifest to see errors

## Production Checklist

Before deploying to production:

- [ ] Customize favicon to match your brand
- [ ] Generate PNG favicons for full compatibility
- [ ] Update manifest.json with your app details
- [ ] Test on mobile devices
- [ ] Verify HTTPS is configured (required for PWA)
- [ ] Test "Add to Home Screen" on iOS and Android
- [ ] Verify theme colors match your design

## Resources

- [Favicon Generator](https://realfavicongenerator.net/)
- [MDN: Web App Manifest](https://developer.mozilla.org/en-US/docs/Web/Manifest)
- [Google: PWA Checklist](https://web.dev/pwa-checklist/)
- [Favicon Cheat Sheet](https://github.com/audreyfeldroy/favicon-cheat-sheet)

---

**Current Status:** ✅ Complete

Wingman now has full favicon and PWA support!
