from django.apps import AppConfig


class JournalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'journal'

    def ready(self):
        from .feedback_handlers import register_journal_feedback_handlers

        register_journal_feedback_handlers()
