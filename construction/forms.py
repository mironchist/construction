from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from .models import ConstructionSite, SitePhoto, SiteComment

User = get_user_model()

class UserRegistrationForm(UserCreationForm):
    """Форма регистрации пользователя"""
    ROLE_CHOICES = [
        ('worker', 'Рабочий'),
        ('foreman', 'Прораб'),
        ('client', 'Заказчик'),
    ]
    
    first_name = forms.CharField(label='Имя', max_length=30, required=True)
    last_name = forms.CharField(label='Фамилия', max_length=30, required=True)
    email = forms.EmailField(label='Email', required=True)
    phone = forms.CharField(label='Телефон', max_length=20, required=True)
    role = forms.ChoiceField(label='Роль', choices=ROLE_CHOICES, required=True)
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'role', 'password1', 'password2')
    
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
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone')
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
    class Meta:
        model = ConstructionSite
        fields = ('name', 'address', 'start_date', 'end_date', 'description', 'client', 'foreman', 'workers')
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'workers': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }
        labels = {
            'name': 'Название объекта',
            'address': 'Адрес',
            'start_date': 'Дата начала работ',
            'end_date': 'Планируемая дата окончания',
            'description': 'Описание',
            'client': 'Заказчик',
            'foreman': 'Ответственный прораб',
            'workers': 'Рабочие',
        }
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Добавляем классы для стилизации полей
        for field_name, field in self.fields.items():
            if field_name not in ['workers']:  # Для workers будем использовать Select2
                field.widget.attrs['class'] = 'form-control'
            if field_name in ['start_date', 'end_date']:
                field.widget.attrs['placeholder'] = 'гггг-мм-дд'
        
        # Настройка полей в зависимости от роли пользователя
        if user.role == 'client':
            # Клиент может выбрать только прораба и рабочих
            self.fields['foreman'].queryset = User.objects.filter(role='foreman')
            self.fields['workers'].queryset = User.objects.filter(role='worker')
            del self.fields['client']  # Удаляем поле клиента, т.к. это сам пользователь
            
            # Добавляем классы для Select2
            self.fields['foreman'].widget.attrs['class'] = 'form-select select2'
            self.fields['workers'].widget.attrs['class'] = 'form-select select2'
            
        elif user.role == 'foreman':
            # Прораб может выбрать только клиентов и рабочих
            self.fields['client'].queryset = User.objects.filter(role='client')
            self.fields['workers'].queryset = User.objects.filter(role='worker')
            
            # Добавляем классы для Select2
            self.fields['client'].widget.attrs['class'] = 'form-select select2'
            self.fields['workers'].widget.attrs['class'] = 'form-select select2'
            
        elif user.role == 'admin':
            # Админ может выбрать всех
            self.fields['client'].queryset = User.objects.filter(role='client')
            self.fields['foreman'].queryset = User.objects.filter(role='foreman')
            self.fields['workers'].queryset = User.objects.filter(role='worker')
            
            # Добавляем классы для Select2
            self.fields['client'].widget.attrs['class'] = 'form-select select2'
            self.fields['foreman'].widget.attrs['class'] = 'form-select select2'
            self.fields['workers'].widget.attrs['class'] = 'form-select select2'
        
        # Добавляем классы Bootstrap для стилизации
        for field_name, field in self.fields.items():
            if field_name != 'workers':
                field.widget.attrs['class'] = 'form-control'
    
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
        fields = ('photo', 'comment')
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Необязательный комментарий к фото'}),
        }
        labels = {
            'photo': 'Фотография',
            'comment': 'Комментарий',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['photo'].widget.attrs.update({'class': 'form-control'})
        self.fields['comment'].widget.attrs.update({'class': 'form-control'})
    
    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            # Проверка размера файла (максимум 10 МБ)
            if photo.size > 10 * 1024 * 1024:
                raise forms.ValidationError('Размер файла не должен превышать 10 МБ')
            
            # Проверка типа файла
            content_type = photo.content_type.split('/')[0]
            if content_type not in ['image']:
                raise forms.ValidationError('Файл должен быть изображением')
        
        return photo

class CommentForm(forms.ModelForm):
    """Форма для добавления комментариев к объекту"""
    class Meta:
        model = SiteComment
        fields = ('text',)
        widgets = {
            'text': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Введите ваш комментарий...'
            }),
        }
        labels = {
            'text': 'Комментарий',
        }
