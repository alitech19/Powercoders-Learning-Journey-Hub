from django.apps import AppConfig


class ReflectionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reflections'

    def ready(self):
        from .feedback_handlers import register_reflection_feedback_handlers

        register_reflection_feedback_handlers()
