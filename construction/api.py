from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Task

@csrf_exempt
@login_required
def update_task_status(request, task_id):
    if request.method == 'POST':
        try:
            task = Task.objects.get(id=task_id)
            
            # Проверяем права доступа
            if not (request.user == task.created_by or 
                   request.user in task.assigned_to.all() or 
                   request.user.is_superuser or 
                   request.user.is_admin):
                return JsonResponse({
                    'success': False, 
                    'error': 'У вас нет прав на изменение этой задачи'
                }, status=403)
            
            # Получаем новый статус из запроса
            new_status = request.POST.get('status')
            if not new_status:
                return JsonResponse({
                    'success': False, 
                    'error': 'Не указан новый статус'
                }, status=400)
            
            # Проверяем, что статус допустимый
            if new_status not in dict(Task.STATUS_CHOICES):
                return JsonResponse({
                    'success': False, 
                    'error': 'Недопустимый статус задачи'
                }, status=400)
            
            # Обновляем статус
            task.status = new_status
            task.save()
            
            return JsonResponse({
                'success': True,
                'status_display': task.get_status_display(),
                'status_color': task.get_status_color()
            })
            
        except Task.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': 'Задача не найдена'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False, 
        'error': 'Метод не разрешен'
    }, status=405)
