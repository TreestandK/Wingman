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
        memory: parseInt(document.getElementById('memory').value),
        disk: parseInt(document.getElementById('disk').value),
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

    // Poll for status
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
                    <h4><i class="fas fa-server"></i> ${dep.subdomain}.${dep.domain || 'yourdomain.com'}</h4>
                    <p>Server: ${dep.server_ip}:${dep.game_port}</p>
                    <div class="deployment-meta">
                        <span><i class="fas fa-gamepad"></i> ${dep.game_type}</span>
                        <span><i class="fas fa-calendar"></i> ${new Date(dep.created_at).toLocaleString()}</span>
                        <span class="status-badge ${dep.status}">${dep.status}</span>
                    </div>
                    <div class="deployment-actions">
                        <button class="btn btn-secondary" onclick="viewLogs('${dep.deployment_id}')">
                            <i class="fas fa-file-alt"></i> Logs
                        </button>
                        <button class="btn btn-danger" onclick="rollbackDeployment('${dep.deployment_id}')">
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
                    <h4><i class="fas fa-file-code"></i> ${tpl.name}</h4>
                    <p>Port: ${tpl.game_port} | Memory: ${tpl.memory}MB | Disk: ${tpl.disk}MB</p>
                    <div class="template-actions">
                        <button class="btn btn-primary" onclick="useTemplate('${tpl.name}')">
                            <i class="fas fa-rocket"></i> Use Template
                        </button>
                        <button class="btn btn-danger" onclick="deleteTemplate('${tpl.name}')">
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
        const response = await fetch('/api/config/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        const result = await response.json();

        if (result.success) {
            statusDiv.innerHTML = '<div class="success-message"><i class="fas fa-check-circle"></i> Configuration is valid!</div>';
        } else {
            statusDiv.innerHTML = `<div class="error-message"><i class="fas fa-times-circle"></i> ${result.error}</div>`;
        }
    } catch (error) {
        statusDiv.innerHTML = '<div class="error-message"><i class="fas fa-times-circle"></i> Validation failed</div>';
    }
}

// Test All APIs
async function testAllAPIs() {
    const statusDiv = document.getElementById('config-status');
    statusDiv.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Testing APIs...</div>';

    try {
        const response = await fetch('/api/config/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        const result = await response.json();

        if (result.tests) {
            const testsHtml = Object.entries(result.tests).map(([service, status]) => {
                const icon = status ? 'fa-check-circle' : 'fa-times-circle';
                const className = status ? 'success-message' : 'error-message';
                return `<div class="${className}"><i class="fas ${icon}"></i> ${service}: ${status ? 'Connected' : 'Failed'}</div>`;
            }).join('');

            statusDiv.innerHTML = testsHtml;
        }
    } catch (error) {
        statusDiv.innerHTML = '<div class="error-message"><i class="fas fa-times-circle"></i> API tests failed</div>';
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

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Load initial stats
    loadMonitoringStats();

    // Refresh stats every 30 seconds
    setInterval(() => {
        if (document.querySelector('[data-tab="monitoring"]').classList.contains('active')) {
            loadMonitoringStats();
        }
    }, 30000);
});
