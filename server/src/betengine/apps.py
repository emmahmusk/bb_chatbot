from django.apps import AppConfig


class BetengineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "betengine"
    def ready(self):
        # Import your signals file to register the handlers
        import betengine.signals