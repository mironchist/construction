from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, ConstructionSite, SitePhoto, SiteComment

# Настройка отображения пользовательской модели пользователя
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
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
    fields = ('photo', 'uploaded_by', 'upload_date', 'comment')
    readonly_fields = ('upload_date', 'uploaded_by')

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
    list_display = ('name', 'status', 'progress', 'start_date', 'end_date', 'foreman', 'client')
    list_filter = ('status', 'start_date', 'end_date')
    search_fields = ('name', 'address', 'description')
    list_editable = ('status', 'progress')
    inlines = [SitePhotoInline, SiteCommentInline]
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
    list_display = ('__str__', 'site', 'uploaded_by', 'upload_date')
    list_filter = ('upload_date', 'uploaded_by')
    search_fields = ('site__name', 'comment')
    readonly_fields = ('upload_date',)

@admin.register(SiteComment)
class SiteCommentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'site', 'author', 'created_date')
    list_filter = ('created_date', 'author')
    search_fields = ('site__name', 'text')
    readonly_fields = ('created_date',)
