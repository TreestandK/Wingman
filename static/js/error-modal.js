// Error Modal Functions for Wingman

function showErrorModal(error) {
    const modal = document.getElementById('error-modal');
    const titleEl = document.getElementById('error-modal-title');
    const messageEl = document.getElementById('error-modal-message');
    const detailsEl = document.getElementById('error-modal-details');
    const detailsContentEl = document.getElementById('error-details-content');
    const troubleshootingEl = document.getElementById('error-troubleshooting');
    const troubleshootingStepsEl = document.getElementById('troubleshooting-steps');
    const docsEl = document.getElementById('error-docs');
    const docsLinkEl = document.getElementById('error-docs-link');

    // Set title
    titleEl.textContent = error.service ? error.service + ' Error' : 'Error';

    // Set message
    messageEl.textContent = error.message || 'An error occurred';

    // Set details
    if (error.details) {
        detailsEl.style.display = 'block';
        detailsContentEl.textContent = error.details;
        detailsContentEl.style.display = 'none'; // Hidden by default
    } else {
        detailsEl.style.display = 'none';
    }

    // Set troubleshooting steps
    if (error.troubleshooting && error.troubleshooting.length > 0) {
        troubleshootingEl.style.display = 'block';
        troubleshootingStepsEl.innerHTML = '';
        error.troubleshooting.forEach(step => {
            const li = document.createElement('li');
            li.textContent = step;
            troubleshootingStepsEl.appendChild(li);
        });
    } else {
        troubleshootingEl.style.display = 'none';
    }

    // Set documentation link
    if (error.docs_url) {
        docsEl.style.display = 'block';
        docsLinkEl.href = error.docs_url;
    } else {
        docsEl.style.display = 'none';
    }

    // Store error for copying
    window.currentError = error;

    // Show modal
    modal.style.display = 'flex';
}

function closeErrorModal() {
    document.getElementById('error-modal').style.display = 'none';
}

function toggleErrorDetails() {
    const btn = document.querySelector('.btn-collapse');
    const content = document.getElementById('error-details-content');

    if (content.style.display === 'none') {
        content.style.display = 'block';
        btn.classList.add('expanded');
        btn.innerHTML = '<i class="fas fa-chevron-up"></i> Hide Technical Details';
    } else {
        content.style.display = 'none';
        btn.classList.remove('expanded');
        btn.innerHTML = '<i class="fas fa-chevron-down"></i> Show Technical Details';
    }
}

function copyErrorDetails() {
    if (!window.currentError) return;

    const errorLines = [
        'Error: ' + window.currentError.message,
        'Service: ' + (window.currentError.service || 'Unknown'),
        'Code: ' + (window.currentError.code || 'N/A'),
        '',
        'Details:',
        window.currentError.details || 'No details available',
        ''
    ];

    if (window.currentError.troubleshooting && window.currentError.troubleshooting.length > 0) {
        errorLines.push('Troubleshooting Steps:');
        window.currentError.troubleshooting.forEach((step, i) => {
            errorLines.push((i + 1) + '. ' + step);
        });
    }

    const errorText = errorLines.join('\n');

    navigator.clipboard.writeText(errorText).then(() => {
        showToast('Error details copied to clipboard', 'success');
    }).catch(() => {
        showToast('Failed to copy error details', 'error');
    });
}

// Enhanced testConnectivity function
async function testConnectivity() {
    showToast('Testing connectivity to all services...', 'info');

    try {
        const response = await fetch('/api/test-connectivity');
        const result = await response.json();

        if (result.success !== undefined) {
            const testResults = result.tests;
            const details = result.details || {};
            const errors = result.errors || {};

            let passed = 0;
            let failed = 0;
            let notConfigured = 0;

            for (const [service, status] of Object.entries(testResults)) {
                if (status === true) {
                    passed++;
                } else if (status === false) {
                    failed++;
                } else {
                    notConfigured++;
                }
            }

            let message = 'Connectivity Test: ';
            message += passed + ' passed, ' + failed + ' failed, ' + notConfigured + ' not configured';

            if (failed === 0) {
                showToast(message, 'success');
            } else {
                showToast(message, 'warning');

                // Show detailed error modal for first failure
                const firstError = Object.values(errors)[0];
                if (firstError) {
                    setTimeout(() => showErrorModal(firstError), 500);
                }
            }
        } else {
            showToast('Connectivity test failed: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Error testing connectivity: ' + error.message, 'error');
    }
}
