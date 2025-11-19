// Live monitoring JavaScript

// Start detection for a camera
async function startDetection(cameraId) {
    try {
        const data = await window.app.apiRequest(`/detection/start/${cameraId}`, 'POST');
        
        if (data.success) {
            window.app.showNotification('Успех', data.message, 'success');
            
            // Update UI
            const card = document.querySelector(`[data-camera-id="${cameraId}"]`);
            const startBtn = card.querySelector('.btn-start');
            const stopBtn = card.querySelector('.btn-stop');
            const streamImg = card.querySelector('.camera-stream');
            const noStream = card.querySelector('.no-stream');
            const statusBadge = card.querySelector('.camera-status');
            
            startBtn.style.display = 'none';
            stopBtn.style.display = 'inline-block';
            streamImg.style.display = 'block';
            noStream.classList.add('d-none');
            statusBadge.className = 'badge bg-success camera-status';
            statusBadge.textContent = 'Активна';
            
            // Reload stream
            streamImg.src = `/detection/stream/${cameraId}?t=${Date.now()}`;
        } else {
            window.app.showNotification('Ошибка', data.message, 'danger');
        }
    } catch (error) {
        window.app.showNotification('Ошибка', error.message, 'danger');
    }
}

// Stop detection for a camera
async function stopDetection(cameraId) {
    try {
        const data = await window.app.apiRequest(`/detection/stop/${cameraId}`, 'POST');
        
        if (data.success) {
            window.app.showNotification('Успех', data.message, 'success');
            
            // Update UI
            const card = document.querySelector(`[data-camera-id="${cameraId}"]`);
            const startBtn = card.querySelector('.btn-start');
            const stopBtn = card.querySelector('.btn-stop');
            const streamImg = card.querySelector('.camera-stream');
            const noStream = card.querySelector('.no-stream');
            const statusBadge = card.querySelector('.camera-status');
            
            startBtn.style.display = 'inline-block';
            stopBtn.style.display = 'none';
            streamImg.style.display = 'none';
            noStream.classList.remove('d-none');
            statusBadge.className = 'badge bg-secondary camera-status';
            statusBadge.textContent = 'Неактивна';
        } else {
            window.app.showNotification('Ошибка', data.message, 'danger');
        }
    } catch (error) {
        window.app.showNotification('Ошибка', error.message, 'danger');
    }
}

// Show event toast
function showEventToast(event) {
    const toast = document.getElementById('event-toast');
    const message = document.getElementById('event-toast-message');
    
    message.textContent = `Камера: ${event.camera_name} (${Math.round(event.confidence * 100)}%)`;
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// Initialize live monitoring
document.addEventListener('DOMContentLoaded', function() {
    
    // Attach event listeners to start/stop buttons
    document.querySelectorAll('.btn-start').forEach(btn => {
        btn.addEventListener('click', function() {
            const cameraId = this.dataset.cameraId;
            startDetection(cameraId);
        });
    });
    
    document.querySelectorAll('.btn-stop').forEach(btn => {
        btn.addEventListener('click', function() {
            const cameraId = this.dataset.cameraId;
            stopDetection(cameraId);
        });
    });
    
    // Listen for new events via WebSocket
    const socket = window.app.socket();
    if (socket) {
        socket.on('new_event', function(data) {
            showEventToast(data);
        });
    }
    
    // Refresh stream images periodically to detect disconnections
    setInterval(() => {
        document.querySelectorAll('.camera-stream').forEach(img => {
            if (img.style.display !== 'none') {
                // Check if image is loaded
                if (img.complete && img.naturalHeight === 0) {
                    // Image failed to load, might be disconnected
                    console.warn('Stream might be disconnected:', img.src);
                }
            }
        });
    }, 5000);
});

