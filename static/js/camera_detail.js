/**
 * Camera Detail Page - Real-time Detection Tracking
 */

// Get camera ID from URL
const cameraId = parseInt(window.location.pathname.split('/').pop());

// Detection tracking
let detectionCount = 0;
let startTime = null;
let statsInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    initializeWebSocket();
    initializeControls();
    loadInitialStats();
    startStatsUpdater();
});

/**
 * Initialize WebSocket connection for real-time updates
 */
function initializeWebSocket() {
    if (!window.socket) {
        console.error('Socket.IO not initialized');
        return;
    }

    // Listen for new events
    window.socket.on('new_event', function(data) {
        console.log('New event received:', data);
        
        // Only process events for this camera
        if (data.camera_id === cameraId) {
            handleNewDetection(data);
        }
    });

    // Listen for alerts
    window.socket.on('alert', function(data) {
        console.log('Alert received:', data);
        
        if (data.camera_id === cameraId && data.type === 'fight_detected') {
            showDetectionAlert(data);
        }
    });

    console.log('WebSocket listeners initialized for camera', cameraId);
}

/**
 * Initialize control buttons
 */
function initializeControls() {
    // Start button
    const startBtns = document.querySelectorAll('#start-btn, #start-btn-center');
    startBtns.forEach(btn => {
        if (btn) {
            btn.addEventListener('click', startDetection);
        }
    });

    // Stop button
    const stopBtn = document.getElementById('stop-btn');
    if (stopBtn) {
        stopBtn.addEventListener('click', stopDetection);
    }
}

/**
 * Start detection for this camera
 */
async function startDetection() {
    try {
        const response = await window.app.apiRequest(`/detection/start/${cameraId}`, 'POST');
        
        if (response.success) {
            showToast('Success', 'Detection started', 'success');
            
            // Reload page to update UI
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showToast('Error', response.message, 'danger');
        }
    } catch (error) {
        showToast('Error', error.message, 'danger');
    }
}

/**
 * Stop detection for this camera
 */
async function stopDetection() {
    try {
        const response = await window.app.apiRequest(`/detection/stop/${cameraId}`, 'POST');
        
        if (response.success) {
            showToast('Success', 'Detection stopped', 'info');
            
            // Reload page to update UI
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showToast('Error', response.message, 'danger');
        }
    } catch (error) {
        showToast('Error', error.message, 'danger');
    }
}

/**
 * Load initial statistics
 */
async function loadInitialStats() {
    try {
        const response = await window.app.apiRequest(`/detection/status/${cameraId}`);
        
        if (response.success) {
            updateStats(response.status);
            startTime = new Date();
        }
    } catch (error) {
        console.log('Camera not active or error loading stats:', error);
    }
}

/**
 * Update statistics display
 */
function updateStats(stats) {
    if (!stats) return;
    
    // Update counters
    document.getElementById('total-frames').textContent = 
        stats.frame_count ? stats.frame_count.toLocaleString() : '0';
    
    document.getElementById('detections-count').textContent = 
        stats.detection_count ? stats.detection_count.toLocaleString() : '0';
    
    // Calculate FPS
    const fps = stats.fps || 0;
    document.getElementById('current-fps').textContent = fps.toFixed(1);
    
    // Update detection count
    detectionCount = stats.detection_count || 0;
    document.getElementById('detection-badge').textContent = detectionCount;
}

/**
 * Start stats updater
 */
function startStatsUpdater() {
    // Update active time every second
    statsInterval = setInterval(() => {
        if (startTime) {
            const elapsed = Math.floor((new Date() - startTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            document.getElementById('active-time').textContent = 
                `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
        
        // Refresh stats from server every 5 seconds
        if (Date.now() % 5000 < 1000) {
            loadInitialStats();
        }
    }, 1000);
}

/**
 * Handle new detection
 */
function handleNewDetection(eventData) {
    console.log('Handling new detection:', eventData);
    
    // Update detection count
    detectionCount++;
    document.getElementById('detection-badge').textContent = detectionCount;
    document.getElementById('detections-count').textContent = detectionCount;
    
    // Add to detection feed
    addToDetectionFeed(eventData);
    
    // Show alert
    showDetectionAlert({
        confidence: eventData.confidence,
        timestamp: eventData.start_time || new Date().toISOString()
    });
    
    // Play sound (optional)
    playAlertSound();
}

/**
 * Add detection to feed
 */
function addToDetectionFeed(eventData) {
    const feed = document.getElementById('detection-feed');
    
    // Clear "no detections" message if exists
    const emptyMsg = feed.querySelector('.text-muted');
    if (emptyMsg) {
        feed.innerHTML = '';
    }
    
    // Create detection item
    const item = document.createElement('div');
    item.className = 'list-group-item list-group-item-action detection-item-new';
    
    const confidence = Math.round((eventData.confidence || 0) * 100);
    const timestamp = new Date(eventData.start_time || Date.now());
    const timeStr = timestamp.toLocaleTimeString();
    
    item.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
                <div class="d-flex align-items-center mb-1">
                    <i class="fas fa-exclamation-triangle text-danger me-2"></i>
                    <strong>Fight Detected</strong>
                </div>
                <small class="text-muted">
                    <i class="far fa-clock"></i> ${timeStr}
                </small>
            </div>
            <div class="text-end">
                <span class="badge bg-danger">${confidence}%</span>
            </div>
        </div>
    `;
    
    // Add animation class
    setTimeout(() => {
        item.classList.remove('detection-item-new');
    }, 500);
    
    // Insert at top
    feed.insertBefore(item, feed.firstChild);
    
    // Keep only last 20 items
    while (feed.children.length > 20) {
        feed.removeChild(feed.lastChild);
    }
}

/**
 * Show detection alert
 */
function showDetectionAlert(data) {
    const alert = document.getElementById('detection-alert');
    const confidence = Math.round((data.confidence || 0) * 100);
    const timestamp = new Date(data.timestamp || Date.now());
    
    document.getElementById('detection-confidence').textContent = confidence + '%';
    document.getElementById('detection-time').textContent = 
        'Detected at ' + timestamp.toLocaleTimeString();
    
    alert.classList.remove('d-none');
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        alert.classList.add('d-none');
    }, 5000);
}

/**
 * Play alert sound
 */
function playAlertSound() {
    // Create a simple beep using Web Audio API
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
        console.log('Could not play alert sound:', e);
    }
}

/**
 * Show toast notification
 */
function showToast(title, message, type = 'info') {
    const toast = document.getElementById('liveToast');
    const toastTitle = document.getElementById('toast-title');
    const toastBody = document.getElementById('toast-body');
    
    toastTitle.textContent = title;
    toastBody.textContent = message;
    
    // Update colors based on type
    toast.className = 'toast show';
    if (type === 'success') {
        toast.classList.add('bg-success', 'text-white');
    } else if (type === 'danger') {
        toast.classList.add('bg-danger', 'text-white');
    }
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (statsInterval) {
        clearInterval(statsInterval);
    }
});

// Add CSS for animation
const style = document.createElement('style');
style.textContent = `
    .detection-item-new {
        animation: slideInLeft 0.3s ease-out;
        background-color: #fff3cd !important;
    }
    
    @keyframes slideInLeft {
        from {
            transform: translateX(-20px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    #detection-alert {
        animation: pulse 0.5s ease-in-out;
    }
    
    @keyframes pulse {
        0%, 100% {
            transform: scale(1);
        }
        50% {
            transform: scale(1.02);
        }
    }
`;
document.head.appendChild(style);


