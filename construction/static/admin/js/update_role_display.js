document.addEventListener('DOMContentLoaded', function() {
    // Функция для обновления отображения роли
    function updateRoleDisplay(select) {
        const row = select.closest('tr');
        const roleBadge = row.querySelector('.role-badge-display');
        
        if (roleBadge) {
            const selectedOption = select.options[select.selectedIndex];
            const roleValue = selectedOption.value;
            const roleText = selectedOption.textContent.trim();
            
            // Обновляем отображение роли
            roleBadge.textContent = roleText;
            roleBadge.setAttribute('data-role', roleValue);
            
            // Обновляем цвет
            const colors = {
                'admin': '#dc3545',    // красный
                'foreman': '#0d6efd',  // синий
                'client': '#198754',   // зеленый
                'worker': '#6c757d',   // серый
            };
            
            roleBadge.style.backgroundColor = colors[roleValue] || '#000000';
        }
    }
    
    // Находим все выпадающие списки ролей
    const roleSelects = document.querySelectorAll('select[name$="-role"]');
    
    // Инициализируем обработчики для существующих элементов
    roleSelects.forEach(select => {
        // Обновляем отображение при загрузке
        updateRoleDisplay(select);
        
        // Обработчик изменения выбора роли
        select.addEventListener('change', function() {
            updateRoleDisplay(this);
        });
    });
    
    // Обработчик для динамически загруженных элементов (если используется AJAX)
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) { // Проверяем, что это элемент
                    const newSelects = node.querySelectorAll ? node.querySelectorAll('select[name$="-role"]') : [];
                    newSelects.forEach(select => {
                        updateRoleDisplay(select);
                        select.addEventListener('change', function() {
                            updateRoleDisplay(this);
                        });
                    });
                }
            });
        });
    });
    
    // Начинаем наблюдение за изменениями в DOM
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});
