from django.apps import AppConfig


class LearningConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "learning"
    verbose_name = "Learning (LMS)"

    def ready(self):
        import learning.signals  # noqa: F401
        import learning.methods.calendar_sync  # noqa: F401
