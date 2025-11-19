/**
 * Webcam Launch Page
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeWebcamPage();
});

/**
 * Initialize webcam page
 */
function initializeWebcamPage() {
    // Check cameras button
    const checkBtn = document.getElementById('check-cameras-btn');
    if (checkBtn) {
        checkBtn.addEventListener('click', checkAvailableCameras);
    }

    // Launch button
    const launchBtn = document.getElementById('launch-btn');
    if (launchBtn) {
        launchBtn.addEventListener('click', launchWebcam);
    }

    // Auto-check cameras on page load
    setTimeout(checkAvailableCameras, 500);
}

/**
 * Check available cameras
 */
async function checkAvailableCameras() {
    const resultDiv = document.getElementById('camera-check-result');
    const checkBtn = document.getElementById('check-cameras-btn');
    
    // Show loading
    resultDiv.innerHTML = `
        <div class="text-center">
            <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
            <span class="ms-2">Поиск камер...</span>
        </div>
    `;
    checkBtn.disabled = true;

    try {
        const response = await window.app.apiRequest('/diagnostics/list-cameras');

        if (response.success && response.cameras.length > 0) {
            // Display available cameras
            let html = `
                <div class="alert alert-success">
                    <h6 class="alert-heading">
                        <i class="fas fa-check-circle"></i> 
                        Найдено камер: ${response.cameras.length}
                    </h6>
                    <ul class="mb-0 mt-2">
            `;

            response.cameras.forEach(cam => {
                html += `<li class="mb-1">
                    <strong>Камера ${cam.index}</strong>`;
                
                if (cam.frame_size) {
                    html += ` - ${cam.frame_size.width}x${cam.frame_size.height}`;
                }
                
                if (cam.can_read === false) {
                    html += ' <span class="badge bg-warning">Не может читать кадры</span>';
                } else {
                    html += ' <span class="badge bg-success">Доступна</span>';
                }
                
                html += '</li>';
            });

            html += `
                    </ul>
                    <hr>
                    <small class="text-muted">
                        <i class="fas fa-lightbulb"></i>
                        Выберите индекс камеры из списка выше
                    </small>
                </div>
            `;

            resultDiv.innerHTML = html;

            // Auto-select first camera
            if (response.cameras.length > 0) {
                const cameraSelect = document.getElementById('camera-index');
                cameraSelect.value = response.cameras[0].index.toString();
            }

        } else {
            // No cameras found
            resultDiv.innerHTML = `
                <div class="alert alert-warning">
                    <h6 class="alert-heading">
                        <i class="fas fa-exclamation-triangle"></i>
                        Камеры не найдены
                    </h6>
                    <p class="mb-2">Возможные причины:</p>
                    <ul class="mb-0">
                        <li>Камера используется другим приложением</li>
                        <li>Нет разрешения на доступ к камере</li>
                        <li>Камера не подключена</li>
                    </ul>
                </div>
            `;
        }
    } catch (error) {
        resultDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-times-circle"></i>
                Ошибка: ${error.message}
            </div>
        `;
    } finally {
        checkBtn.disabled = false;
    }
}

/**
 * Launch webcam
 */
async function launchWebcam() {
    const cameraIndex = document.getElementById('camera-index').value;
    const cameraName = document.getElementById('camera-name').value.trim();
    const launchBtn = document.getElementById('launch-btn');
    const statusDiv = document.getElementById('status-messages');

    // Validation
    if (!cameraName) {
        showStatus('danger', 'Пожалуйста, введите название камеры');
        return;
    }

    // Show loading modal
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    loadingModal.show();

    // Disable button
    launchBtn.disabled = true;
    statusDiv.innerHTML = '';

    try {
        // Step 1: Check camera availability
        updateLoadingMessage('Проверка доступности камеры...');
        
        const checkResponse = await window.app.apiRequest(`/diagnostics/check-camera/${cameraIndex}`);

        if (!checkResponse.success || !checkResponse.available) {
            throw new Error(checkResponse.message || 'Камера недоступна');
        }

        if (checkResponse.can_read === false) {
            throw new Error('Камера не может читать кадры. Проверьте разрешения.');
        }

        // Step 2: Create/get camera
        updateLoadingMessage('Добавление камеры в систему...');
        
        const createResponse = await window.app.apiRequest('/quick/quick-webcam', 'POST', {
            camera_index: cameraIndex,
            camera_name: cameraName
        });

        if (!createResponse.success) {
            throw new Error(createResponse.message || 'Не удалось создать камеру');
        }

        const cameraId = createResponse.camera_id;

        // Step 3: Start detection
        updateLoadingMessage('Запуск детекции...');
        
        const startResponse = await window.app.apiRequest(`/detection/start/${cameraId}`, 'POST');

        if (!startResponse.success) {
            throw new Error(startResponse.message || 'Не удалось запустить детекцию');
        }

        // Step 4: Success - redirect
        updateLoadingMessage('Готово! Перенаправление...', 'success');

        setTimeout(() => {
            window.location.href = `/camera/${cameraId}`;
        }, 1000);

    } catch (error) {
        console.error('Launch error:', error);
        
        loadingModal.hide();
        
        showStatus('danger', `
            <strong>Ошибка запуска:</strong><br>
            ${error.message}
            <hr>
            <small>
                <strong>Что делать:</strong><br>
                • Проверьте что камера не используется другим приложением<br>
                • Дайте разрешение на доступ к камере<br>
                • Попробуйте другой индекс камеры
            </small>
        `);
        
        launchBtn.disabled = false;
    }
}

/**
 * Update loading modal message
 */
function updateLoadingMessage(message, type = 'info') {
    const messageEl = document.getElementById('loading-message');
    const detailEl = document.getElementById('loading-detail');
    
    messageEl.textContent = message;
    
    if (type === 'success') {
        messageEl.innerHTML = `<i class="fas fa-check-circle text-success"></i> ${message}`;
    }
}

/**
 * Show status message
 */
function showStatus(type, message) {
    const statusDiv = document.getElementById('status-messages');
    
    const alertClass = type === 'danger' ? 'alert-danger' : 
                      type === 'success' ? 'alert-success' : 
                      type === 'warning' ? 'alert-warning' : 'alert-info';
    
    statusDiv.innerHTML = `
        <div class="alert ${alertClass}" role="alert">
            ${message}
        </div>
    `;
}

