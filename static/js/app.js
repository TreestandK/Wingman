// Wingman Game Server Manager - Frontend JavaScript

// Tab Management
document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', () => {
        const tabName = button.dataset.tab;
        switchTab(tabName);
    });
});

function switchTab(tabName) {
    // Update buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Load tab-specific data
    loadTabData(tabName);
}

function loadTabData(tabName) {
    switch(tabName) {
        case 'deployments':
            loadDeployments();
            break;
        case 'templates':
            loadTemplates();
            break;
        case 'monitoring':
            loadMonitoringStats();
            break;
        case 'users':
            loadUsers();
            loadPasswordRequirements();
            break;
    }
}

// Toast Notifications
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 4000);
}

// Basic HTML escaping to prevent XSS when rendering untrusted data
function esc(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}


// Collapsible Sections
function toggleSection(element) {
    const section = element.parentElement;
    section.classList.toggle('open');
}

// Template Name Toggle
document.getElementById('save-template')?.addEventListener('change', function(e) {
    const templateNameGroup = document.getElementById('template-name-group');
    templateNameGroup.style.display = e.target.checked ? 'block' : 'none';
});

// Game Type Auto-fill
document.getElementById('game-type')?.addEventListener('change', function(e) {
    const gameConfigs = {
        'minecraft_java': { port: 25565, memory: 4096, disk: 10240 },
        'minecraft_bedrock': { port: 19132, memory: 2048, disk: 5120 },
        'valheim': { port: 2456, memory: 4096, disk: 20480 },
        'terraria': { port: 7777, memory: 1024, disk: 2048 },
        'palworld': { port: 8211, memory: 8192, disk: 30720 },
        'rust': { port: 28015, memory: 8192, disk: 20480 },
        'ark': { port: 7777, memory: 8192, disk: 40960 }
    };

    const config = gameConfigs[e.target.value];
    if (config) {
        document.getElementById('game-port').value = config.port;
        document.getElementById('memory').value = config.memory;
        document.getElementById('disk').value = config.disk;
    }
});

// Deploy Form Submission
document.getElementById('deploy-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = {
        subdomain: document.getElementById('subdomain').value,
        server_ip: document.getElementById('server-ip').value,
        game_type: document.getElementById('game-type').value,
        game_port: parseInt(document.getElementById('game-port').value),
        memory_mb: parseInt(document.getElementById('memory').value),
        disk_mb: parseInt(document.getElementById('disk').value),
        cpu_limit: parseInt(document.getElementById('cpu').value),
        enable_ssl: document.getElementById('enable-ssl').checked,
        enable_monitoring: document.getElementById('enable-monitoring').checked,
        protocol: document.getElementById('protocol').value,
        save_template: document.getElementById('save-template').checked,
        template_name: document.getElementById('template-name').value
    };

    // Parse additional ports
    const additionalPortsStr = document.getElementById('additional-ports').value;
    if (additionalPortsStr) {
        formData.additional_ports = additionalPortsStr.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));
    }

    // Add Pterodactyl configuration if enabled
    if (document.getElementById('enable-pterodactyl').checked) {
        const nestId = document.getElementById('ptero-nest').value;
        const eggId = document.getElementById('ptero-egg').value;
        const nodeId = document.getElementById('ptero-node').value;
        const portMode = document.getElementById('ptero-port-mode').value;

        if (!nestId || !eggId || !nodeId) {
            showToast('Please select nest, egg, and node', 'error');
            return;
        }

        formData.pterodactyl_nest_id = parseInt(nestId);
        formData.pterodactyl_egg_id = parseInt(eggId);
        formData.pterodactyl_node_id = parseInt(nodeId);

        // Handle port assignment mode
        formData.pterodactyl_port_mode = portMode;
        if (portMode === 'select') {
            const allocationId = document.getElementById('ptero-allocation').value;
            if (!allocationId) {
                showToast('Please select a port allocation', 'error');
                return;
            }
            formData.pterodactyl_allocation_id = parseInt(allocationId);
        } else if (portMode === 'specify') {
            const port = document.getElementById('ptero-port').value;
            if (!port || port < 1024 || port > 65535) {
                showToast('Please enter a valid port number (1024-65535)', 'error');
                return;
            }
            formData.pterodactyl_port = parseInt(port);
        }
        // 'auto' mode doesn't need additional params

        // Resource limits (convert to Pterodactyl format)
        const cpuCores = parseFloat(document.getElementById('ptero-cpu').value) || 2;
        const memoryGB = parseFloat(document.getElementById('ptero-memory').value) || 4;
        const diskGB = parseFloat(document.getElementById('ptero-disk').value) || 20;

        // CPU: cores * 100 (e.g., 2 cores = 200%)
        formData.pterodactyl_cpu = Math.round(cpuCores * 100);
        // Memory: GB to MB
        formData.pterodactyl_memory = Math.round(memoryGB * 1024);
        // Disk: GB to MB
        formData.pterodactyl_disk = Math.round(diskGB * 1024);
    }

    try {
        const response = await fetch('/api/deploy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (result.success) {
            showToast('Deployment started successfully!', 'success');
            showDeploymentProgress(result.deployment_id);
        } else {
            showToast('Deployment failed: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
});

// Show Deployment Progress
function showDeploymentProgress(deploymentId) {
    const progressDiv = document.getElementById('deployment-progress');
    const stepsDiv = document.getElementById('deployment-steps');
    progressDiv.style.display = 'block';

    // Start WebSocket connection for real-time updates
    if (typeof watchDeployment === 'function') {
        watchDeployment(deploymentId);
    }

    // Poll for status (fallback and final state check)
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/deploy/${deploymentId}/status`);
            const result = await response.json();

            if (result.success) {
                const status = result.status;
                updateProgressBar(status.progress || 0);
                updateDeploymentSteps(status.steps || []);

                if (status.state === 'completed') {
                    clearInterval(pollInterval);
                    showToast('Deployment completed successfully!', 'success');
                    setTimeout(() => {
                        progressDiv.style.display = 'none';
                        loadDeployments();
                    }, 3000);
                } else if (status.state === 'failed') {
                    clearInterval(pollInterval);
                    showToast('Deployment failed: ' + status.error, 'error');
                }
            }
        } catch (error) {
            console.error('Status poll error:', error);
        }
    }, 2000);
}

function updateProgressBar(progress) {
    document.getElementById('progress-fill').style.width = progress + '%';
}

function updateDeploymentSteps(steps) {
    const stepsDiv = document.getElementById('deployment-steps');
    stepsDiv.innerHTML = steps.map(step => {
        let statusClass = '';
        let icon = 'fa-circle';

        if (step.status === 'completed') {
            statusClass = 'completed';
            icon = 'fa-check-circle';
        } else if (step.status === 'active') {
            statusClass = 'active';
            icon = 'fa-spinner fa-spin';
        } else if (step.status === 'failed') {
            statusClass = 'failed';
            icon = 'fa-times-circle';
        }

        return `
            <div class="deployment-step ${statusClass}">
                <i class="fas ${icon}"></i>
                <span>${step.name}</span>
            </div>
        `;
    }).join('');
}

// Load Deployments
async function loadDeployments() {
    const listDiv = document.getElementById('deployments-list');
    listDiv.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';

    try {
        const response = await fetch('/api/deployments');
        const result = await response.json();

        if (result.success && result.deployments.length > 0) {
            listDiv.innerHTML = result.deployments.map(dep => `
                <div class="deployment-card">
                    <h4><i class="fas fa-server"></i> ${esc(dep.subdomain)}.${esc(dep.domain || 'yourdomain.com')}</h4>
                    <p>Server: ${esc(dep.server_ip)}:${esc(dep.game_port)}</p>
                    <div class="deployment-meta">
                        <span><i class="fas fa-gamepad"></i> ${dep.game_type}</span>
                        <span><i class="fas fa-calendar"></i> ${new Date(dep.created_at).toLocaleString()}</span>
                        <span class="status-badge ${esc(dep.status)}">${esc(dep.status)}</span>
                    </div>
                    <div class="deployment-actions">
                        <button class="btn btn-secondary" onclick="viewLogs('${esc(dep.deployment_id)}')">
                            <i class="fas fa-file-alt"></i> Logs
                        </button>
                        <button class="btn btn-danger" onclick="rollbackDeployment('${esc(dep.deployment_id)}')">
                            <i class="fas fa-undo"></i> Rollback
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            listDiv.innerHTML = '<p class="info-message"><i class="fas fa-info-circle"></i> No deployments found.</p>';
        }
    } catch (error) {
        listDiv.innerHTML = '<p class="error-message"><i class="fas fa-exclamation-triangle"></i> Error loading deployments.</p>';
    }
}

// Load Templates
async function loadTemplates() {
    const listDiv = document.getElementById('templates-list');
    listDiv.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';

    try {
        const response = await fetch('/api/templates');
        const result = await response.json();

        if (result.success && result.templates.length > 0) {
            listDiv.innerHTML = result.templates.map(tpl => `
                <div class="template-card">
                    <h4><i class="fas fa-file-code"></i> ${esc(tpl.name)}</h4>
                    <p>Port: ${tpl.game_port} | Memory: ${tpl.memory}MB | Disk: ${tpl.disk}MB</p>
                    <div class="template-actions">
                        <button class="btn btn-primary" onclick="useTemplate('${esc(tpl.name)}')">
                            <i class="fas fa-rocket"></i> Use Template
                        </button>
                        <button class="btn btn-danger" onclick="deleteTemplate('${esc(tpl.name)}')">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            listDiv.innerHTML = '<p class="info-message"><i class="fas fa-info-circle"></i> No templates found.</p>';
        }
    } catch (error) {
        listDiv.innerHTML = '<p class="error-message"><i class="fas fa-exclamation-triangle"></i> Error loading templates.</p>';
    }
}

// Use Template
async function useTemplate(templateName) {
    try {
        const response = await fetch(`/api/templates/${templateName}`);
        const result = await response.json();

        if (result.success) {
            const template = result.template;
            document.getElementById('game-type').value = template.game_type || 'custom';
            document.getElementById('game-port').value = template.game_port;
            document.getElementById('memory').value = template.memory;
            document.getElementById('disk').value = template.disk;
            if (template.additional_ports) {
                document.getElementById('additional-ports').value = template.additional_ports.join(', ');
            }

            switchTab('deploy');
            showToast('Template loaded successfully!', 'success');
        }
    } catch (error) {
        showToast('Error loading template: ' + error.message, 'error');
    }
}

// Load Monitoring Stats
async function loadMonitoringStats() {
    try {
        const response = await fetch('/api/monitoring/stats');
        const result = await response.json();

        if (result.success) {
            const stats = result.stats;
            document.getElementById('stat-total').textContent = stats.total_deployments || 0;
            document.getElementById('stat-active').textContent = stats.active_deployments || 0;
            document.getElementById('stat-failed').textContent = stats.failed_deployments || 0;
            document.getElementById('stat-avg-time').textContent = stats.avg_deploy_time || '-';
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Test Connectivity
async function testConnectivity() {
    showToast('Testing API connectivity...', 'warning');

    try {
        const response = await fetch('/api/config/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        const result = await response.json();

        if (result.success) {
            showToast('All APIs are reachable!', 'success');
        } else {
            showToast('Some APIs failed connectivity test', 'warning');
        }
    } catch (error) {
        showToast('Connectivity test failed: ' + error.message, 'error');
    }
}

// Validate Configuration
async function validateConfig() {
    const statusDiv = document.getElementById('config-status');
    statusDiv.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Validating...</div>';

    try {
        // Get current configuration from the API
        const configResponse = await fetch('/api/config');

        if (!configResponse.ok) {
            throw new Error(`Failed to load config: HTTP ${configResponse.status}`);
        }

        const configData = await configResponse.json();
        console.log('Loaded config:', configData);

        if (!configData.success) {
            console.error('Config load failed:', configData);
            statusDiv.innerHTML = '<div class="error-message"><i class="fas fa-times-circle"></i> Failed to load configuration</div>';
            return;
        }

        // Validate the configuration
        const response = await fetch('/api/config/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(configData.config)
        });

        if (!response.ok) {
            throw new Error(`Validation request failed: HTTP ${response.status}`);
        }

        const result = await response.json();
        console.log('Validation result:', result);

        if (result.success) {
            statusDiv.innerHTML = '<div class="success-message"><i class="fas fa-check-circle"></i> Configuration is valid!</div>';
        } else {
            // Handle validation errors
            const errorList = result.errors && result.errors.length > 0
                ? result.errors.map(err => `<li>${err}</li>`).join('')
                : '<li>Unknown validation error</li>';
            const warningList = result.warnings && result.warnings.length > 0
                ? `<p><strong>Warnings:</strong></p><ul>${result.warnings.map(w => `<li>${w}</li>`).join('')}</ul>`
                : '';
            statusDiv.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-times-circle"></i>
                    <strong>Validation failed:</strong>
                    <ul>${errorList}</ul>
                    ${warningList}
                </div>`;
        }
    } catch (error) {
        console.error('Validation error:', error);
        statusDiv.innerHTML = `<div class="error-message"><i class="fas fa-times-circle"></i> Validation failed: ${error.message}</div>`;
    }
}

// Test All APIs
async function testAllAPIs() {
    const statusDiv = document.getElementById('config-status');
    statusDiv.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Testing APIs...</div>';

    try {
        // Get current configuration
        const configResponse = await fetch('/api/config');

        if (!configResponse.ok) {
            throw new Error(`Failed to load config: HTTP ${configResponse.status}`);
        }

        const configData = await configResponse.json();
        console.log('Loaded config for testing:', configData);

        if (!configData.success) {
            statusDiv.innerHTML = '<div class="error-message"><i class="fas fa-times-circle"></i> Failed to load configuration</div>';
            return;
        }

        // Test API connectivity
        const response = await fetch('/api/config/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(configData.config)
        });

        if (!response.ok) {
            throw new Error(`API test failed: HTTP ${response.status}`);
        }

        const result = await response.json();
        console.log('API test result:', result);

        if (result.tests) {
            const testsHtml = Object.entries(result.tests).map(([service, status]) => {
                let icon, className, statusText;
                if (status === null) {
                    icon = 'fa-minus-circle';
                    className = 'info-message';
                    statusText = 'Not Configured';
                } else if (status) {
                    icon = 'fa-check-circle';
                    className = 'success-message';
                    statusText = 'Connected';
                } else {
                    icon = 'fa-times-circle';
                    className = 'error-message';
                    statusText = 'Failed';
                }
                return `<div class="${className}"><i class="fas ${icon}"></i> <strong>${service}:</strong> ${statusText}</div>`;
            }).join('');

            statusDiv.innerHTML = testsHtml;

            // Show summary toast
            const failedCount = Object.values(result.tests).filter(s => s === false).length;
            if (failedCount > 0) {
                showToast(`API tests completed with ${failedCount} failure(s)`, 'warning');
            } else {
                showToast('All configured APIs are reachable!', 'success');
            }
        }
    } catch (error) {
        console.error('API test error:', error);
        statusDiv.innerHTML = `<div class="error-message"><i class="fas fa-times-circle"></i> API tests failed: ${error.message}</div>`;
    }
}

// View Logs
async function viewLogs(deploymentId) {
    try {
        const response = await fetch(`/api/logs/${deploymentId}`);
        const result = await response.json();

        if (result.success) {
            alert('Logs:\n\n' + result.logs.join('\n'));
        } else {
            showToast('Failed to retrieve logs', 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}

// Rollback Deployment
async function rollbackDeployment(deploymentId) {
    if (!confirm('Are you sure you want to rollback this deployment? This will remove all associated resources.')) {
        return;
    }

    try {
        const response = await fetch(`/api/deploy/${deploymentId}/rollback`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            showToast('Rollback completed successfully!', 'success');
            loadDeployments();
        } else {
            showToast('Rollback failed: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}

// Delete Template
async function deleteTemplate(templateName) {
    if (!confirm(`Delete template "${templateName}"?`)) {
        return;
    }

    showToast('Template deletion not yet implemented', 'warning');
}

// Pterodactyl Integration
let pterodactylData = {
    nests: [],
    eggs: [],
    nodes: [],
    allocations: {}
};

// Toggle Pterodactyl configuration section
document.getElementById('enable-pterodactyl')?.addEventListener('change', function(e) {
    const config = document.getElementById('pterodactyl-config');
    if (e.target.checked) {
        config.style.display = 'block';
        loadPterodactylData();
    } else {
        config.style.display = 'none';
    }
});

// Load all Pterodactyl data
async function loadPterodactylData() {
    await Promise.all([
        loadPterodactylNests(),
        loadPterodactylNodes()
    ]);
}

// Load Pterodactyl nests
async function loadPterodactylNests() {
    try {
        const response = await fetch('/api/pterodactyl/nests');
        const result = await response.json();

        if (result.success && result.nests) {
            pterodactylData.nests = result.nests;
            const nestSelect = document.getElementById('ptero-nest');
            nestSelect.innerHTML = '<option value="">Select a nest...</option>';

            result.nests.forEach(nest => {
                const option = document.createElement('option');
                option.value = nest.attributes.id;
                option.textContent = nest.attributes.name;
                option.dataset.nest = JSON.stringify(nest);
                nestSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading Pterodactyl nests:', error);
    }
}

// Load Pterodactyl nodes
async function loadPterodactylNodes() {
    try {
        const response = await fetch('/api/pterodactyl/nodes');
        const result = await response.json();

        if (result.success && result.nodes) {
            pterodactylData.nodes = result.nodes;
            const nodeSelect = document.getElementById('ptero-node');
            nodeSelect.innerHTML = '<option value="">Select a node...</option>';

            result.nodes.forEach(node => {
                const option = document.createElement('option');
                option.value = node.id;
                option.textContent = `${node.name} (${node.fqdn})`;
                option.dataset.node = JSON.stringify(node);
                nodeSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading Pterodactyl nodes:', error);
    }
}

// Handle nest selection change
document.getElementById('ptero-nest')?.addEventListener('change', async function(e) {
    const nestId = e.target.value;
    const eggSelect = document.getElementById('ptero-egg');

    if (!nestId) {
        eggSelect.innerHTML = '<option value="">Select a nest first...</option>';
        return;
    }

    eggSelect.innerHTML = '<option value="">Loading eggs...</option>';

    try {
        const nestData = JSON.parse(e.target.options[e.target.selectedIndex].dataset.nest);
        const eggs = nestData.relationships?.eggs?.data || [];

        eggSelect.innerHTML = '<option value="">Select an egg...</option>';

        eggs.forEach(egg => {
            const option = document.createElement('option');
            option.value = egg.attributes.id;
            option.textContent = egg.attributes.name;
            option.dataset.description = egg.attributes.description || '';
            option.dataset.author = egg.attributes.author || 'Unknown';
            eggSelect.appendChild(option);
        });

        if (eggs.length === 0) {
            eggSelect.innerHTML = '<option value="">No eggs available in this nest</option>';
        }
    } catch (error) {
        console.error('Error loading eggs:', error);
        eggSelect.innerHTML = '<option value="">Error loading eggs</option>';
    }
});

// Handle egg selection change - show description
document.getElementById('ptero-egg')?.addEventListener('change', function(e) {
    const descElement = document.getElementById('egg-description');
    if (e.target.value) {
        const description = e.target.options[e.target.selectedIndex].dataset.description;
        const author = e.target.options[e.target.selectedIndex].dataset.author;
        descElement.textContent = description ? `${description} (by ${author})` : '';
    } else {
        descElement.textContent = '';
    }
});

// Toggle port assignment mode
function togglePortMode() {
    const mode = document.getElementById('ptero-port-mode').value;
    const selectGroup = document.getElementById('port-select-group');
    const specifyGroup = document.getElementById('port-specify-group');

    // Hide all port input groups
    selectGroup.style.display = 'none';
    specifyGroup.style.display = 'none';

    // Show the appropriate group based on mode
    if (mode === 'select') {
        selectGroup.style.display = 'block';
    } else if (mode === 'specify') {
        specifyGroup.style.display = 'block';
    }
    // 'auto' mode doesn't show any additional fields
}

// Handle node selection change - load allocations
document.getElementById('ptero-node')?.addEventListener('change', async function(e) {
    const nodeId = e.target.value;
    const allocationSelect = document.getElementById('ptero-allocation');

    if (!nodeId) {
        allocationSelect.innerHTML = '<option value="">Select a node first...</option>';
        return;
    }

    allocationSelect.innerHTML = '<option value="">Loading allocations...</option>';

    try {
        const response = await fetch(`/api/pterodactyl/nodes/${nodeId}/allocations`);
        const result = await response.json();

        if (result.success && result.allocations) {
            pterodactylData.allocations[nodeId] = result.allocations;
            allocationSelect.innerHTML = '<option value="">Select a port...</option>';

            result.allocations.forEach(alloc => {
                const option = document.createElement('option');
                option.value = alloc.id;
                option.textContent = `${alloc.alias}:${alloc.port}`;
                allocationSelect.appendChild(option);
            });

            if (result.allocations.length === 0) {
                allocationSelect.innerHTML = '<option value="">No available ports on this node</option>';
            }
        } else {
            allocationSelect.innerHTML = '<option value="">Error loading allocations</option>';
        }
    } catch (error) {
        console.error('Error loading allocations:', error);
        allocationSelect.innerHTML = '<option value="">Error loading allocations</option>';
    }
});

// Update subdomain preview
document.getElementById('subdomain')?.addEventListener('input', function(e) {
    const preview = document.getElementById('subdomain-preview');
    if (preview) {
        preview.textContent = e.target.value || 'minecraft';
    }
});

// Auto-fill game port based on game type
document.getElementById('game-type')?.addEventListener('change', function(e) {
    const portInput = document.getElementById('game-port');
    const defaultPorts = {
        'minecraft_java': 25565,
        'minecraft_bedrock': 19132,
        'valheim': 2456,
        'terraria': 7777,
        'palworld': 8211,
        'rust': 28015,
        'ark': 7777,
        'custom': ''
    };

    const port = defaultPorts[e.target.value];
    if (port && portInput && !portInput.value) {
        portInput.value = port;
    }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Load initial stats
    loadMonitoringStats();

    // Check user permissions to show/hide admin-only tabs
    checkUserPermissions();

    // Refresh stats every 30 seconds
    setInterval(() => {
        if (document.querySelector('[data-tab="monitoring"]').classList.contains('active')) {
            loadMonitoringStats();
        }
    }, 30000);
});

// ===========================================
// USER MANAGEMENT FUNCTIONS
// ===========================================

let currentUserRole = null;
let csrfToken = null;

// Get CSRF token
async function getCsrfToken() {
    if (csrfToken) return csrfToken;
    try {
        const response = await fetch('/api/csrf');
        const result = await response.json();
        csrfToken = result.csrf_token || '';
        return csrfToken;
    } catch {
        return '';
    }
}

// Check if current user is admin and show Users tab
async function checkUserPermissions() {
    try {
        const response = await fetch('/api/auth/status');
        const result = await response.json();

        if (result.success && result.user) {
            currentUserRole = result.user.role;

            // Show Users tab only for admins
            const usersTabButton = document.getElementById('users-tab-button');
            if (usersTabButton && currentUserRole === 'admin') {
                usersTabButton.style.display = 'flex';
            }
        }
    } catch (error) {
        console.error('Error checking permissions:', error);
    }
}

// Password requirements cache
let passwordRequirements = null;

// Load and display password requirements
async function loadPasswordRequirements() {
    const reqDiv = document.getElementById('password-requirements');
    if (!reqDiv) return;

    try {
        const response = await fetch('/api/auth/password-requirements');
        const result = await response.json();

        if (result.success && result.requirements) {
            passwordRequirements = result.requirements;
            const reqList = reqDiv.querySelector('ul');
            reqList.innerHTML = passwordRequirements.requirements_text.map((req, i) =>
                `<li id="req-${i}" class="unmet"><i class="fas fa-circle"></i> ${esc(req)}</li>`
            ).join('');

            // Add live validation listener
            const passwordInput = document.getElementById('new-password');
            if (passwordInput) {
                passwordInput.addEventListener('input', validatePasswordLive);
                // Update minlength attribute
                passwordInput.minLength = passwordRequirements.min_length;
            }
        }
    } catch (error) {
        console.error('Error loading password requirements:', error);
    }
}

// Live password validation
function validatePasswordLive() {
    if (!passwordRequirements) return;

    const password = document.getElementById('new-password').value;
    const reqs = passwordRequirements;
    let reqIndex = 0;

    // Check min length
    const lengthMet = password.length >= reqs.min_length;
    updateRequirement(reqIndex++, lengthMet);

    // Check uppercase
    if (reqs.require_uppercase) {
        updateRequirement(reqIndex++, /[A-Z]/.test(password));
    }

    // Check lowercase
    if (reqs.require_lowercase) {
        updateRequirement(reqIndex++, /[a-z]/.test(password));
    }

    // Check digit
    if (reqs.require_digit) {
        updateRequirement(reqIndex++, /\d/.test(password));
    }

    // Check special char
    if (reqs.require_special) {
        updateRequirement(reqIndex++, /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password));
    }
}

function updateRequirement(index, met) {
    const el = document.getElementById(`req-${index}`);
    if (el) {
        el.className = met ? 'met' : 'unmet';
        el.querySelector('i').className = met ? 'fas fa-check-circle' : 'fas fa-circle';
    }
}

// Load users list
async function loadUsers() {
    const listDiv = document.getElementById('users-list');
    if (!listDiv) return;

    listDiv.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Loading users...</div>';

    try {
        const token = await getCsrfToken();
        const response = await fetch('/api/users', {
            headers: {
                'X-CSRF-Token': token
            }
        });
        const result = await response.json();

        if (result.success && result.users && result.users.length > 0) {
            listDiv.innerHTML = result.users.map(user => {
                const isSSO = user.auth_provider && user.auth_provider !== 'local';
                const isInactive = user.is_active === false;
                const isLocked = user.is_locked === true;

                let badges = '';
                badges += `<span class="badge badge-${user.role}">${esc(user.role)}</span>`;
                if (isSSO) badges += `<span class="badge badge-sso">SSO</span>`;
                if (isLocked) badges += `<span class="badge badge-locked"><i class="fas fa-lock"></i> Locked</span>`;
                if (isInactive) badges += `<span class="badge badge-inactive">Inactive</span>`;

                const lastLogin = user.last_login
                    ? new Date(user.last_login).toLocaleString()
                    : 'Never';

                const createdAt = user.created_at
                    ? new Date(user.created_at).toLocaleDateString()
                    : 'Unknown';

                // Show failed login info if any
                const failedLogins = user.failed_login_count > 0
                    ? `<span><i class="fas fa-exclamation-triangle" style="color: var(--warning-color)"></i> Failed logins: ${user.failed_login_count}</span>`
                    : '';

                return `
                    <div class="user-card ${isSSO ? 'sso-user' : ''} ${isInactive ? 'inactive' : ''} ${isLocked ? 'locked' : ''}">
                        <div class="user-info">
                            <h4>
                                <i class="fas ${isSSO ? 'fa-shield-alt' : 'fa-user'}"></i>
                                ${esc(user.username)}
                                ${badges}
                            </h4>
                            <div class="user-meta">
                                <span><i class="fas fa-envelope"></i> ${esc(user.email || 'No email')}</span>
                                <span><i class="fas fa-clock"></i> Last login: ${lastLogin}</span>
                                <span><i class="fas fa-calendar"></i> Created: ${createdAt}</span>
                                ${failedLogins}
                            </div>
                        </div>
                        <div class="user-actions">
                            ${isLocked ? `
                                <button class="btn btn-warning" onclick="unlockUser('${esc(user.username)}')">
                                    <i class="fas fa-unlock"></i> Unlock
                                </button>
                            ` : ''}
                            <select class="role-select" onchange="changeUserRole('${esc(user.username)}', this.value)">
                                <option value="viewer" ${user.role === 'viewer' ? 'selected' : ''}>Viewer</option>
                                <option value="operator" ${user.role === 'operator' ? 'selected' : ''}>Operator</option>
                                <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>Admin</option>
                            </select>
                            <button class="btn btn-secondary" onclick="toggleUserStatus('${esc(user.username)}', ${user.is_active !== false})">
                                <i class="fas fa-${user.is_active !== false ? 'ban' : 'check'}"></i>
                                ${user.is_active !== false ? 'Disable' : 'Enable'}
                            </button>
                            ${!isSSO ? `
                                <button class="btn btn-secondary" onclick="showResetPasswordModal('${esc(user.username)}')">
                                    <i class="fas fa-key"></i> Reset
                                </button>
                            ` : ''}
                            <button class="btn btn-danger" onclick="deleteUser('${esc(user.username)}')">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            listDiv.innerHTML = '<div class="no-users-message"><i class="fas fa-users"></i><p>No users found.</p></div>';
        }
    } catch (error) {
        listDiv.innerHTML = '<p class="error-message"><i class="fas fa-exclamation-triangle"></i> Error loading users.</p>';
        console.error('Error loading users:', error);
    }
}

// Create new user form handler
document.getElementById('add-user-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = {
        username: document.getElementById('new-username').value,
        password: document.getElementById('new-password').value,
        email: document.getElementById('new-email').value || null,
        role: document.getElementById('new-role').value
    };

    try {
        const token = await getCsrfToken();
        const response = await fetch('/api/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': token
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (result.success) {
            showToast('User created successfully!', 'success');
            document.getElementById('add-user-form').reset();
            loadUsers();
        } else {
            showToast('Failed to create user: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Error creating user: ' + error.message, 'error');
    }
});

// Change user role
async function changeUserRole(username, newRole) {
    try {
        const token = await getCsrfToken();
        const response = await fetch(`/api/users/${encodeURIComponent(username)}/role`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': token
            },
            body: JSON.stringify({ role: newRole })
        });

        const result = await response.json();

        if (result.success) {
            showToast(`Role updated to ${newRole}`, 'success');
        } else {
            showToast('Failed to update role: ' + result.error, 'error');
            loadUsers(); // Reload to reset select
        }
    } catch (error) {
        showToast('Error updating role: ' + error.message, 'error');
        loadUsers();
    }
}

// Toggle user active status
async function toggleUserStatus(username, currentStatus) {
    const action = currentStatus ? 'disable' : 'enable';
    if (!confirm(`Are you sure you want to ${action} user "${username}"?`)) {
        return;
    }

    try {
        const token = await getCsrfToken();
        const response = await fetch(`/api/users/${encodeURIComponent(username)}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': token
            },
            body: JSON.stringify({ is_active: !currentStatus })
        });

        const result = await response.json();

        if (result.success) {
            showToast(`User ${action}d successfully`, 'success');
            loadUsers();
        } else {
            showToast(`Failed to ${action} user: ` + result.error, 'error');
        }
    } catch (error) {
        showToast(`Error: ` + error.message, 'error');
    }
}

// Unlock a locked user account
async function unlockUser(username) {
    if (!confirm(`Are you sure you want to unlock user "${username}"?`)) {
        return;
    }

    try {
        const token = await getCsrfToken();
        const response = await fetch(`/api/users/${encodeURIComponent(username)}/unlock`, {
            method: 'POST',
            headers: {
                'X-CSRF-Token': token
            }
        });

        const result = await response.json();

        if (result.success) {
            showToast('User unlocked successfully', 'success');
            loadUsers();
        } else {
            showToast('Failed to unlock user: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Error unlocking user: ' + error.message, 'error');
    }
}

// Delete user
async function deleteUser(username) {
    if (!confirm(`Are you sure you want to delete user "${username}"? This cannot be undone.`)) {
        return;
    }

    try {
        const token = await getCsrfToken();
        const response = await fetch(`/api/users/${encodeURIComponent(username)}`, {
            method: 'DELETE',
            headers: {
                'X-CSRF-Token': token
            }
        });

        const result = await response.json();

        if (result.success) {
            showToast('User deleted successfully', 'success');
            loadUsers();
        } else {
            showToast('Failed to delete user: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Error deleting user: ' + error.message, 'error');
    }
}

// Show reset password modal (simple prompt for now)
function showResetPasswordModal(username) {
    const newPassword = prompt(`Enter new password for user "${username}" (minimum 8 characters):`);
    if (!newPassword) return;

    if (newPassword.length < 8) {
        showToast('Password must be at least 8 characters', 'error');
        return;
    }

    resetUserPassword(username, newPassword);
}

// Reset user password
async function resetUserPassword(username, newPassword) {
    try {
        const token = await getCsrfToken();
        const response = await fetch(`/api/users/${encodeURIComponent(username)}/password`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': token
            },
            body: JSON.stringify({ password: newPassword })
        });

        const result = await response.json();

        if (result.success) {
            showToast('Password reset successfully', 'success');
        } else {
            showToast('Failed to reset password: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Error resetting password: ' + error.message, 'error');
    }
}
