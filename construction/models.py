from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

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
        
    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser or self.is_staff

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
    address = models.CharField('Адрес объекта', max_length=255)
    start_date = models.DateField('Дата начала работ', default=timezone.now)
    end_date = models.DateField('Планируемая дата окончания', null=True, blank=True)
    description = models.TextField('Описание объекта', blank=True, null=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='planning')
    progress = models.PositiveSmallIntegerField('Прогресс', default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    foreman = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sites_managed', verbose_name='Ответственный прораб')
    client = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sites_ordered', verbose_name='Заказчик')
    workers = models.ManyToManyField(User, related_name='sites_working', verbose_name='Рабочие', blank=True, null=True)
    
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
        
    def calculate_progress_by_time(self):
        """
        Рассчитывает процент выполнения на основе времени.
        Возвращает значение от 0 до 100.
        """
        from django.utils import timezone
        
        # Если объект еще не начат или отменен, возвращаем 0
        if self.status in ['planning', 'cancelled']:
            return 0
            
        # Если объект завершен, возвращаем 100
        if self.status == 'completed':
            return 100
            
        now = timezone.now().date()
        
        # Если дата окончания не указана, возвращаем 0
        if not self.end_date:
            return 0
            
        # Если текущая дата раньше даты начала, возвращаем 0
        if now < self.start_date:
            return 0
            
        # Если текущая дата позже даты окончания, возвращаем 100
        if now >= self.end_date:
            return 100
            
        # Рассчитываем процент выполнения
        total_days = (self.end_date - self.start_date).days
        if total_days <= 0:
            return 100
            
        days_passed = (now - self.start_date).days
        progress = min(100, max(0, int((days_passed / total_days) * 100)))
        
        return progress
        
    def save(self, *args, **kwargs):
        # Если объект завершен, устанавливаем прогресс 100%
        if self.status == 'completed':
            self.progress = 100
        # Если объект отменен или в планировании, сбрасываем прогресс
        elif self.status in ['cancelled', 'planning']:
            self.progress = 0
        # В остальных случаях рассчитываем прогресс по времени
        else:
            self.progress = self.calculate_progress_by_time()
            
        super().save(*args, **kwargs)
    
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
        return f"Комментарий от {self.author.username} к объекту {self.site.name}"
    
    class Meta:
        verbose_name = 'Комментарий к объекту'
        verbose_name_plural = 'Комментарии к объектам'
        ordering = ['-created_date']

# Модель для задач
class Task(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('in_progress', 'В работе'),
        ('completed', 'Выполнена'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
    ]
    
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_tasks',
        verbose_name='Постановщик'
    )
    assigned_to = models.ManyToManyField(
        User, 
        related_name='assigned_tasks',
        verbose_name='Исполнители'
    )
    construction_site = models.ForeignKey(
        'ConstructionSite',
        on_delete=models.CASCADE,
        verbose_name='Строительный объект',
        related_name='tasks',
        null=True,
        blank=True
    )
    deadline = models.DateTimeField('Срок выполнения', null=True, blank=True)
    status = models.CharField(
        'Статус', 
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='new'
    )
    priority = models.CharField(
        'Приоритет',
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text='Приоритет выполнения задачи'
    )
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['-created_at']
        
    @property
    def is_overdue(self):
        """Проверяет, просрочена ли задача"""
        if self.deadline and self.status != 'completed':
            from django.utils import timezone
            return self.deadline < timezone.now()
            
    def get_status_color(self):
        """Возвращает цвет для отображения статуса"""
        colors = {
            'new': 'secondary',
            'in_progress': 'primary',
            'completed': 'success',
            'cancelled': 'danger'
        }
        return colors.get(self.status, 'secondary')
        
    def get_priority_color(self):
        """Возвращает цвет для отображения приоритета"""
        colors = {
            'low': 'info',
            'medium': 'warning',
            'high': 'danger'
        }
        return colors.get(self.priority, 'secondary')
        
    def get_status_display_with_color(self):
        """Возвращает статус с HTML-разметкой для цвета"""
        from django.utils.html import format_html
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            self.get_status_color(),
            self.get_status_display()
        )
        
    def get_priority_display_with_color(self):
        """Возвращает приоритет с HTML-разметкой для цвета"""
        return f'<span class="badge bg-{self.get_priority_color()}">{self.get_priority_display()}</span>'
        
    def get_absolute_url(self):
        """Возвращает URL для детального просмотра задачи"""
        from django.urls import reverse
        try:
            return reverse('task_detail', kwargs={'pk': self.pk})
        except Exception as e:
            # Логируем ошибку, но не падаем
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating URL for task {self.pk}: {str(e)}")
            return f'/tasks/{self.pk}/'


class TaskComment(models.Model):
    """
    Модель для комментариев к задачам.
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Задача'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='task_comments'
    )
    text = models.TextField('Текст комментария')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Комментарий к задаче'
        verbose_name_plural = 'Комментарии к задачам'
        ordering = ['-created_at']

    def __str__(self):
        return f'Комментарий {self.id} к задаче {self.task.id} от {self.author}'
    
    def can_edit(self, user):
        """Проверяет, может ли пользователь редактировать комментарий"""
        return user == self.author or user.is_staff
    
    def can_delete(self, user):
        """Проверяет, может ли пользователь удалить комментарий"""
        return user == self.author or user.is_staff
