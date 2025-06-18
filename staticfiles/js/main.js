// Функция для отображения уведомлений
function showToast(type, message) {
    const toastEl = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');
    const toastHeader = toastEl.querySelector('.toast-header');
    
    if (toastEl && toastMessage) {
        // Устанавливаем сообщение
        toastMessage.textContent = message;
        
        // Устанавливаем цвет в зависимости от типа уведомления
        toastHeader.className = 'toast-header text-white ' + 
            (type === 'success' ? 'bg-success' : 
             type === 'error' ? 'bg-danger' : 
             type === 'warning' ? 'bg-warning' : 'bg-primary');
        
        // Показываем уведомление
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    }
}

// Инициализация всех всплывающих подсказок
document.addEventListener('DOMContentLoaded', function() {
    // Инициализация тултипов
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Инициализация попапов
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Обработчик для кнопки копирования в буфер обмена
    document.querySelectorAll('[data-copy]').forEach(button => {
        button.addEventListener('click', function() {
            const textToCopy = this.getAttribute('data-copy');
            if (navigator.clipboard) {
                navigator.clipboard.writeText(textToCopy).then(() => {
                    const originalText = this.innerHTML;
                    this.innerHTML = '<i class="bi bi-check"></i> Скопировано!';
                    setTimeout(() => {
                        this.innerHTML = originalText;
                    }, 2000);
                });
            }
        });
    });
});

// Функция для подтверждения действия
function confirmAction(message, callback) {
    if (confirm(message || 'Вы уверены?')) {
        if (typeof callback === 'function') {
            callback();
        }
    }
}

// Функция для загрузки файлов с прогрессом
function uploadFileWithProgress(formElement, progressBarId, callback) {
    const formData = new FormData(formElement);
    const xhr = new XMLHttpRequest();
    const progressBar = document.getElementById(progressBarId);
    
    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            const percentComplete = Math.round((e.loaded / e.total) * 100);
            if (progressBar) {
                progressBar.style.width = percentComplete + '%';
                progressBar.setAttribute('aria-valuenow', percentComplete);
                progressBar.textContent = percentComplete + '%';
            }
        }
    };
    
    xhr.onload = function() {
        if (xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            if (typeof callback === 'function') {
                callback(null, response);
            }
        } else {
            if (typeof callback === 'function') {
                callback(new Error('Ошибка загрузки файла'));
            }
        }
    };
    
    xhr.open('POST', formElement.action, true);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.send(formData);
}
