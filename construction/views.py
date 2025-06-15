import logging
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

# Настройка логгера
logger = logging.getLogger(__name__)

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

def get_objects_for_user(user):
    """
    Возвращает QuerySet объектов ConstructionSite, доступных пользователю
    в зависимости от его роли.
    """
    if user.is_admin:
        return ConstructionSite.objects.all()
    elif user.role == 'foreman':
        return ConstructionSite.objects.filter(foreman=user)
    elif user.role == 'client':
        return ConstructionSite.objects.filter(client=user)
    else:  # worker
        return ConstructionSite.objects.filter(workers=user)

# Список объектов
@login_required
def object_list_view(request):
    """Список объектов строительства с пагинацией"""
    objects_list = get_objects_for_user(request.user).order_by('-start_date')
    
    # Пагинация
    paginator = Paginator(objects_list, 10)
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
    
    # Обновляем прогресс выполнения на основе времени
    obj.save()  # Вызовет пересчет прогресса в методе save() модели
    
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
def _get_users_for_selection():
    """Возвращает словарь с пользователями, сгруппированными по ролям"""
    return {
        'clients': User.objects.filter(role='client'),
        'foremen': User.objects.filter(role='foreman'),
        'workers': User.objects.filter(role='worker')
    }

def _save_construction_site_form(form, request, is_edit=False, obj=None):
    """
    Сохраняет форму ConstructionSiteForm и возвращает результат.
    
    Args:
        form: Экземпляр ConstructionSiteForm
        request: Объект запроса
        is_edit: Флаг редактирования существующего объекта
        obj: Существующий объект (только для редактирования)
    """
    if form.is_valid():
        try:
            site = form.save(commit=False)
            site.save()
            form.save_m2m()  # Сохраняем связи many-to-many (workers)
            
            action = 'изменен' if is_edit else 'создан'
            messages.success(request, f'Объект успешно {action}')
            return True, redirect('object_detail', pk=site.pk)
            
        except Exception as e:
            logger.error(f'Ошибка при сохранении объекта: {str(e)}')
            messages.error(request, f'Произошла ошибка при сохранении: {str(e)}')
    
    return False, None

@login_required
def object_create_view(request):
    """Создание нового объекта строительства"""
    if request.user.role not in ['admin', 'foreman', 'client']:
        messages.error(request, 'У вас нет прав на создание объектов')
        return redirect('objects')
    
    if request.method == 'POST':
        form = ConstructionSiteForm(data=request.POST, user=request.user)
        success, response = _save_construction_site_form(form, request, is_edit=False)
        if success:
            return response
    else:
        form = ConstructionSiteForm(user=request.user)
    
    context = {
        'form': form,
        'title': 'Создание нового объекта',
        **_get_users_for_selection()
    }
    
    return render(request, 'construction/object_form.html', context)

@login_required
def object_edit_view(request, pk):
    """Редактирование существующего объекта строительства"""
    obj = get_object_or_404(ConstructionSite, pk=pk)
    
    # Проверка прав доступа
    if not (request.user.is_admin or 
            obj.foreman == request.user or 
            obj.client == request.user):
        messages.error(request, 'У вас нет прав на редактирование этого объекта')
        return redirect('object_detail', pk=pk)
    
    if request.method == 'POST':
        form = ConstructionSiteForm(data=request.POST, instance=obj, user=request.user)
        success, response = _save_construction_site_form(form, request, is_edit=True, obj=obj)
        if success:
            return response
    else:
        form = ConstructionSiteForm(instance=obj, user=request.user)
    
    context = {
        'form': form,
        'object': obj,
        'title': 'Редактирование объекта',
        'user': request.user,  # Добавляем пользователя в контекст
        **_get_users_for_selection()
    }
    
    return render(request, 'construction/object_form.html', context)

def _check_photo_permissions(user, obj):
    """
    Проверяет, имеет ли пользователь права на управление фотографиями объекта.
    
    Args:
        user: Пользователь, совершающий действие
        obj: Объект ConstructionSite
        
    Returns:
        bool: True если есть права, иначе False
    """
    return (
        user.is_admin or 
        user.role == 'foreman' or 
        obj.client == user or 
        user in obj.workers.all()
    )

# Управление фотографиями
@login_required
def add_photo_view(request, pk):
    """Добавление фотографии к объекту строительства"""
    obj = get_object_or_404(ConstructionSite, pk=pk)
    
    # Проверка прав доступа
    if not _check_photo_permissions(request.user, obj):
        messages.error(request, 'У вас нет прав на добавление фотографий')
        return redirect('object_detail', pk=pk)
    
    if request.method == 'POST':
        form = SitePhotoForm(request.POST, request.FILES, exclude_fields=[])
        if form.is_valid():
            try:
                photo = form.save(commit=False)
                photo.site = obj
                photo.uploaded_by = request.user
                photo.save()
                messages.success(request, 'Фотография успешно добавлена')
                return redirect('object_detail', pk=obj.pk)
                
            except Exception as e:
                logger.error(f'Ошибка при добавлении фотографии: {str(e)}')
                messages.error(
                    request, 
                    'Произошла ошибка при загрузке фотографии. Пожалуйста, попробуйте снова.'
                )
    else:
        form = SitePhotoForm(exclude_fields=[])
    
    return render(request, 'construction/add_photo.html', {
        'form': form,
        'object': obj,
        'title': 'Добавление фотографии'
    })



# Домашняя страница
@login_required
def home_view(request):
    """Домашняя страница с последними объектами пользователя"""
    # Получаем последние 5 объектов пользователя, отсортированные по дате начала
    recent_objects = get_objects_for_user(request.user).order_by('-start_date')[:5]
    
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
    if not (request.user.is_admin or 
            obj.foreman == request.user or 
            obj.client == request.user or
            (request.user.role == 'foreman' and obj.foreman == request.user)):
        messages.error(request, 'У вас нет прав на изменение статуса этого объекта')
        return redirect('object_detail', pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        new_progress = request.POST.get('progress', 0)
        
        # Проверяем, что переданный статус допустим
        if new_status and new_status in dict(ConstructionSite.STATUS_CHOICES):
            obj.status = new_status
            
        # Обрабатываем прогресс
        try:
            progress = int(new_progress)
            if 0 <= progress <= 100:
                obj.progress = progress
            else:
                messages.warning(request, 'Прогресс должен быть числом от 0 до 100')
        except (ValueError, TypeError):
            messages.warning(request, 'Некорректное значение прогресса')
        
        try:
            obj.save(update_fields=['status', 'progress', 'updated_at'])
            messages.success(request, 'Статус объекта обновлен')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении статуса: {str(e)}')
    
    return redirect('object_detail', pk=obj.pk)

@login_required
def edit_photo_view(request, pk):
    """
    Редактирование описания фотографии.
    
    Разрешается редактировать только описание. Для изменения самой фотографии 
    нужно удалить старую и загрузить новую.
    """
    photo = get_object_or_404(SitePhoto, pk=pk)
    obj = photo.site
    
    # Проверка прав доступа
    if not (request.user.is_admin or 
            request.user.role == 'foreman' or 
            photo.site.client == request.user or 
            photo.uploaded_by == request.user):
        messages.error(request, 'У вас нет прав на редактирование этой фотографии')
        return redirect('object_detail', pk=obj.pk)
    
    if request.method == 'POST':
        # Разрешаем изменять только описание, а не саму фотографию
        form = SitePhotoForm(
            request.POST, 
            request.FILES,
            instance=photo, 
            # Исключаем поле изображения из формы при редактировании
            exclude_fields=['photo']
        )
        
        if form.is_valid():
            try:
                # Сохраняем данные, но не коммитим в БД
                photo = form.save(commit=False)
                # Убедимся, что загруженный пользователь не меняется
                photo.uploaded_by = photo.uploaded_by or request.user
                photo.save()
                
                messages.success(request, 'Описание фотографии обновлено')
                return redirect('object_detail', pk=obj.pk)
                
            except Exception as e:
                logger.error(f'Ошибка при обновлении фотографии: {str(e)}', exc_info=True)
                messages.error(
                    request, 
                    'Произошла ошибка при обновлении фотографии. Пожалуйста, попробуйте снова.'
                )
    else:
        # Инициализируем форму без возможности изменения изображения
        form = SitePhotoForm(instance=photo, exclude_fields=['photo'])
    
    return render(request, 'construction/photo_form.html', {
        'form': form,
        'object': obj,
        'photo': photo,
        'title': 'Редактирование фотографии',
        'allow_image_change': False  # Флаг для отключения загрузки изображения в шаблоне
    })

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
    """
    Обновление роли пользователя через AJAX.
    
    Только администратор может изменять роли пользователей.
    Нельзя изменить роль другого администратора.
    """
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
        
        # Проверяем, не пытаемся ли изменить свою собственную роль
        if user == request.user and request.POST.get('role') != 'admin':
            return JsonResponse(
                {'success': False, 'error': 'Вы не можете изменить свою собственную роль'}, 
                status=403
            )
            
        form = UserRoleForm(request.POST, instance=user)
        
        if form.is_valid():
            try:
                form.save()
                return JsonResponse({
                    'success': True, 
                    'message': f'Роль пользователя {user.get_full_name()} успешно обновлена',
                    'new_role_display': user.get_role_display(),
                    'new_role': user.role
                })
            except Exception as e:
                # Логируем ошибку для отладки
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Ошибка при обновлении роли пользователя: {str(e)}')
                
                return JsonResponse(
                    {'success': False, 'error': 'Произошла ошибка при обновлении роли'}, 
                    status=500
                )
        else:
            # Возвращаем первую ошибку валидации
            error = next(iter(form.errors.values()))[0]
            return JsonResponse(
                {'success': False, 'error': error}, 
                status=400
            )
            
    except User.DoesNotExist:
        return JsonResponse(
            {'success': False, 'error': 'Пользователь не найден'}, 
            status=404
        )
    except Exception as e:
        # Логируем неожиданные ошибки
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Неожиданная ошибка в update_user_role_view: {str(e)}')
        
        return JsonResponse(
            {'success': False, 'error': 'Внутренняя ошибка сервера'}, 
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

def _check_comment_permissions(user, obj):
    """
    Проверяет, имеет ли пользователь права на оставление комментариев к объекту.
    
    Args:
        user: Пользователь, совершающий действие
        obj: Объект ConstructionSite
        
    Returns:
        bool: True если есть права, иначе False
    """
    return (
        user.is_admin or 
        obj.foreman == user or 
        obj.client == user or 
        user in obj.workers.all()
    )

@login_required
def api_add_comment(request, pk):
    """API для добавления комментария к объекту"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)
    
    try:
        obj = get_object_or_404(ConstructionSite, pk=pk)
        
        # Проверка прав доступа
        if not _check_comment_permissions(request.user, obj):
            return JsonResponse({'error': 'Доступ запрещен'}, status=403)
        
        form = CommentForm(request.POST)
        if form.is_valid():
            try:
                comment = form.save(commit=False)
                comment.site = obj
                comment.author = request.user
                comment.save()
                
                return JsonResponse({
                    'success': True,
                    'comment': {
                        'id': comment.id,
                        'text': comment.text,
                        'created_date': comment.created_date.strftime('%d.%m.%Y %H:%M'),
                        'author': comment.author.get_full_name() or comment.author.username,
                        'author_id': comment.author.id,  # Добавляем ID автора
                        'can_delete': True  # Пользователь может удалять свои комментарии
                    }
                })
            except Exception as e:
                logger.error(f'Ошибка при сохранении комментария: {str(e)}', exc_info=True)
                return JsonResponse(
                    {'error': 'Произошла ошибка при сохранении комментария'}, 
                    status=500
                )
        
        # Если форма не валидна, возвращаем ошибки валидации
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [str(error) for error in error_list]
            
        return JsonResponse(
            {'error': 'Неверные данные', 'errors': errors}, 
            status=400
        )
        
    except ConstructionSite.DoesNotExist:
        return JsonResponse({'error': 'Объект не найден'}, status=404)
    except Exception as e:
        logger.error(f'Непредвиденная ошибка в api_add_comment: {str(e)}', exc_info=True)
        return JsonResponse(
            {'error': 'Произошла непредвиденная ошибка'}, 
            status=500
        )

@login_required
def api_object_comments(request, pk):
    """API для получения комментариев объекта"""
    obj = get_object_or_404(ConstructionSite, pk=pk)
    
    # Проверка прав доступа
    if not _check_comment_permissions(request.user, obj):
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    comments = [{
        'id': comment.id,
        'text': comment.text,
        'created_date': comment.created_date.strftime('%d.%m.%Y %H:%M'),
        'author': comment.author.get_full_name(),
        'author_id': comment.author.id,  # Добавляем ID автора
        'can_delete': (
            request.user.is_admin or 
            comment.author == request.user or
            obj.foreman == request.user
        )
    } for comment in obj.comments.all().order_by('-created_date')]
    
    return JsonResponse({'comments': comments})

@login_required
@require_http_methods(["POST"])
def delete_comment_view(request, pk):
    """
    Удаление комментария.
    
    Доступно только через POST-запрос для защиты от CSRF и случайного удаления.
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(
            {'error': 'Неверный запрос'}, 
            status=400
        )
    
    comment = get_object_or_404(SiteComment, pk=pk)
    obj = comment.site
    
    # Проверка прав доступа
    can_delete = (
        request.user.is_admin or 
        comment.author == request.user or
        obj.foreman == request.user
    )
    
    if not can_delete:
        return JsonResponse(
            {'error': 'У вас нет прав на удаление этого комментария'}, 
            status=403
        )
    
    try:
        comment_id = comment.id
        comment.delete()
        return JsonResponse({
            'success': True,
            'message': 'Комментарий успешно удален',
            'comment_id': comment_id
        })
        
    except Exception as e:
        logger.error(f'Ошибка при удалении комментария: {str(e)}')
        return JsonResponse(
            {'error': 'Произошла ошибка при удалении комментария'}, 
            status=500
        )
