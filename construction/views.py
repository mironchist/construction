from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from .models import User, ConstructionSite, SitePhoto, SiteComment
from .forms import UserRegistrationForm, UserEditForm, ConstructionSiteForm, SitePhotoForm, CommentForm, UserRoleForm

# Аутентификация
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.get_full_name()}!')
            return redirect('home')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
            
    return render(request, 'construction/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы')
    return redirect('login')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Сохраняем пользователя с ролью 'worker' по умолчанию
            user = form.save(commit=False)
            user.role = 'worker'  # Устанавливаем роль по умолчанию
            user.save()
            
            # Сохраняем группы, если они есть
            if hasattr(form, 'save_m2m'):
                form.save_m2m()
                
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно! Вам автоматически назначена роль рабочего.')
            return redirect('home')
    else:
        form = UserRegistrationForm()
        
    return render(request, 'construction/register.html', {'form': form})

# Профиль пользователя
@login_required
def profile_view(request):
    form = UserEditForm(instance=request.user)
    return render(request, 'construction/profile.html', {'form': form})

@login_required
def profile_update_view(request):
    if request.method == 'POST':
        form = UserEditForm(instance=request.user, data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен')
            return redirect('profile')
    else:
        return redirect('profile')
    
    # Если форма не валидна, показываем страницу с ошибками
    return render(request, 'construction/profile.html', {'form': form})

@login_required
def admin_profile_update_view(request, user_id):
    """Редактирование профиля пользователя администратором"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет прав для выполнения этого действия')
        return redirect('home')
    
    user_to_edit = get_object_or_404(User, id=user_id)
    
    # Проверяем, не пытаемся ли редактировать другого администратора
    if user_to_edit.role == 'admin' and user_to_edit != request.user:
        messages.error(request, 'Нельзя редактировать профиль другого администратора')
        return redirect('user_list')
    
    if request.method == 'POST':
        form = UserEditForm(instance=user_to_edit, data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, f'Профиль пользователя {user_to_edit.get_full_name()} успешно обновлен')
            return redirect('user_list')
    else:
        form = UserEditForm(instance=user_to_edit)
    
    return render(request, 'construction/admin_profile_update.html', {
        'form': form,
        'user_to_edit': user_to_edit
    })

@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменен')
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
        
    return render(request, 'construction/change_password.html', {'form': form})

# Список объектов
@login_required
def object_list_view(request):
    # Фильтрация объектов в зависимости от роли пользователя
    if request.user.role == 'admin':
        objects_list = ConstructionSite.objects.all()
    elif request.user.role == 'foreman':
        objects_list = ConstructionSite.objects.filter(foreman=request.user)
    elif request.user.role == 'client':
        objects_list = ConstructionSite.objects.filter(client=request.user)
    else:  # worker
        objects_list = ConstructionSite.objects.filter(workers=request.user)
    
    # Пагинация
    paginator = Paginator(objects_list.order_by('-start_date'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'construction/objects.html', {
        'page_obj': page_obj,
        'object_list': page_obj.object_list,
    })

# Детали объекта
@login_required
def object_detail_view(request, pk):
    obj = get_object_or_404(ConstructionSite, pk=pk)
    
    # Проверка прав доступа
    if not (request.user.role == 'admin' or 
            obj.foreman == request.user or 
            obj.client == request.user or 
            request.user in obj.workers.all()):
        messages.error(request, 'У вас нет доступа к этому объекту')
        return redirect('objects')
    
    # Обработка комментариев
    if request.method == 'POST' and 'comment' in request.POST:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.site = obj
            comment.author = request.user
            comment.save()
            messages.success(request, 'Комментарий добавлен')
            return redirect('object_detail', pk=pk)
    else:
        comment_form = CommentForm()
    
    return render(request, 'construction/object_detail.html', {
        'object': obj,
        'comment_form': comment_form,
    })

# Создание и редактирование объекта
@login_required
def object_create_view(request):
    if request.user.role not in ['admin', 'foreman', 'client']:
        messages.error(request, 'У вас нет прав на создание объектов')
        return redirect('objects')
    
    if request.method == 'POST':
        form = ConstructionSiteForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            if request.user.role == 'client':
                obj.client = request.user
            obj.save()
            form.save_m2m()  # Для сохранения many-to-many полей
            messages.success(request, 'Объект успешно создан')
            return redirect('object_detail', pk=obj.pk)
    else:
        form = ConstructionSiteForm(user=request.user)
    
    return render(request, 'construction/object_form.html', {
        'form': form,
        'title': 'Создание объекта'
    })

@login_required
def object_edit_view(request, pk):
    obj = get_object_or_404(ConstructionSite, pk=pk)
    
    # Проверка прав доступа
    if not (request.user.role == 'admin' or 
            obj.foreman == request.user or 
            obj.client == request.user):
        messages.error(request, 'У вас нет прав на редактирование этого объекта')
        return redirect('object_detail', pk=pk)
    
    if request.method == 'POST':
        form = ConstructionSiteForm(request.user, request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Изменения сохранены')
            return redirect('object_detail', pk=obj.pk)
    else:
        form = ConstructionSiteForm(user=request.user, instance=obj)
    
    return render(request, 'construction/object_form.html', {
        'form': form,
        'object': obj,
        'title': 'Редактирование объекта'
    })

# Управление фотографиями
@login_required
def add_photo_view(request, pk):
    obj = get_object_or_404(ConstructionSite, pk=pk)
    
    # Проверка прав доступа
    if not (request.user.role in ['admin', 'foreman'] or 
            obj.client == request.user or 
            request.user in obj.workers.all()):
        messages.error(request, 'У вас нет прав на добавление фотографий')
        return redirect('object_detail', pk=pk)
    
    if request.method == 'POST':
        form = SitePhotoForm(request.POST, request.FILES)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.site = obj
            photo.uploaded_by = request.user
            photo.save()
            messages.success(request, 'Фотография добавлена')
            return redirect('object_detail', pk=obj.pk)
    else:
        form = SitePhotoForm()
    
    return render(request, 'construction/add_photo.html', {
        'form': form,
        'object': obj,
    })

@login_required
def delete_photo_view(request, pk):
    photo = get_object_or_404(SitePhoto, pk=pk)
    obj = photo.site
    
    # Проверка прав доступа
    if not (request.user.role in ['admin', 'foreman'] or 
            obj.client == request.user or 
            photo.uploaded_by == request.user):
        messages.error(request, 'У вас нет прав на удаление этой фотографии')
        return redirect('object_detail', pk=obj.pk)
    
    if request.method == 'POST':
        photo.delete()
        messages.success(request, 'Фотография удалена')
        return redirect('object_detail', pk=obj.pk)
    
    return render(request, 'construction/confirm_delete.html', {
        'object': photo,
        'back_url': 'object_detail',
        'back_kwargs': {'pk': obj.pk}
    })

# Домашняя страница
@login_required
def home_view(request):
    # Получаем последние объекты пользователя
    if request.user.role == 'admin':
        recent_objects = ConstructionSite.objects.all().order_by('-start_date')[:5]
    elif request.user.role == 'foreman':
        recent_objects = ConstructionSite.objects.filter(foreman=request.user).order_by('-start_date')[:5]
    elif request.user.role == 'client':
        recent_objects = ConstructionSite.objects.filter(client=request.user).order_by('-start_date')[:5]
    else:  # worker
        recent_objects = ConstructionSite.objects.filter(workers=request.user).order_by('-start_date')[:5]
    
    return render(request, 'construction/home.html', {
        'recent_objects': recent_objects,
    })

@login_required
def object_delete_view(request, pk):
    """Удаление объекта строительства"""
    obj = get_object_or_404(ConstructionSite, pk=pk)
    
    # Проверка прав доступа
    if not (request.user.role == 'admin' or 
            obj.foreman == request.user or 
            obj.client == request.user):
        messages.error(request, 'У вас нет прав на удаление этого объекта')
        return redirect('object_detail', pk=pk)
    
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Объект успешно удален')
        return redirect('objects')
    
    return render(request, 'construction/confirm_delete.html', {
        'object': obj,
        'back_url': 'object_detail',
        'back_kwargs': {'pk': obj.pk}
    })

@login_required
def update_object_status_view(request, pk):
    """Обновление статуса объекта"""
    obj = get_object_or_404(ConstructionSite, pk=pk)
    
    # Проверка прав доступа
    if not (request.user.role in ['admin', 'foreman'] or 
            obj.foreman == request.user or 
            obj.client == request.user):
        messages.error(request, 'У вас нет прав на изменение статуса этого объекта')
        return redirect('object_detail', pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        new_progress = request.POST.get('progress', 0)
        
        if new_status in dict(ConstructionSite.STATUS_CHOICES).keys():
            obj.status = new_status
            
        try:
            progress = int(new_progress)
            if 0 <= progress <= 100:
                obj.progress = progress
        except (ValueError, TypeError):
            pass
            
        obj.save()
        messages.success(request, 'Статус объекта обновлен')
    
    return redirect('object_detail', pk=obj.pk)

@login_required
def edit_photo_view(request, pk):
    """Редактирование фотографии"""
    photo = get_object_or_404(SitePhoto, pk=pk)
    obj = photo.site
    
    # Проверка прав доступа
    if not (request.user.role in ['admin', 'foreman'] or 
            obj.client == request.user or 
            photo.uploaded_by == request.user):
        messages.error(request, 'У вас нет прав на редактирование этой фотографии')
        return redirect('object_detail', pk=obj.pk)
    
    if request.method == 'POST':
        form = SitePhotoForm(request.POST, instance=photo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Изменения сохранены')
            return redirect('object_detail', pk=obj.pk)
    else:
        form = SitePhotoForm(instance=photo)
    
    return render(request, 'construction/photo_form.html', {
        'form': form,
        'object': obj,
        'photo': photo,
        'title': 'Редактирование фотографии'
    })

@login_required
def add_comment_view(request, pk):
    """Добавление комментария к объекту"""
    obj = get_object_or_404(ConstructionSite, pk=pk)
    
    # Проверка прав доступа
    if not (request.user.role in ['admin', 'foreman'] or 
            obj.foreman == request.user or 
            obj.client == request.user or
            request.user in obj.workers.all()):
        messages.error(request, 'У вас нет прав на добавление комментариев к этому объекту')
        return redirect('object_detail', pk=pk)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.site = obj
            comment.author = request.user
            comment.save()
            messages.success(request, 'Комментарий успешно добавлен')
            return redirect('object_detail', pk=pk)
    else:
        form = CommentForm()
    
    # Если форма не валидна, вернем пользователя на страницу объекта с формой
    return redirect('object_detail', pk=pk)

# Управление пользователями
@login_required
def user_list_view(request):
    """Список пользователей для администратора (исключая других администраторов)"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет прав для просмотра этой страницы')
        return redirect('home')
    
    # Получаем всех пользователей, кроме администраторов
    users = User.objects.exclude(role='admin').order_by('-date_joined')
    return render(request, 'construction/user_list.html', {'users': users})

@login_required
@require_http_methods(["POST"])
def update_user_role_view(request, user_id):
    """Обновление роли пользователя через AJAX"""
    if not request.user.is_admin:
        return JsonResponse(
            {'success': False, 'error': 'У вас нет прав для выполнения этого действия'}, 
            status=403
        )
    
    try:
        user = User.objects.get(id=user_id)
        
        # Проверяем, не пытаемся ли изменить роль другого администратора
        if user.role == 'admin' and user != request.user:
            return JsonResponse(
                {'success': False, 'error': 'Нельзя изменить роль другого администратора'}, 
                status=403
            )
            
        form = UserRoleForm(request.POST, instance=user)
        
        if form.is_valid():
            form.save()
            return JsonResponse({
                'success': True, 
                'message': f'Роль пользователя {user.get_full_name()} успешно обновлена',
                'new_role_display': user.get_role_display()
            })
        else:
            return JsonResponse(
                {'success': False, 'error': 'Неверные данные формы'}, 
                status=400
            )
            
    except User.DoesNotExist:
        return JsonResponse(
            {'success': False, 'error': 'Пользователь не найден'}, 
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'error': str(e)}, 
            status=500
        )

# API представления
@login_required
def api_object_photos(request, pk):
    """API для получения фотографий объекта"""
    obj = get_object_or_404(ConstructionSite, pk=pk)
    
    # Проверка прав доступа
    if not (request.user.role == 'admin' or 
            obj.foreman == request.user or 
            obj.client == request.user or 
            request.user in obj.workers.all()):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    photos = [{
        'id': photo.id,
        'url': request.build_absolute_uri(photo.photo.url),
        'comment': photo.comment,
        'upload_date': photo.upload_date.strftime('%d.%m.%Y %H:%M'),
        'uploaded_by': photo.uploaded_by.get_full_name()
    } for photo in obj.photos.all()]
    
    return JsonResponse({'photos': photos})

@login_required
def api_object_comments(request, pk):
    """API для получения комментариев объекта"""
    obj = get_object_or_404(ConstructionSite, pk=pk)
    
    # Проверка прав доступа
    if not (request.user.role == 'admin' or 
            obj.foreman == request.user or 
            obj.client == request.user or 
            request.user in obj.workers.all()):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    comments = [{
        'id': comment.id,
        'text': comment.text,
        'created_date': comment.created_date.strftime('%d.%m.%Y %H:%M'),
        'author': comment.author.get_full_name()
    } for comment in obj.comments.all().order_by('-created_date')]
    
    return JsonResponse({'comments': comments})

@login_required
def delete_photo_view(request, pk):
    """Удаление фотографии объекта"""
    photo = get_object_or_404(SitePhoto, pk=pk)
    obj = photo.site
    
    # Проверка прав доступа
    if not (request.user.role in ['admin', 'foreman'] or 
            obj.client == request.user or 
            photo.uploaded_by == request.user):
        messages.error(request, 'У вас нет прав на удаление этой фотографии')
        return redirect('object_detail', pk=obj.pk)
    
    if request.method == 'POST':
        photo.delete()
        messages.success(request, 'Фотография успешно удалена')
        return redirect('object_detail', pk=obj.pk)
    
    return render(request, 'construction/confirm_delete.html', {
        'object': obj,
        'photo': photo,
        'back_url': 'object_detail',
        'back_kwargs': {'pk': obj.pk},
        'title': 'Удаление фотографии',
        'message': 'Вы уверены, что хотите удалить эту фотографию? Это действие нельзя отменить.'
    })
