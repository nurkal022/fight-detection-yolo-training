// Settings page JavaScript

// Add camera
async function addCamera() {
    const name = document.getElementById('camera_name').value;
    const source = document.getElementById('camera_source').value;
    const sourceType = document.getElementById('camera_source_type').value;
    const location = document.getElementById('camera_location').value;
    const confidence = parseFloat(document.getElementById('camera_confidence').value);
    
    try {
        const data = await window.app.apiRequest('/api/cameras', 'POST', {
            name: name,
            source: source,
            source_type: sourceType,
            location: location,
            confidence_threshold: confidence
        });
        
        if (data.success) {
            window.app.showNotification('Успех', 'Камера добавлена', 'success');
            
            // Close modal and reload page
            const modal = bootstrap.Modal.getInstance(document.getElementById('addCameraModal'));
            modal.hide();
            
            setTimeout(() => location.reload(), 500);
        } else {
            window.app.showNotification('Ошибка', data.message, 'danger');
        }
    } catch (error) {
        window.app.showNotification('Ошибка', error.message, 'danger');
    }
}

// Edit camera
async function editCamera(cameraId) {
    try {
        const data = await window.app.apiRequest(`/api/cameras/${cameraId}`);
        
        if (data.success) {
            const camera = data.camera;
            
            document.getElementById('edit_camera_id').value = camera.id;
            document.getElementById('edit_camera_name').value = camera.name;
            document.getElementById('edit_camera_source').value = camera.source;
            document.getElementById('edit_camera_source_type').value = camera.source_type;
            document.getElementById('edit_camera_location').value = camera.location || '';
            document.getElementById('edit_camera_confidence').value = camera.confidence_threshold;
            document.getElementById('edit_camera_confidence_value').textContent = 
                Math.round(camera.confidence_threshold * 100);
            
            const modal = new bootstrap.Modal(document.getElementById('editCameraModal'));
            modal.show();
        }
    } catch (error) {
        window.app.showNotification('Ошибка', error.message, 'danger');
    }
}

// Update camera
async function updateCamera() {
    const cameraId = document.getElementById('edit_camera_id').value;
    const name = document.getElementById('edit_camera_name').value;
    const source = document.getElementById('edit_camera_source').value;
    const sourceType = document.getElementById('edit_camera_source_type').value;
    const location = document.getElementById('edit_camera_location').value;
    const confidence = parseFloat(document.getElementById('edit_camera_confidence').value);
    
    try {
        const data = await window.app.apiRequest(`/api/cameras/${cameraId}`, 'PUT', {
            name: name,
            source: source,
            source_type: sourceType,
            location: location,
            confidence_threshold: confidence
        });
        
        if (data.success) {
            window.app.showNotification('Успех', 'Камера обновлена', 'success');
            
            const modal = bootstrap.Modal.getInstance(document.getElementById('editCameraModal'));
            modal.hide();
            
            setTimeout(() => location.reload(), 500);
        } else {
            window.app.showNotification('Ошибка', data.message, 'danger');
        }
    } catch (error) {
        window.app.showNotification('Ошибка', error.message, 'danger');
    }
}

// Delete camera
async function deleteCamera(cameraId) {
    if (!confirm('Вы уверены, что хотите удалить эту камеру?')) {
        return;
    }
    
    try {
        const data = await window.app.apiRequest(`/api/cameras/${cameraId}`, 'DELETE');
        
        if (data.success) {
            window.app.showNotification('Успех', 'Камера удалена', 'success');
            
            const row = document.querySelector(`tr[data-camera-id="${cameraId}"]`);
            row.remove();
        } else {
            window.app.showNotification('Ошибка', data.message, 'danger');
        }
    } catch (error) {
        window.app.showNotification('Ошибка', error.message, 'danger');
    }
}

// Initialize settings page
document.addEventListener('DOMContentLoaded', function() {
    // Camera confidence slider
    const cameraConfidence = document.getElementById('camera_confidence');
    const cameraConfidenceValue = document.getElementById('camera_confidence_value');
    
    if (cameraConfidence) {
        cameraConfidence.addEventListener('input', function() {
            cameraConfidenceValue.textContent = Math.round(this.value * 100);
        });
    }
    
    // Edit camera confidence slider
    const editCameraConfidence = document.getElementById('edit_camera_confidence');
    const editCameraConfidenceValue = document.getElementById('edit_camera_confidence_value');
    
    if (editCameraConfidence) {
        editCameraConfidence.addEventListener('input', function() {
            editCameraConfidenceValue.textContent = Math.round(this.value * 100);
        });
    }
    
    // System settings confidence slider
    const confidenceThreshold = document.getElementById('confidence_threshold');
    const confidenceValue = document.getElementById('confidence_value');
    
    if (confidenceThreshold) {
        confidenceThreshold.addEventListener('input', function() {
            confidenceValue.textContent = Math.round(this.value * 100);
        });
    }
    
    // Save camera button
    const saveCameraBtn = document.getElementById('save-camera-btn');
    if (saveCameraBtn) {
        saveCameraBtn.addEventListener('click', addCamera);
    }
    
    // Update camera button
    const updateCameraBtn = document.getElementById('update-camera-btn');
    if (updateCameraBtn) {
        updateCameraBtn.addEventListener('click', updateCamera);
    }
    
    // Edit camera buttons
    document.querySelectorAll('.btn-edit-camera').forEach(btn => {
        btn.addEventListener('click', function() {
            const cameraId = this.dataset.cameraId;
            editCamera(cameraId);
        });
    });
    
    // Delete camera buttons
    document.querySelectorAll('.btn-delete-camera').forEach(btn => {
        btn.addEventListener('click', function() {
            const cameraId = this.dataset.cameraId;
            deleteCamera(cameraId);
        });
    });
    
    // System settings form
    const systemSettingsForm = document.getElementById('system-settings-form');
    if (systemSettingsForm) {
        systemSettingsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            window.app.showNotification('Успех', 'Настройки сохранены', 'success');
        });
    }

    // Send test telegram button
    const sendTestTelegramBtn = document.getElementById('send-test-telegram');
    if (sendTestTelegramBtn) {
        sendTestTelegramBtn.addEventListener('click', async function() {
            try {
                // Default sample image from training results
                const payload = { image_path: 'runs/pose_training/fight_detection_pose/results.png' };
                const resp = await window.app.apiRequest('/api/notifications/test-telegram', 'POST', payload);
                if (resp.success) {
                    window.app.showNotification('Успех', 'Тестовое сообщение Telegram отправлено', 'success');
                } else {
                    window.app.showNotification('Ошибка', resp.message || 'Не удалось отправить сообщение', 'danger');
                }
            } catch (err) {
                window.app.showNotification('Ошибка', err.message, 'danger');
            }
        });
    }

    // Send test detection button (with real detection from dataset)
    const sendTestDetectionBtn = document.getElementById('send-test-detection');
    if (sendTestDetectionBtn) {
        sendTestDetectionBtn.addEventListener('click', async function() {
            const btn = this;
            const originalText = btn.innerHTML;
            
            // Disable button and show loading
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
            
            try {
                const resp = await window.app.apiRequest('/api/notifications/test-detection', 'POST', {});
                
                if (resp.success) {
                    const message = `Тестовая детекция отправлена ${resp.results.sent} пользователям!\n` +
                                  `Обнаружено: ${resp.detection.detected_classes.join(', ') || 'нет'}\n` +
                                  `Уверенность: ${(resp.detection.max_confidence * 100).toFixed(1)}%`;
                    window.app.showNotification('Успех', message, 'success');
                } else {
                    window.app.showNotification('Ошибка', resp.message || 'Не удалось отправить детекцию', 'danger');
                }
            } catch (err) {
                window.app.showNotification('Ошибка', err.message, 'danger');
            } finally {
                // Re-enable button
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        });
    }
});

