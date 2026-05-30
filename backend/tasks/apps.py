from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tasks'

    def ready(self):
        from .feedback_handlers import register_task_feedback_handlers

        register_task_feedback_handlers()
