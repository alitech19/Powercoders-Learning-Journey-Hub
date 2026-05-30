from django.apps import AppConfig


class GoalsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'goals'

    def ready(self):
        from .feedback_handlers import register_goal_feedback_handlers

        register_goal_feedback_handlers()
