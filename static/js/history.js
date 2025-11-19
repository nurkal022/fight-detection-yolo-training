// History page JavaScript

// Resolve event
async function resolveEvent(eventId) {
    try {
        const data = await window.app.apiRequest(`/api/events/${eventId}`, 'PUT', {
            status: 'resolved'
        });
        
        if (data.success) {
            window.app.showNotification('Успех', 'Событие отмечено как решенное', 'success');
            
            // Update UI
            const row = document.querySelector(`tr[data-event-id="${eventId}"]`);
            const statusBadge = row.querySelector('td:nth-child(7) span');
            statusBadge.className = 'badge bg-success';
            statusBadge.textContent = 'resolved';
            
            const resolveBtn = row.querySelector('.btn-resolve');
            resolveBtn.disabled = true;
        } else {
            window.app.showNotification('Ошибка', data.message, 'danger');
        }
    } catch (error) {
        window.app.showNotification('Ошибка', error.message, 'danger');
    }
}

// Mark as false positive
async function markFalsePositive(eventId) {
    try {
        const data = await window.app.apiRequest(`/api/events/${eventId}`, 'PUT', {
            status: 'false_positive'
        });
        
        if (data.success) {
            window.app.showNotification('Успех', 'Событие отмечено как ложное срабатывание', 'success');
            
            // Update UI
            const row = document.querySelector(`tr[data-event-id="${eventId}"]`);
            const statusBadge = row.querySelector('td:nth-child(7) span');
            statusBadge.className = 'badge bg-secondary';
            statusBadge.textContent = 'false_positive';
            
            const falsePositiveBtn = row.querySelector('.btn-false-positive');
            falsePositiveBtn.disabled = true;
        } else {
            window.app.showNotification('Ошибка', data.message, 'danger');
        }
    } catch (error) {
        window.app.showNotification('Ошибка', error.message, 'danger');
    }
}

// Delete event
async function deleteEvent(eventId) {
    if (!confirm('Вы уверены, что хотите удалить это событие?')) {
        return;
    }
    
    try {
        const data = await window.app.apiRequest(`/api/events/${eventId}`, 'DELETE');
        
        if (data.success) {
            window.app.showNotification('Успех', 'Событие удалено', 'success');
            
            // Remove row from table
            const row = document.querySelector(`tr[data-event-id="${eventId}"]`);
            row.remove();
        } else {
            window.app.showNotification('Ошибка', data.message, 'danger');
        }
    } catch (error) {
        window.app.showNotification('Ошибка', error.message, 'danger');
    }
}

// Initialize history page
document.addEventListener('DOMContentLoaded', function() {
    // Attach event listeners
    document.querySelectorAll('.btn-resolve').forEach(btn => {
        btn.addEventListener('click', function() {
            const eventId = this.dataset.eventId;
            resolveEvent(eventId);
        });
    });
    
    document.querySelectorAll('.btn-false-positive').forEach(btn => {
        btn.addEventListener('click', function() {
            const eventId = this.dataset.eventId;
            markFalsePositive(eventId);
        });
    });
    
    document.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', function() {
            const eventId = this.dataset.eventId;
            deleteEvent(eventId);
        });
    });
});

