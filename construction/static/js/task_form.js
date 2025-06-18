// Инициализация Select2 для выбора нескольких исполнителей
$(document).ready(function() {
    $('.select2-multiple').select2({
        theme: 'bootstrap-5',
        width: '100%',
        placeholder: 'Выберите исполнителей',
        allowClear: true,
        closeOnSelect: false,
        language: 'ru'
    });
    
    // Обработка формы для поддержки required с Select2
    $('form').on('submit', function() {
        var $select = $('#assigned_to');
        if ($select.val() && $select.val().length > 0) {
            return true;
        }
        
        // Показываем сообщение об ошибке, если не выбран ни один исполнитель
        $select.siblings('.select2-container').addClass('is-invalid');
        $('<div class="invalid-feedback d-block">Пожалуйста, выберите хотя бы одного исполнителя</div>').insertAfter($select.siblings('.select2-container'));
        return false;
    });
    
    // Удаляем сообщение об ошибке при выборе исполнителя
    $('#assigned_to').on('change', function() {
        $(this).siblings('.select2-container').removeClass('is-invalid');
        $(this).siblings('.invalid-feedback').remove();
    });
});
