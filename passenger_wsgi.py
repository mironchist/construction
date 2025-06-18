import os
import sys

# Укажите путь к вашему проекту
INTERP = os.path.expanduser("/home/your_username/venv/bin/python3")
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

# Добавляем путь к проекту
sys.path.append(os.getcwd())

# Запускаем приложение
from construction_project.wsgi import application
