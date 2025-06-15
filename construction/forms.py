from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from .models import ConstructionSite, SitePhoto, SiteComment, Task, TaskComment

User = get_user_model()

class UserRegistrationForm(UserCreationForm):
    """Форма регистрации пользователя"""
    first_name = forms.CharField(label='Имя', max_length=30, required=True)
    last_name = forms.CharField(label='Фамилия', max_length=30, required=True)
    email = forms.EmailField(label='Email', required=True)
    phone = forms.CharField(
        label='Телефон', 
        max_length=20, 
        required=False,
        help_text='Необязательное поле'
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Логин'
        self.fields['password1'].label = 'Пароль'
        self.fields['password2'].label = 'Подтверждение пароля'
        
        # Добавляем классы Bootstrap для стилизации
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Пользователь с таким логином уже существует')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже зарегистрирован')
        return email

class UserEditForm(forms.ModelForm):
    """Форма редактирования профиля пользователя"""
    ROLE_CHOICES = [
        ('worker', 'Рабочий'),
        ('foreman', 'Прораб'),
        ('client', 'Заказчик'),
    ]
    
    role = forms.ChoiceField(
        label='Роль',
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone', 'role')
        labels = {
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'email': 'Email',
            'phone': 'Телефон'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class ConstructionSiteForm(forms.ModelForm):
    """Форма для создания и редактирования строительного объекта"""
    status = forms.ChoiceField(
        choices=ConstructionSite.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Статус объекта',
        required=True
    )
    
    class Meta:
        model = ConstructionSite
        fields = ('name', 'address', 'start_date', 'end_date', 'description', 'status', 'client', 'foreman', 'workers')
        widgets = {
            'start_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }
            ),
            'end_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }
            ),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'foreman': forms.Select(attrs={'class': 'form-select'}),
            'workers': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Устанавливаем формат даты для правильного отображения
        for field_name in ['start_date', 'end_date']:
            if field_name in self.fields:
                self.fields[field_name].input_formats = ['%Y-%m-%d']
                if self.instance and getattr(self.instance, field_name):
                    self.fields[field_name].widget.attrs['value'] = getattr(self.instance, field_name).strftime('%Y-%m-%d')
        
        # Устанавливаем метки полей
        self.fields['name'].label = 'Название объекта'
        self.fields['address'].label = 'Адрес'
        self.fields['start_date'].label = 'Дата начала работ'
        self.fields['end_date'].label = 'Планируемая дата окончания'
        self.fields['description'].label = 'Описание'
        self.fields['status'].label = 'Статус объекта'
        if 'client' in self.fields:
            self.fields['client'].label = 'Заказчик (необязательно)'
        if 'foreman' in self.fields:
            self.fields['foreman'].label = 'Ответственный прораб (необязательно)'
        
        # Устанавливаем подсказки для полей
        if 'client' in self.fields:
            self.fields['client'].help_text = 'Выберите заказчика, если он зарегистрирован в системе'
        if 'foreman' in self.fields:
            self.fields['foreman'].help_text = 'Выберите прораба, если он зарегистрирован в системе'
        if 'workers' in self.fields:
            self.fields['workers'].help_text = 'Выберите одного или нескольких рабочих (необязательно)'
        
        # Устанавливаем выбор статуса из модели
        self.fields['status'].choices = ConstructionSite.STATUS_CHOICES
        
        # Добавляем классы для стилизации полей
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field_name in ['start_date', 'end_date']:
                field.widget.attrs['placeholder'] = 'гггг-мм-дд'
        
        # Делаем поля необязательными
        if 'client' in self.fields:
            self.fields['client'].required = False
        if 'foreman' in self.fields:
            self.fields['foreman'].required = False
        
        # Настройка полей в зависимости от роли пользователя
        if user and hasattr(user, 'role'):
            if user.role == 'client':
                # Клиент может выбрать только прораба
                if 'foreman' in self.fields:
                    self.fields['foreman'].queryset = User.objects.filter(role='foreman')
                    self.fields['foreman'].widget.attrs['class'] = 'form-select select2'
                if 'client' in self.fields:
                    del self.fields['client']  # Удаляем поле клиента, т.к. это сам пользователь
                
            elif user.role == 'foreman':
                # Прораб может выбрать только клиентов
                if 'client' in self.fields:
                    self.fields['client'].queryset = User.objects.filter(role='client')
                    self.fields['client'].widget.attrs['class'] = 'form-select select2'
                
            elif user.role == 'admin':
                # Админ может выбрать всех
                if 'client' in self.fields:
                    self.fields['client'].queryset = User.objects.filter(role='client')
                    self.fields['client'].widget.attrs['class'] = 'form-select select2'
                if 'foreman' in self.fields:
                    self.fields['foreman'].queryset = User.objects.filter(role='foreman')
                    self.fields['foreman'].widget.attrs['class'] = 'form-select select2'
    

    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'Дата окончания не может быть раньше даты начала')
        
        return cleaned_data

class SitePhotoForm(forms.ModelForm):
    """Форма для загрузки фотографий объекта"""
    
    class Meta:
        model = SitePhoto
        fields = ['photo', 'comment']
    
    def __init__(self, *args, **kwargs):
        # Извлекаем exclude_fields из kwargs, если он есть
        self.exclude_fields = kwargs.pop('exclude_fields', [])
        super().__init__(*args, **kwargs)
        
        # Убедимся, что exclude_fields является списком
        if not isinstance(self.exclude_fields, list):
            self.exclude_fields = []
        
        # Если fields не инициализирован, инициализируем его пустым словарем
        if not hasattr(self, 'fields') or self.fields is None:
            self.fields = {}
        
        # Применяем классы к полям
        for field_name, field in list(self.fields.items()):  # Используем list для создания копии
            # Пропускаем исключенные поля
            if field_name in self.exclude_fields:
                del self.fields[field_name]
                continue
                
            field.widget.attrs.update({'class': 'form-control'})
            
            # Добавляем атрибут required, если поле обязательно и не исключено
            if field.required and field_name not in self.exclude_fields:
                field.widget.attrs['required'] = 'required'
    
    def clean_photo(self):
        # Пропускаем валидацию, если поле photo исключено
        if self.exclude_fields and 'photo' in self.exclude_fields:
            return self.cleaned_data.get('photo')
            
        photo = self.cleaned_data.get('photo')
        if photo:
            # Проверка размера файла (максимум 10 МБ)
            max_size = 10 * 1024 * 1024  # 10 МБ
            if photo.size > max_size:
                raise forms.ValidationError('Размер файла не должен превышать 10 МБ')
            
            # Проверка типа файла
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            ext = photo.name.lower()
            if not any(ext.endswith(ext) for ext in valid_extensions):
                raise forms.ValidationError('Допустимые форматы: JPG, JPEG, PNG, GIF')
        return photo

class CommentForm(forms.ModelForm):
    """Форма для добавления комментариев к объекту"""
    class Meta:
        model = SiteComment
        fields = ('text',)
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Введите комментарий...',
                'required': 'required',
                'minlength': '3',
                'maxlength': '1000'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].label = ''  # Убираем метку поля
    
    def clean_text(self):
        text = self.cleaned_data.get('text', '').strip()
        if len(text) < 3:
            raise forms.ValidationError('Комментарий должен содержать не менее 3 символов')
        if len(text) > 1000:
            raise forms.ValidationError('Комментарий не должен превышать 1000 символов')
        return text

class UserRoleForm(forms.ModelForm):
    """Форма для изменения роли пользователя"""
    ROLE_CHOICES = [
        ('worker', 'Рабочий'),
        ('foreman', 'Прораб'),
        ('client', 'Заказчик'),
        ('admin', 'Администратор'),
    ]
    
    role = forms.ChoiceField(
        label='Роль',
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = User
        fields = ('role',)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Устанавливаем текущую роль пользователя
        if self.instance and self.instance.pk:
            self.fields['role'].initial = self.instance.role


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'assigned_to', 'construction_site', 'deadline', 'status', 'priority']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'deadline': forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local',
                    'placeholder': 'дд.мм.гггг чч:мм'
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }
        labels = {
            'title': 'Название задачи',
            'description': 'Описание',
            'assigned_to': 'Исполнители',
            'construction_site': 'Строительный объект',
            'deadline': 'Срок выполнения',
            'priority': 'Приоритет',
            'status': 'Статус',
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Настройка queryset для исполнителей и объектов
        if user and hasattr(user, 'role'):
            # Для прораба - только его рабочие и его объекты
            if user.role == 'foreman':
                self.fields['assigned_to'].queryset = User.objects.filter(
                    role='worker',
                    worker_profile__foreman=user
                )
                self.fields['construction_site'].queryset = ConstructionSite.objects.filter(
                    foreman=user
                )
            # Для админа - все рабочие и объекты
            elif user.role == 'admin':
                self.fields['assigned_to'].queryset = User.objects.filter(role='worker')
                self.fields['construction_site'].queryset = ConstructionSite.objects.all()
            
            # Для обычных пользователей скрываем поле статуса
            if user.role not in ['admin', 'foreman'] and 'status' in self.fields:
                del self.fields['status']
        
        # Устанавливаем атрибуты для полей
        for field_name, field in self.fields.items():
            if field_name == 'assigned_to':
                field.help_text = 'Удерживайте Ctrl (или Cmd на Mac) для выбора нескольких исполнителей'
                field.required = True
                field.widget.attrs.update({
                    'class': 'form-select',
                    'multiple': 'multiple',
                    'data-placeholder': 'Выберите исполнителей'
                })
            elif field_name == 'deadline':
                field.required = False
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': 'дд.мм.гггг чч:мм',
                    'autocomplete': 'off'
                })
            elif field_name == 'status':
                field.initial = 'new'
                if user and user.role not in ['admin', 'foreman']:
                    field.widget.attrs['disabled'] = 'disabled'
            elif field_name == 'priority':
                field.initial = 'medium'
    
    def clean(self):
        cleaned_data = super().clean()
        # Можно добавить дополнительную валидацию при необходимости
        return cleaned_data


class TaskCommentForm(forms.ModelForm):
    """Форма для добавления комментариев к задаче"""
    class Meta:
        model = TaskComment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Введите текст комментария...',
                'required': 'required'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.task = kwargs.pop('task', None)
        super().__init__(*args, **kwargs)
        self.fields['text'].label = ''
    
    def save(self, commit=True):
        comment = super().save(commit=False)
        if self.user:
            comment.author = self.user
        if self.task:
            comment.task = self.task
        if commit:
            comment.save()
        return comment
