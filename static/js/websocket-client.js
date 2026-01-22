// WebSocket Client for Real-Time Deployment Logs

let socket = null;
let currentDeploymentId = null;

// Initialize WebSocket connection
function initializeWebSocket() {
    // Load Socket.IO client library from CDN if not already loaded
    if (typeof io === 'undefined') {
        const script = document.createElement('script');
        script.src = 'https://cdn.socket.io/4.5.4/socket.io.min.js';
        script.onload = connectWebSocket;
        document.head.appendChild(script);
    } else {
        connectWebSocket();
    }
}

// Connect to WebSocket server
function connectWebSocket() {
    if (socket && socket.connected) {
        return; // Already connected
    }

    socket = io({
        transports: ['websocket', 'polling'],
        upgrade: true
    });

    socket.on('connect', () => {
        console.log('WebSocket connected');
        addConsoleLog('🔌 Connected to deployment console', 'system');
    });

    socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
        addConsoleLog('⚠️ Disconnected from deployment console', 'system');
    });

    socket.on('deployment_log', (data) => {
        if (data.deployment_id === currentDeploymentId) {
            addConsoleLog(data.log_entry, 'log');
        }
    });

    socket.on('deployment_progress', (data) => {
        if (data.deployment_id === currentDeploymentId) {
            updateProgressBar(data.progress);
            updateDeploymentSteps(data.steps);
        }
    });

    socket.on('error', (error) => {
        console.error('WebSocket error:', error);
    });
}

// Start watching a deployment
function watchDeployment(deploymentId) {
    currentDeploymentId = deploymentId;

    // Initialize WebSocket if not already done
    if (!socket) {
        initializeWebSocket();
    }

    // Show the console
    showDeploymentConsole(deploymentId);
}

// Add log to console
function addConsoleLog(message, type = 'log') {
    const consoleEl = document.getElementById('deployment-console-logs');
    if (!consoleEl) return;

    const logEntry = document.createElement('div');
    logEntry.className = `console-log console-log-${type}`;
    logEntry.textContent = message;

    consoleEl.appendChild(logEntry);

    // Auto-scroll to bottom
    consoleEl.scrollTop = consoleEl.scrollHeight;

    // Limit console to 1000 entries
    while (consoleEl.children.length > 1000) {
        consoleEl.removeChild(consoleEl.firstChild);
    }
}

// Show deployment console
function showDeploymentConsole(deploymentId) {
    const progressDiv = document.getElementById('deployment-progress');
    const consoleDiv = document.getElementById('deployment-console');

    if (progressDiv) {
        progressDiv.style.display = 'block';
    }

    if (consoleDiv) {
        consoleDiv.style.display = 'block';
        const logsEl = document.getElementById('deployment-console-logs');
        if (logsEl) {
            logsEl.innerHTML = ''; // Clear previous logs
        }
        addConsoleLog(`📦 Starting deployment ${deploymentId}...`, 'system');
    }
}

// Hide deployment console
function hideDeploymentConsole() {
    const consoleDiv = document.getElementById('deployment-console');
    if (consoleDiv) {
        consoleDiv.style.display = 'none';
    }
    currentDeploymentId = null;
}

// Export current logs
function exportConsoleLogs() {
    const logsEl = document.getElementById('deployment-console-logs');
    if (!logsEl) return;

    const logs = Array.from(logsEl.children).map(el => el.textContent).join('\n');
    const blob = new Blob([logs], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `deployment-${currentDeploymentId}-logs.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast('Logs exported successfully', 'success');
}

// Clear console
function clearConsole() {
    const logsEl = document.getElementById('deployment-console-logs');
    if (logsEl) {
        logsEl.innerHTML = '';
        addConsoleLog('Console cleared', 'system');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Initialize WebSocket when page loads
    initializeWebSocket();
});
