from django.apps import AppConfig


class HabitsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'habits'

    def ready(self):
        from .feedback_handlers import register_habit_feedback_handlers

        register_habit_feedback_handlers()
