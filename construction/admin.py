from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import User, ConstructionSite, SitePhoto, SiteComment, Task

# Настройка отображения пользовательской модели пользователя
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_colored_role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    
    class Media:
        js = ('admin/js/update_role_display.js',)
    
    def get_colored_role(self, obj):
        role = obj.get_role_display()
        colors = {
            'admin': '#dc3545',    # красный
            'foreman': '#0d6efd',  # синий
            'client': '#198754',   # зеленый
            'worker': '#6c757d',   # серый
        }
        color = colors.get(obj.role, '#000000')  # черный по умолчанию
        return format_html(
            '<span class="role-badge-display" data-role="{}" style="background-color: {}; color: white; font-weight: bold; '
            'padding: 2px 8px; border-radius: 12px; display: inline-block; min-width: 80px; text-align: center;">{}</span>',
            obj.role, color, role
        )
    get_colored_role.short_description = 'Роль'
    get_colored_role.allow_tags = True
    get_colored_role.admin_order_field = 'role'
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        (_('Permissions'), {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role'),
        }),
    )

# Настройка отображения строительных объектов
class SitePhotoInline(admin.TabularInline):
    model = SitePhoto
    extra = 1
    fields = ('photo_preview', 'photo', 'uploaded_by', 'upload_date', 'comment')
    readonly_fields = ('photo_preview', 'upload_date', 'uploaded_by')
    
    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="max-height: 100px;" />', obj.photo.url)
        return "Нет фото"
    photo_preview.short_description = 'Предпросмотр'

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

class SiteCommentInline(admin.TabularInline):
    model = SiteComment
    extra = 1
    fields = ('author', 'text', 'created_date')
    readonly_fields = ('created_date',)

@admin.register(ConstructionSite)
class ConstructionSiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'progress_bar', 'start_date', 'end_date', 'foreman', 'client')
    list_filter = ('status', 'start_date', 'end_date', 'foreman', 'client')
    search_fields = ('name', 'address', 'description', 'foreman__username', 'client__username')
    list_editable = ('status',)
    inlines = [SitePhotoInline, SiteCommentInline]
    
    def progress_bar(self, obj):
        return format_html(
            '<div class="progress" style="width:100px">'
            '<div class="progress-bar" role="progressbar" style="width: {}%" '
            'aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100">{}%</div>'
            '</div>',
            obj.progress, obj.progress, obj.progress
        )
    progress_bar.short_description = 'Прогресс'
    progress_bar.admin_order_field = 'progress'
    fieldsets = (
        (None, {
            'fields': ('name', 'address', 'description')
        }),
        ('Даты', {
            'fields': (('start_date', 'end_date'),)
        }),
        ('Статус', {
            'fields': (('status', 'progress'),)
        }),
        ('Участники', {
            'fields': ('foreman', 'client', 'workers')
        }),
    )
    filter_horizontal = ('workers',)

# Регистрация оставшихся моделей
@admin.register(SitePhoto)
class SitePhotoAdmin(admin.ModelAdmin):
    list_display = ('photo_preview', 'site_link', 'uploaded_by', 'upload_date')
    list_filter = ('upload_date', 'uploaded_by', 'site__status')
    search_fields = ('site__name', 'comment', 'uploaded_by__username')
    readonly_fields = ('upload_date', 'photo_preview')
    list_select_related = ('site', 'uploaded_by')
    
    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="max-height: 100px;" />', obj.photo.url)
        return "Нет фото"
    photo_preview.short_description = 'Фото'
    
    def site_link(self, obj):
        url = f'/admin/construction/constructionsite/{obj.site.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.site.name)
    site_link.short_description = 'Объект'
    site_link.admin_order_field = 'site__name'

@admin.register(SiteComment)
class SiteCommentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'site', 'author', 'created_date')
    list_filter = ('created_date', 'author')
    search_fields = ('site__name', 'text')
    readonly_fields = ('created_date',)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'created_by', 'deadline', 'get_assigned_to', 'construction_site', 'created_at')
    list_filter = ('status', 'created_at', 'deadline', 'created_by')
    search_fields = ('title', 'description', 'created_by__username', 'assigned_to__username', 'construction_site__name')
    list_editable = ('status',)
    filter_horizontal = ('assigned_to',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'status')
        }),
        ('Детали', {
            'fields': (('created_by', 'assigned_to'), 'construction_site', 'deadline')
        }),
        ('Даты', {
            'fields': (('created_at', 'updated_at'),),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_assigned_to(self, obj):
        return ", ".join([user.get_full_name() or user.username for user in obj.assigned_to.all()])
    get_assigned_to.short_description = 'Исполнители'
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Если объект создается, а не обновляется
            obj.created_by = request.user
        obj.save()
