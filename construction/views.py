import json
import logging
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render, redirect, get_object_or_404, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt

from .models import Task, TaskComment, ConstructionSite, SiteComment, SitePhoto, User
from .forms import TaskForm, TaskCommentForm, ConstructionSiteForm, SitePhotoForm, CommentForm, UserRegistrationForm, UserEditForm

# Настройка логгера
import logging
logger = logging.getLogger(__name__)
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template.loader import render_to_string
from .models import User, ConstructionSite, SitePhoto, SiteComment, Task
from .forms import (UserRegistrationForm, UserEditForm, 
                   ConstructionSiteForm, SitePhotoForm, 
                   CommentForm, TaskForm)
# Настройка логгера
logger = logging.getLogger(__name__)

@login_required
def task_list_view(request):
    """
    Представление для отображения списка задач.
    """
    # Получаем задачи в зависимости от роли пользователя
    if request.user.is_admin or (hasattr(request.user, 'role') and request.user.role == 'admin'):
        # Администратор видит все задачи
        tasks = Task.objects.all()
    elif hasattr(request.user, 'role') and request.user.role == 'foreman':
        # Прораб видит задачи, которые он создал или которые назначены его рабочим
        tasks = Task.objects.filter(
            Q(created_by=request.user) | 
            Q(assigned_to__worker_profile__foreman=request.user)
        ).distinct()
    elif hasattr(request.user, 'role') and request.user.role == 'worker':
        # Рабочий видит только свои задачи
        tasks = Task.objects.filter(assigned_to=request.user)
    elif hasattr(request.user, 'role') and request.user.role == 'client':
        # Клиент видит задачи по своим объектам
        tasks = Task.objects.filter(
            Q(created_by=request.user) |
            Q(construction_site__client=request.user)
        ).distinct()
    else:
        # По умолчанию показываем только созданные пользователем задачи
        tasks = Task.objects.filter(created_by=request.user)
    
    # Сортировка задач
    sort_by = request.GET.get('sort_by', '-created_at')
    tasks = tasks.order_by(sort_by)
    
    # Пагинация
    paginator = Paginator(tasks, 10)  # Показываем по 10 задач на странице
    page_number = request.GET.get('page')
    
    try:
        tasks = paginator.page(page_number)
    except PageNotAnInteger:
        # Если страница не является целым числом, показываем первую страницу
        tasks = paginator.page(1)
    except EmptyPage:
        # Если номер страницы больше максимального, показываем последнюю страницу
        tasks = paginator.page(paginator.num_pages)
    
    context = {
        'tasks': tasks,
        'sort_by': sort_by,
    }
    
    return render(request, 'construction/task_list.html', context)

@login_required
def task_detail_view(request, pk):
    """
    Представление для просмотра деталей задачи.
    """
    try:
        logger.info(f"Попытка загрузить задачу с ID: {pk}")
        task = get_object_or_404(Task, pk=pk)
        logger.info(f"Задача найдена: {task.title}")
        
        # Проверка прав доступа
        has_access = (
            request.user == task.created_by or 
            request.user in task.assigned_to.all() or 
            request.user.is_admin or 
            (hasattr(request.user, 'role') and request.user.role in ['admin', 'foreman'])
        )
        
        logger.info(f"Пользователь {request.user.username} имеет доступ к задаче: {has_access}")
        
        if not has_access:
            messages.error(request, 'У вас нет прав для просмотра этой задачи.')
            logger.warning(f"Попытка доступа к задаче {pk} пользователем {request.user.username} без прав")
            return redirect('task_list')
        
        context = {
            'task': task,
            'can_edit': request.user == task.created_by or request.user.is_admin or (hasattr(request.user, 'role') and request.user.role == 'foreman'),
            'can_delete': request.user == task.created_by or request.user.is_admin,
        }
        
        logger.info(f"Рендеринг шаблона для задачи {pk}")
        return render(request, 'construction/task_detail.html', context)
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке задачи {pk}: {str(e)}", exc_info=True)
        messages.error(request, 'Произошла ошибка при загрузке задачи')
        return redirect('task_list')

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
            # Сохраняем форму, но не коммитим в БД, чтобы изменить роль
            user = form.save(commit=False)
            
            # Обновляем роль, только если это не текущий пользователь
            # (чтобы не снять самому себе права админа)
            if user != request.user:
                user.role = form.cleaned_data['role']
            
            user.save()
            form.save_m2m()  # Сохраняем связи many-to-many, если они есть
            
            messages.success(request, 'Профиль пользователя успешно обновлен')
            return redirect('user_list')
    else:
        form = UserEditForm(instance=user_to_edit)
        # Устанавливаем начальное значение роли
        form.fields['role'].initial = user_to_edit.role
    
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

@login_required
@require_http_methods(["POST"])
def api_delete_photo(request, pk):
    """
    Удаление фотографии объекта.
    
    Доступно только для администраторов, прорабов и владельцев объекта.
    """
    print(f"\n=== Начало обработки запроса на удаление фотографии {pk} ===")
    print(f"Пользователь: {request.user.id} ({request.user.username})")
    print(f"Метод: {request.method}")
    print(f"Заголовки: {dict(request.headers)}")
    print(f"POST данные: {dict(request.POST)}")
    
    # Проверяем, что это AJAX-запрос
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        print("Ошибка: не AJAX-запрос")
        return JsonResponse(
            {'error': 'Неверный тип запроса'}, 
            status=400
        )
    
    try:
        # Получаем фотографию
        photo = SitePhoto.objects.select_related('site').get(pk=pk)
        print(f"Найдена фотография: {photo}")
        
        # Получаем связанный объект
        obj = photo.site
        print(f"Объект: {obj} (ID: {obj.id})")
        
        # Проверка прав доступа
        can_delete = (
            request.user.role == 'admin' or 
            (hasattr(obj, 'foreman') and obj.foreman == request.user) or
            (hasattr(obj, 'client') and obj.client == request.user)
        )
        
        if not can_delete:
            print("Ошибка: недостаточно прав")
            return JsonResponse(
                {'error': 'У вас нет прав на удаление этой фотографии'}, 
                status=403
            )
        
        # Получаем путь к файлу перед удалением
        photo_path = photo.photo.path if photo.photo else 'неизвестно'
        print(f"Удаление фотографии. Путь к файлу: {photo_path}")
        
        # Удаляем запись из базы данных (файл удалится автоматически)
        photo.delete()
        print("Фотография успешно удалена")
        
        return JsonResponse({
            'success': True,
            'message': 'Фотография успешно удалена',
            'object_id': obj.id
        })
        
    except SitePhoto.DoesNotExist:
        error_msg = f'Фотография с ID {pk} не найдена'
        print(error_msg)
        return JsonResponse(
            {'error': error_msg}, 
            status=404
        )
    except Exception as e:
        error_msg = f'Ошибка при удалении фотографии: {str(e)}'
        print(error_msg)
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {'error': 'Произошла внутренняя ошибка сервера: ' + str(e)}, 
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


# Представления для работы с задачами
@login_required
def task_list_view(request):
    """Список задач с фильтрацией и сортировкой"""
    # Получаем все задачи, к которым имеет доступ пользователь
    tasks = Task.objects.filter(
        Q(created_by=request.user) | Q(assigned_to=request.user)
    ).distinct()
    
    # Фильтрация по статусу, если указан
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        tasks = tasks.filter(status=status_filter)
    
    # Фильтрация по типу (созданные/назначенные)
    task_type = request.GET.get('type')
    if task_type == 'created':
        tasks = tasks.filter(created_by=request.user)
    elif task_type == 'assigned':
        tasks = tasks.filter(assigned_to=request.user).exclude(created_by=request.user)
    
    # Фильтрация по приоритету, если указан
    priority_filter = request.GET.get('priority')
    if priority_filter and priority_filter != 'all':
        tasks = tasks.filter(priority=priority_filter)
    
    # Сортировка
    sort_by = request.GET.get('sort_by', '-created_at')
    valid_sort_fields = ['created_at', 'deadline', 'priority', 'status']
    sort_field = sort_by.lstrip('-')
    
    if sort_field not in valid_sort_fields:
        sort_by = '-created_at'
    
    tasks = tasks.order_by(sort_by, '-created_at')
    
    # Пагинация
    paginator = Paginator(tasks, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Контекст для шаблона
    context = {
        'page_obj': page_obj,
        'tasks': page_obj.object_list,  # Добавляем список задач для итерации в шаблоне
        'status_choices': [('all', 'Все статусы')] + list(Task.STATUS_CHOICES),
        'priority_choices': [('all', 'Любой приоритет')] + list(Task.PRIORITY_CHOICES),
        'current_status': status_filter if status_filter else 'all',
        'current_priority': priority_filter if priority_filter else 'all',
        'current_type': task_type if task_type else 'all',
        'current_sort': sort_by,
        'query_params': request.GET.urlencode()
    }
    return render(request, 'construction/task_list.html', context)


@csrf_exempt
@login_required
def api_update_task_status(request, pk):
    """
    API-эндпоинт для обновления статуса задачи через AJAX.
    
    Принимает POST-запрос с параметром 'status'.
    Возвращает JSON с результатом операции.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Метод не разрешен'}, status=405)
    
    try:
        task = Task.objects.get(pk=pk)
        
        # Проверяем права доступа
        if not (request.user == task.created_by or 
                request.user in task.assigned_to.all() or 
                request.user.is_superuser or 
                request.user.is_admin):
            return JsonResponse(
                {'success': False, 'error': 'У вас нет прав на изменение этой задачи'}, 
                status=403
            )
        
        # Получаем новый статус из запроса
        new_status = request.POST.get('status')
        if not new_status:
            return JsonResponse(
                {'success': False, 'error': 'Не указан новый статус'}, 
                status=400
            )
        
        # Проверяем, что статус допустимый
        if new_status not in dict(Task.STATUS_CHOICES):
            return JsonResponse(
                {'success': False, 'error': 'Недопустимый статус задачи'}, 
                status=400
            )
        
        # Обновляем статус
        task.status = new_status
        task.save()
        
        return JsonResponse({
            'success': True,
            'status_display': task.get_status_display(),
            'status_color': task.get_status_color()
        })
        
    except Task.DoesNotExist:
        return JsonResponse(
            {'success': False, 'error': 'Задача не найдена'}, 
            status=404
        )
    except Exception as e:
        logger.error(f'Ошибка при обновлении статуса задачи: {str(e)}')
        return JsonResponse(
            {'success': False, 'error': 'Внутренняя ошибка сервера'}, 
            status=500
        )


@login_required
def task_detail_view(request, pk):
    """
    Детальный просмотр задачи с возможностью изменения статуса и комментариями.
    
    Разрешен доступ:
    - Создателю задачи
    - Назначенным исполнителям
    - Суперпользователям
    - Администраторам
    """
    print(f"\n=== DEBUG: task_detail_view called with pk={pk} ===")
    print(f"User: {request.user} (ID: {request.user.id if request.user.is_authenticated else 'anon'})")
    
    try:
        task = get_object_or_404(Task, pk=pk)
        print(f"Task found: {task} (created by: {task.created_by}, assigned to: {list(task.assigned_to.all())})")
        
        # Проверка прав доступа
        if not (request.user == task.created_by or 
                request.user in task.assigned_to.all() or 
                request.user.is_superuser or 
                request.user.is_admin):
            messages.error(request, 'У вас нет прав для просмотра этой задачи.')
            return redirect('task_list')
        
        # Обработка изменения статуса
        if request.method == 'POST' and 'status' in request.POST:
            new_status = request.POST.get('status')
            if new_status in dict(Task.STATUS_CHOICES):
                task.status = new_status
                task.save()
                messages.success(request, 'Статус задачи обновлен')
                return redirect('task_detail', pk=task.pk)
            else:
                messages.error(request, 'Недопустимый статус задачи')
        
        # Получаем комментарии к задаче
        comments = task.comments.select_related('author').order_by('created_at')
        
        # Форма для добавления комментария
        comment_form = TaskCommentForm(user=request.user, task=task)
        
        # Определяем, может ли пользователь изменять статус
        can_change_status = (
            request.user in task.assigned_to.all() or 
            request.user == task.created_by or 
            request.user.is_superuser or 
            request.user.is_admin
        )
        
        # Формируем список статусов с цветами и подсказками
        status_choices = [
            {
                'value': 'new',
                'display': 'Новая',
                'color': 'secondary',
                'help_text': 'Задача только создана и ожидает выполнения'
            },
            {
                'value': 'in_progress',
                'display': 'В работе',
                'color': 'primary',
                'help_text': 'Задача в процессе выполнения'
            },
            {
                'value': 'completed',
                'display': 'Завершена',
                'color': 'success',
                'help_text': 'Задача успешно завершена'
            },
            {
                'value': 'cancelled',
                'display': 'Отменена',
                'color': 'danger',
                'help_text': 'Задача отменена и не будет выполняться'
            }
        ]
        
        context = {
            'task': task,
            'comments': comments,
            'comment_form': comment_form,
            'can_edit': request.user == task.created_by or request.user.is_superuser or request.user.is_admin,
            'can_accept': request.user in task.assigned_to.all(),
            'can_change_status': can_change_status,
            'status_choices': status_choices,
            'now': timezone.now(),
            'title': f'Задача: {task.title}'
        }
        return render(request, 'construction/task_detail.html', context)
        
    except Exception as e:
        logger.error(f'Ошибка при просмотре задачи {pk}: {str(e)}', exc_info=True)
        messages.error(request, 'Произошла ошибка при загрузке задачи')
        return redirect('task_list')


@login_required
def add_task_comment(request, task_id):
    """
    Добавление комментария к задаче.
    
    Доступно для:
    - Создателя задачи
    - Назначенных исполнителей
    - Администраторов
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            task = get_object_or_404(Task, pk=task_id)
            
            # Проверка прав доступа
            if not (request.user == task.created_by or 
                    request.user in task.assigned_to.all() or 
                    request.user.is_superuser or 
                    request.user.is_admin):
                return JsonResponse({'success': False, 'error': 'Нет прав для добавления комментария'}, status=403)
            
            form = TaskCommentForm(request.POST, user=request.user, task=task)
            
            if form.is_valid():
                comment = form.save(commit=False)
                comment.author = request.user
                comment.task = task
                comment.save()
                
                # Рендерим новый комментарий в HTML
                comment_html = render_to_string('construction/includes/task_comment.html', {
                    'comment': comment,
                    'user': request.user
                })
                
                return JsonResponse({
                    'success': True,
                    'comment_html': comment_html,
                    'comment_id': comment.id
                })
            else:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
                
        except Exception as e:
            logger.error(f'Ошибка при добавлении комментария к задаче {task_id}: {str(e)}', exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'Ошибка при добавлении комментария'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Неверный запрос'}, status=400)


@login_required
def delete_task_comment(request, comment_id):
    """
    Удаление комментария к задаче.
    
    Доступно для:
    - Автора комментария
    - Создателя задачи
    - Администраторов
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            comment = get_object_or_404(TaskComment, pk=comment_id)
            task = comment.task
            
            # Проверка прав доступа
            if not (request.user == comment.author or 
                    request.user == task.created_by or 
                    request.user.is_superuser or 
                    request.user.is_admin):
                return JsonResponse({'success': False, 'error': 'Нет прав для удаления комментария'}, status=403)
            
            comment_id = comment.id
            comment.delete()
            
            return JsonResponse({
                'success': True,
                'comment_id': comment_id
            })
            
        except Exception as e:
            logger.error(f'Ошибка при удалении комментария {comment_id}: {str(e)}', exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'Ошибка при удалении комментария'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Неверный запрос'}, status=400)


@login_required
def task_create_view(request):
    """
    Создание новой задачи.
    
    Доступно для:
    - Администраторов
    - Прорабов
    """
    # Проверка прав доступа
    if not request.user.is_authenticated or request.user.role not in ['admin', 'foreman']:
        messages.error(request, 'У вас нет прав для создания задач')
        return redirect('home')
    
    # Получаем список доступных исполнителей
    if request.user.role == 'admin':
        available_workers = User.objects.filter(role='worker')
    else:  # foreman
        available_workers = User.objects.filter(
            role='worker',
            worker_profile__foreman=request.user
        )
    
    # Формируем queryset для поля assigned_to
    assigned_to_queryset = available_workers
    
    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        form.fields['assigned_to'].queryset = assigned_to_queryset
        
        if form.is_valid():
            try:
                task = form.save(commit=False)
                task.created_by = request.user
                
                # Устанавливаем статус по умолчанию для новых задач
                if not task.pk:  # Только для новых задач
                    task.status = 'new'
                
                # Сохраняем приоритет
                task.priority = form.cleaned_data.get('priority', 'medium')
                
                # Сохраняем задачу
                task.save()
                
                # Сохраняем many-to-many отношения (исполнителей)
                if 'assigned_to' in form.cleaned_data:
                    task.assigned_to.set(form.cleaned_data['assigned_to'])
                
                # Обновляем объект задачи, чтобы сохранить связи many-to-many
                form.save_m2m()
                
                # Логируем успешное создание задачи
                logger.info(f'Задача успешно создана: {task.title} (ID: {task.id})')
                logger.info(f'Исполнители: {list(task.assigned_to.values_list("username", flat=True))}')
                logger.info(f'Статус: {task.status}, Приоритет: {task.priority}')
                
                messages.success(request, 'Задача успешно создана')
                return redirect('task_detail', pk=task.pk)
                
            except Exception as e:
                logger.error(f'Ошибка при сохранении задачи: {str(e)}')
                logger.exception('Детали ошибки:')
                messages.error(request, f'Произошла ошибка при сохранении задачи: {str(e)}')
        else:
            logger.error(f'Ошибки в форме: {form.errors}')
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        # GET запрос - создаем новую форму
        form = TaskForm(user=request.user)
        form.fields['assigned_to'].queryset = assigned_to_queryset
        # Устанавливаем начальные значения
        form.fields['status'].initial = 'new'
        form.fields['priority'].initial = 'medium'
    
    # Подготавливаем данные о пользователях для Select2
    users_data = []
    for user in assigned_to_queryset:
        avatar_url = ''
        if hasattr(user, 'avatar') and user.avatar:
            try:
                avatar_url = user.avatar.url
            except (ValueError, AttributeError):
                pass
                
        users_data.append({
            'id': user.id,
            'text': json.dumps({
                'full_name': user.get_full_name(),
                'avatar': avatar_url,
                'role_display': user.get_role_display()
            }),
            'selected': False  # По умолчанию никто не выбран при создании новой задачи
        })
    
    # Обновляем поле assigned_to с новыми данными
    form.fields['assigned_to'].choices = [(user['id'], user['text']) for user in users_data]
    
    # Создаем контекст для шаблона
    context = {
        'title': 'Создать задачу',
        'form': form,
        'users_data': json.dumps(users_data, cls=DjangoJSONEncoder)
    }
    return render(request, 'construction/task_form.html', context)


@login_required
def task_edit_view(request, pk):
    """
    Редактирование существующей задачи.
    
    Доступно для:
    - Создателя задачи
    - Администраторов
    - Прорабов (для своих задач и задач подчиненных)
    """
    task = get_object_or_404(Task, pk=pk)
    
    # Проверка прав доступа
    can_edit = (
        task.created_by == request.user or 
        request.user.is_superuser or 
        request.user.role in ['admin'] or
        (request.user.role == 'foreman' and 
         (task.created_by == request.user or 
          task.assigned_to.filter(worker_profile__foreman=request.user).exists()))
    )
    
    if not can_edit:
        messages.error(request, 'У вас нет прав для редактирования этой задачи')
        return redirect('task_detail', pk=task.pk)
    
    # Получаем список доступных исполнителей
    if request.user.role == 'admin':
        available_workers = User.objects.filter(role='worker')
    else:  # foreman
        available_workers = User.objects.filter(
            role='worker',
            worker_profile__foreman=request.user
        )
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, user=request.user)
        form.fields['assigned_to'].queryset = available_workers
        
        # Для существующей задачи сохраняем текущий статус, если пользователь не может его менять
        if request.user.role not in ['admin', 'foreman'] and 'status' in form.fields:
            form.data = form.data.copy()
            form.data['status'] = task.status
            
        if form.is_valid():
            try:
                task = form.save(commit=False)
                task.save()
                
                # Сохраняем many-to-many отношения (исполнителей)
                if 'assigned_to' in form.cleaned_data:
                    task.assigned_to.set(form.cleaned_data['assigned_to'])
                form.save_m2m()
                
                messages.success(request, '✅ Задача успешно обновлена')
                return redirect('task_detail', pk=task.pk)
                
            except Exception as e:
                logger.error(f'Ошибка при обновлении задачи {pk}: {str(e)}', exc_info=True)
                messages.error(request, f'Произошла ошибка при обновлении задачи: {str(e)}')
    else:
        form = TaskForm(instance=task, user=request.user)
        form.fields['assigned_to'].queryset = available_workers
    
    # Подготавливаем данные о пользователях для Select2
    users_data = []
    for user in available_workers:
        avatar_url = ''
        if hasattr(user, 'avatar') and user.avatar:
            try:
                avatar_url = user.avatar.url
            except (ValueError, AttributeError):
                pass
                
        users_data.append({
            'id': user.id,
            'text': json.dumps({
                'full_name': user.get_full_name(),
                'avatar': avatar_url,
                'role_display': user.get_role_display()
            }),
            'selected': task.assigned_to.filter(pk=user.pk).exists()
        })
    
    # Обновляем поле assigned_to с новыми данными
    form.fields['assigned_to'].choices = [(user['id'], user['text']) for user in users_data]
    
    context = {
        'form': form,
        'title': f'Редактирование задачи: {task.title}',
        'task': task,
        'users_data': json.dumps(users_data, cls=DjangoJSONEncoder),
        'submit_btn_text': 'Сохранить изменения',
        'submit_btn_class': 'btn-primary',
        'cancel_url': reverse('task_detail', kwargs={'pk': task.pk})
    }
    return render(request, 'construction/task_form.html', context)


@login_required
def task_delete_view(request, pk):
    """
    Удаление задачи.
    
    Доступно для:
    - Создателя задачи
    - Администраторов
    - Прорабов (только для своих задач и задач своих подчиненных)
    """
    task = get_object_or_404(Task, pk=pk)
    
    # Проверка прав доступа
    can_delete = (
        task.created_by == request.user or 
        request.user.is_superuser or 
        request.user.is_admin or
        (request.user.role == 'foreman' and 
         (task.created_by == request.user or 
          task.assigned_to.filter(worker_profile__foreman=request.user).exists()))
    )
    
    if not can_delete:
        messages.error(request, 'У вас нет прав для удаления этой задачи')
        return redirect('task_detail', pk=task.pk)
    
    if request.method == 'POST':
        try:
            task_title = task.title
            task.delete()
            messages.success(request, f'✅ Задача "{task_title}" успешно удалена')
            return redirect('task_list')
        except Exception as e:
            logger.error(f'Ошибка при удалении задачи {pk}: {str(e)}', exc_info=True)
            messages.error(request, f'Произошла ошибка при удалении задачи: {str(e)}')
            return redirect('task_detail', pk=task.pk)
    
    # Подсчет связанных объектов для предупреждения
    related_objects = []
    
    # Проверяем, есть ли связанные комментарии
    if hasattr(task, 'comments') and task.comments.exists():
        related_objects.append(f'комментарии ({task.comments.count()})')
    
    context = {
        'task': task,
        'related_objects': related_objects,
        'cancel_url': reverse('task_detail', kwargs={'pk': task.pk})
    }
    return render(request, 'construction/task_confirm_delete.html', context)


@login_required
@require_http_methods(['POST'])
def api_update_task_status(request, pk):
    """Обновление статуса задачи через AJAX"""
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if not new_status:
            return JsonResponse({'success': False, 'error': 'Статус не указан'}, status=400)
            
        # Получаем задачу и проверяем права доступа
        task = get_object_or_404(Task, pk=pk)
        if request.user not in task.assigned_to.all() and request.user != task.created_by:
            return JsonResponse(
                {'success': False, 'error': 'У вас нет прав на изменение этой задачи'}, 
                status=403
            )
        
        # Проверяем, что статус допустимый
        if new_status not in dict(Task.STATUS_CHOICES).keys():
            return JsonResponse(
                {'success': False, 'error': 'Недопустимый статус'}, 
                status=400
            )
        
        # Обновляем статус
        task.status = new_status
        task.save()
        
        # Возвращаем обновленные данные
        return JsonResponse({
            'success': True,
            'status': dict(Task.STATUS_CHOICES).get(new_status, 'Неизвестно'),
            'status_class': f'status-{task.status}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
