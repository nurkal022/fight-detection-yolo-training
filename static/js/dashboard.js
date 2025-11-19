// Dashboard specific JavaScript

// Load statistics
async function loadStatistics() {
    try {
        const data = await window.app.apiRequest('/api/statistics/summary');
        
        if (data.success) {
            const stats = data.statistics;
            
            // Update cards
            document.getElementById('total-cameras').textContent = stats.total_cameras;
            document.getElementById('active-cameras').textContent = stats.active_cameras;
            document.getElementById('events-24h').textContent = stats.events_24h;
            document.getElementById('total-events').textContent = stats.total_events;
        }
    } catch (error) {
        console.error('Failed to load statistics:', error);
    }
}

// Load recent events
async function loadRecentEvents() {
    try {
        const data = await window.app.apiRequest('/api/events?per_page=5');
        
        if (data.success && data.events.length > 0) {
            const container = document.getElementById('recent-events-list');
            container.innerHTML = '';
            
            data.events.forEach(event => {
                const eventDiv = document.createElement('div');
                eventDiv.className = 'event-item';
                eventDiv.innerHTML = `
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <div class="event-camera">
                                <i class="fas fa-camera"></i> ${event.camera_name}
                            </div>
                            <div class="event-time">
                                <i class="fas fa-clock"></i> ${window.app.formatDateTime(event.start_time)}
                            </div>
                        </div>
                        <div class="text-end">
                            <span class="badge bg-${event.confidence >= 0.8 ? 'danger' : 'warning'}">
                                ${Math.round(event.confidence * 100)}%
                            </span>
                            ${event.duration ? `<div class="text-muted small">${window.app.formatDuration(event.duration)}</div>` : ''}
                        </div>
                    </div>
                `;
                container.appendChild(eventDiv);
            });
        } else {
            document.getElementById('recent-events-list').innerHTML = 
                '<p class="text-muted text-center py-4">Нет событий</p>';
        }
    } catch (error) {
        console.error('Failed to load recent events:', error);
        document.getElementById('recent-events-list').innerHTML = 
            '<p class="text-danger text-center py-4">Ошибка загрузки событий</p>';
    }
}

// Load system status
async function loadSystemStatus() {
    try {
        const data = await window.app.apiRequest('/detection/stats');
        
        if (data.success) {
            const container = document.getElementById('system-status-details');
            const stats = data.stats;
            
            container.innerHTML = `
                <div class="row">
                    <div class="col-md-4">
                        <div class="mb-3">
                            <strong>Активных потоков:</strong>
                            <span class="badge bg-success ms-2">${stats.active_streams}</span>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <strong>Активных событий:</strong>
                            <span class="badge bg-warning ms-2">${stats.event_stats.active_events}</span>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <strong>Камер с историей:</strong>
                            <span class="badge bg-info ms-2">${stats.event_stats.cameras_with_history}</span>
                        </div>
                    </div>
                </div>
                ${stats.streams.length > 0 ? `
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Camera ID</th>
                                    <th>Frames</th>
                                    <th>Detections</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${stats.streams.map(stream => `
                                    <tr>
                                        <td>${stream.camera_id}</td>
                                        <td>${stream.frame_count}</td>
                                        <td>${stream.detection_count}</td>
                                        <td>
                                            <span class="badge bg-${stream.active ? 'success' : 'secondary'}">
                                                ${stream.active ? 'Active' : 'Inactive'}
                                            </span>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                ` : '<p class="text-muted text-center">Нет активных потоков</p>'}
            `;
        }
    } catch (error) {
        console.error('Failed to load system status:', error);
        document.getElementById('system-status-details').innerHTML = 
            '<p class="text-danger text-center py-4">Ошибка загрузки статуса системы</p>';
    }
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Load initial data
    loadStatistics();
    loadRecentEvents();
    loadSystemStatus();
    
    // Refresh data periodically
    setInterval(loadStatistics, 10000); // Every 10 seconds
    setInterval(loadRecentEvents, 15000); // Every 15 seconds
    setInterval(loadSystemStatus, 5000); // Every 5 seconds
    
    // Listen for new events via WebSocket
    const socket = window.app.socket();
    if (socket) {
        socket.on('new_event', function(data) {
            // Reload events list
            loadRecentEvents();
            loadStatistics();
        });
    }
});

