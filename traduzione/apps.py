from django.apps import AppConfig


class TraduzioneConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'traduzione'

    def ready(self):
        from traduzione import lingue
        lingue._collega()
