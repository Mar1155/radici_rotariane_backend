from django.apps import AppConfig


class TraduzioneConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'traduzione'

    def ready(self):
        from traduzione import checks, lingue, segnali  # noqa: F401
        lingue._collega()
        segnali.collega()
