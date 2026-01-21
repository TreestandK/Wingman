// Configuration and Pterodactyl Management Functions

// ===== Configuration Management =====

// Load current configuration
async function loadConfiguration() {
    try {
        const response = await fetch('/api/config');
        const result = await response.json();

        if (result.success) {
            const config = result.config;

            // Populate form fields
            document.getElementById('config-domain').value = config.domain || '';
            document.getElementById('cf-api-token').value = config.cloudflare?.api_token || '';
            document.getElementById('cf-zone-id').value = config.cloudflare?.zone_id || '';
            document.getElementById('enable-cloudflare').checked = config.cloudflare?.enabled || false;

            document.getElementById('npm-url').value = config.npm?.api_url || '';
            document.getElementById('npm-email').value = config.npm?.email || '';
            document.getElementById('npm-password').value = config.npm?.password || '';
            document.getElementById('enable-npm').checked = config.npm?.enabled || false;

            document.getElementById('unifi-url').value = config.unifi?.url || '';
            document.getElementById('unifi-user').value = config.unifi?.user || '';
            document.getElementById('unifi-password').value = config.unifi?.password || '';
            document.getElementById('unifi-site').value = config.unifi?.site || 'default';
            document.getElementById('unifi-is-udm').checked = config.unifi?.is_udm || false;
            document.getElementById('enable-unifi').checked = config.unifi?.enabled || false;

            document.getElementById('ptero-url').value = config.pterodactyl?.url || '';
            document.getElementById('ptero-api-key').value = config.pterodactyl?.api_key || '';
            document.getElementById('enable-pterodactyl').checked = config.pterodactyl?.enabled || false;

            showToast('Configuration loaded', 'success');
        }
    } catch (error) {
        showToast('Error loading configuration: ' + error.message, 'error');
    }
}

// Save configuration
document.getElementById('config-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();

    const config = {
        domain: document.getElementById('config-domain').value,
        cloudflare: {
            api_token: document.getElementById('cf-api-token').value,
            zone_id: document.getElementById('cf-zone-id').value,
            enabled: document.getElementById('enable-cloudflare').checked
        },
        npm: {
            api_url: document.getElementById('npm-url').value,
            email: document.getElementById('npm-email').value,
            password: document.getElementById('npm-password').value,
            enabled: document.getElementById('enable-npm').checked
        },
        unifi: {
            url: document.getElementById('unifi-url').value,
            user: document.getElementById('unifi-user').value,
            password: document.getElementById('unifi-password').value,
            site: document.getElementById('unifi-site').value,
            is_udm: document.getElementById('unifi-is-udm').checked,
            enabled: document.getElementById('enable-unifi').checked
        },
        pterodactyl: {
            url: document.getElementById('ptero-url').value,
            api_key: document.getElementById('ptero-api-key').value,
            enabled: document.getElementById('enable-pterodactyl').checked
        }
    };

    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const result = await response.json();

        if (result.success) {
            showToast('Configuration saved successfully!', 'success');
        } else {
            showToast('Failed to save configuration: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Error saving configuration: ' + error.message, 'error');
    }
});

// ===== Pterodactyl Management =====

// List available nests
async function listNests() {
    const listDiv = document.getElementById('nests-list');
    listDiv.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Loading nests...</div>';

    try {
        const response = await fetch('/api/pterodactyl/nests');
        const result = await response.json();

        if (result.success && result.nests.length > 0) {
            listDiv.innerHTML = '<h4>Available Nests:</h4>' + result.nests.map(nest => {
                const eggsCount = nest.relationships?.eggs?.data?.length || 0;
                return `
                    <div class="egg-card">
                        <h4><i class="fas fa-folder"></i> ${nest.attributes.name}</h4>
                        <div class="egg-meta">
                            <span>ID: ${nest.attributes.id}</span>
                            <span>Eggs: ${eggsCount}</span>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            listDiv.innerHTML = '<p class="info-message"><i class="fas fa-info-circle"></i> No nests found or Pterodactyl not configured.</p>';
        }
    } catch (error) {
        listDiv.innerHTML = '<p class="error-message"><i class="fas fa-exclamation-triangle"></i> Error loading nests: ' + error.message + '</p>';
    }
}

// Upload egg
document.getElementById('egg-upload-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();

    const fileInput = document.getElementById('egg-file');
    const nestId = document.getElementById('nest-id').value;
    const resultDiv = document.getElementById('upload-result');

    if (!fileInput.files || fileInput.files.length === 0) {
        showToast('Please select an egg file', 'error');
        return;
    }

    const file = fileInput.files[0];

    try {
        // Read file content
        const fileContent = await file.text();
        const eggData = JSON.parse(fileContent);

        resultDiv.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Uploading egg...</div>';

        const response = await fetch('/api/pterodactyl/eggs/upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nest_id: parseInt(nestId),
                egg_data: eggData
            })
        });

        const result = await response.json();

        if (result.success) {
            resultDiv.innerHTML = '<div class="success-message"><i class="fas fa-check-circle"></i> Egg uploaded successfully!</div>';
            showToast('Egg uploaded to Pterodactyl!', 'success');
            fileInput.value = '';
            loadPterodactylEggs();
        } else {
            resultDiv.innerHTML = '<div class="error-message"><i class="fas fa-times-circle"></i> Upload failed: ' + result.error + '</div>';
            showToast('Upload failed: ' + result.error, 'error');
        }
    } catch (error) {
        resultDiv.innerHTML = '<div class="error-message"><i class="fas fa-times-circle"></i> Error: ' + error.message + '</div>';
        showToast('Error uploading egg: ' + error.message, 'error');
    }
});

// Load Pterodactyl eggs list
async function loadPterodactylEggs() {
    const listDiv = document.getElementById('eggs-list');
    listDiv.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Loading eggs...</div>';

    try {
        const response = await fetch('/api/pterodactyl/eggs');
        const result = await response.json();

        if (result.success && result.eggs.length > 0) {
            listDiv.innerHTML = result.eggs.map(egg => `
                <div class="egg-card">
                    <h4><i class="fas fa-egg"></i> ${egg.name}</h4>
                    <p>${egg.description || 'No description'}</p>
                    <div class="egg-meta">
                        <span>ID: ${egg.id}</span>
                        <span>Nest: ${egg.nest_name || egg.nest_id}</span>
                        <span>Author: ${egg.author || 'Unknown'}</span>
                    </div>
                </div>
            `).join('');
        } else {
            listDiv.innerHTML = '<p class="info-message"><i class="fas fa-info-circle"></i> No eggs found or Pterodactyl not configured.</p>';
        }
    } catch (error) {
        listDiv.innerHTML = '<p class="error-message"><i class="fas fa-exclamation-triangle"></i> Error loading eggs: ' + error.message + '</p>';
    }
}

// Initialize configuration on settings tab
document.addEventListener('DOMContentLoaded', () => {
    // Load configuration when settings tab is opened
    const settingsTab = document.querySelector('[data-tab="settings"]');
    if (settingsTab) {
        settingsTab.addEventListener('click', () => {
            loadConfiguration();
        });
    }
});
