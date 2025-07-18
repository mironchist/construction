# Generated by Django 5.2.3 on 2025-06-15 11:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("construction", "0005_task"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="priority",
            field=models.CharField(
                choices=[("low", "Низкий"), ("medium", "Средний"), ("high", "Высокий")],
                default="medium",
                help_text="Приоритет выполнения задачи",
                max_length=10,
                verbose_name="Приоритет",
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="construction_site",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tasks",
                to="construction.constructionsite",
                verbose_name="Строительный объект",
            ),
        ),
    ]
