from django.apps import AppConfig


class TraduzioneConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'traduzione'

    def ready(self):
        from traduzione import checks, lingue  # noqa: F401  registra i controlli
        lingue._collega()
