from django.apps import AppConfig


class MktConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mkt"

    # def ready(self):
    #     import mkt.signals
