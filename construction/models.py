from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

# Кастомная модель пользователя с ролями
class User(AbstractUser):
    ROLE_CHOICES = [
        ('worker', 'Рабочий'),
        ('foreman', 'Прораб'),
        ('client', 'Заказчик'),
        ('admin', 'Администратор'),
    ]
    
    role = models.CharField('Роль', max_length=10, choices=ROLE_CHOICES, default='worker')
    phone = models.CharField('Телефон', max_length=20, blank=True, null=True)
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

# Модель строительного объекта
class ConstructionSite(models.Model):
    STATUS_CHOICES = [
        ('planning', 'Планирование'),
        ('in_progress', 'В процессе'),
        ('on_hold', 'На паузе'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]
    
    name = models.CharField('Название объекта', max_length=200)
    address = models.TextField('Адрес объекта')
    start_date = models.DateField('Дата начала работ', default=timezone.now)
    end_date = models.DateField('Планируемая дата окончания', null=True, blank=True)
    description = models.TextField('Описание объекта', blank=True, null=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='planning')
    progress = models.PositiveSmallIntegerField('Прогресс', default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    foreman = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sites_managed', verbose_name='Ответственный прораб')
    client = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sites_ordered', verbose_name='Заказчик')
    workers = models.ManyToManyField(User, related_name='sites_working', verbose_name='Рабочие', blank=True)
    
    def __str__(self):
        return self.name
        
    def get_status_color(self):
        colors = {
            'planning': 'info',
            'in_progress': 'primary',
            'on_hold': 'warning',
            'completed': 'success',
            'cancelled': 'danger',
        }
        return colors.get(self.status, 'secondary')
    
    class Meta:
        verbose_name = 'Строительный объект'
        verbose_name_plural = 'Строительные объекты'

# Модель для фотографий объекта
class SitePhoto(models.Model):
    site = models.ForeignKey(ConstructionSite, on_delete=models.CASCADE, related_name='photos', verbose_name='Объект')
    photo = models.ImageField('Фотография', upload_to='site_photos/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Добавил')
    upload_date = models.DateTimeField('Дата загрузки', auto_now_add=True)
    comment = models.TextField('Комментарий', blank=True, null=True)
    
    def __str__(self):
        return f"Фото для {self.site.name} от {self.upload_date.strftime('%d.%m.%Y')}"
    
    class Meta:
        verbose_name = 'Фотография объекта'
        verbose_name_plural = 'Фотографии объектов'

# Модель для комментариев к объекту
class SiteComment(models.Model):
    site = models.ForeignKey(ConstructionSite, on_delete=models.CASCADE, related_name='comments', verbose_name='Объект')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Автор')
    text = models.TextField('Текст комментария')
    created_date = models.DateTimeField('Дата создания', auto_now_add=True)
    
    def __str__(self):
        return f"Комментарий от {self.author} к {self.site.name}"
    
    class Meta:
        verbose_name = 'Комментарий к объекту'
        verbose_name_plural = 'Комментарии к объектам'
        ordering = ['-created_date']
