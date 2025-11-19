// Global Socket.IO connection
let socket;

// Initialize Socket.IO
function initSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to server');
        updateSystemStatus(true);
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        updateSystemStatus(false);
    });
    
    socket.on('new_event', function(data) {
        console.log('New event:', data);
        showNotification('Обнаружена драка!', `Камера: ${data.camera_name}`, 'danger');
        playAlertSound();
    });
    
    socket.on('alert', function(data) {
        console.log('Alert:', data);
    });
}

// Update system status indicator
function updateSystemStatus(isConnected) {
    const statusBadge = document.getElementById('system-status');
    if (statusBadge) {
        if (isConnected) {
            statusBadge.className = 'badge bg-success';
            statusBadge.innerHTML = '<i class="fas fa-circle"></i> Система активна';
        } else {
            statusBadge.className = 'badge bg-danger';
            statusBadge.innerHTML = '<i class="fas fa-circle"></i> Система отключена';
        }
    }
}

// Show notification
function showNotification(title, message, type = 'info') {
    const container = document.getElementById('alert-container');
    if (!container) return;
    
    const alertId = 'alert-' + Date.now();
    const alertDiv = document.createElement('div');
    alertDiv.id = alertId;
    alertDiv.className = `alert alert-${type} alert-notification alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        <strong>${title}</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(alertDiv);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alert = document.getElementById(alertId);
        if (alert) {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }
    }, 5000);
}

// Play alert sound
function playAlertSound() {
    // Create audio context and play a simple beep
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    } catch (e) {
        console.log('Audio not supported:', e);
    }
}

// Format date/time
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// Format duration
function formatDuration(seconds) {
    if (!seconds) return '-';
    
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    
    if (mins > 0) {
        return `${mins}м ${secs}с`;
    }
    return `${secs}с`;
}

// API helper functions
async function apiRequest(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.message || 'Request failed');
        }
        
        return result;
    } catch (error) {
        console.error('API request error:', error);
        throw error;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Socket.IO
    initSocket();
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    console.log('Application initialized');
});

// Export functions for use in other scripts
window.app = {
    showNotification,
    formatDateTime,
    formatDuration,
    apiRequest,
    socket: () => socket
};

