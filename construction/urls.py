from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.decorators.http import require_http_methods
from . import views

# app_name = 'construction'  # Удаляем пространство имен

urlpatterns = [
    # Аутентификация
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    
    # Профиль пользователя
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update_view, name='profile_update'),
    path('profile/update/<int:user_id>/', views.admin_profile_update_view, name='admin_profile_update'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    
    # Сброс пароля
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset.html',
             email_template_name='registration/password_reset_email.html',
             subject_template_name='registration/password_reset_subject.txt'
         ), 
         name='password_reset'),
    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    # Объекты строительства
    path('objects/', views.object_list_view, name='objects'),
    path('objects/create/', views.object_create_view, name='object_create'),
    path('objects/<int:pk>/', views.object_detail_view, name='object_detail'),
    path('objects/<int:pk>/edit/', views.object_edit_view, name='object_edit'),
    path('objects/<int:pk>/delete/', views.object_delete_view, name='object_delete'),
    path('objects/<int:pk>/update-status/', views.update_object_status_view, name='update_object_status'),
    
    # Фотографии объектов
    path('objects/<int:pk>/add-photo/', views.add_photo_view, name='add_photo'),
    
    # Комментарии объектов
    path('photos/<int:pk>/edit/', views.edit_photo_view, name='edit_photo'),
    
    # API для AJAX запросов
    path('api/objects/<int:pk>/photos/', views.api_object_photos, name='api_object_photos'),
    path('api/photos/<int:pk>/delete/', views.api_delete_photo, name='api_delete_photo'),
    path('api/objects/<int:pk>/comments/', views.api_object_comments, name='api_object_comments'),
    path('api/objects/<int:pk>/comments/add/', views.api_add_comment, name='api_add_comment'),
    path('api/comments/<int:pk>/delete/', views.delete_comment_view, name='api_delete_comment'),
    
    # Управление пользователями
    path('users/', views.user_list_view, name='user_list'),
    path('users/<int:user_id>/update-role/', 
         require_http_methods(['POST'])(views.update_user_role_view), 
         name='update_user_role'),
]
