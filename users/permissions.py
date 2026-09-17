"""Ruoli applicativi e permessi DRF.

Il ruolo sta qui e non in `section/views.py` perche' non riguarda solo gli
articoli: e' la stessa domanda che si pongono i menu, i pulsanti delle pagine e
i permessi delle API. Averne una definizione sola e' cio' che impedisce alle
risposte di divergere.

Nota sui permessi di Wagtail: sono un'altra cosa e restano separati. Governano
chi puo' fare cosa dentro `/cms/`, non chi puo' chiamare le API.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

# Gli stessi valori che il CMS usa in `ArticleType.can_publish`.
ANONIMO = 'anonymous'
SOCIO = 'user'
CLUB = 'club'
ADMIN = 'admin'


def ruolo_applicativo(user) -> str:
    """Ruolo dell'utente ai fini di cosa puo' pubblicare e vedere.

    La derivazione originale era invertita: guardava `user.club`, che su un
    account CLUB e' vuoto (sono i soci a puntare al club, non il contrario).
    Un club veniva quindi classificato 'user', e un socio con club 'club'.
    """
    if not getattr(user, 'is_authenticated', False):
        return ANONIMO
    if user.is_staff or user.is_superuser:
        return ADMIN
    if getattr(user, 'user_type', None) == 'CLUB':
        return CLUB
    return SOCIO


class IsAppAdmin(BasePermission):
    """Solo lo staff. Per le operazioni che governano la piattaforma."""

    message = 'Serve un account amministratore.'

    def has_permission(self, request, view):
        return ruolo_applicativo(request.user) == ADMIN


class IsOwnerOrAdmin(BasePermission):
    """Modifica e cancellazione solo a chi ha scritto, o a un amministratore.

    La lettura resta libera: se un oggetto non va letto da tutti, e' la vista a
    non doverlo restituire, non questo permesso a nasconderlo dopo.
    """

    message = 'Puoi modificare solo cio che hai pubblicato tu.'

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if ruolo_applicativo(request.user) == ADMIN:
            return True
        autore = getattr(obj, 'author_id', None)
        return bool(autore and autore == request.user.id)


class IsAuthenticatedOrReadOnly(BasePermission):
    """Lettura a tutti, scrittura a chi ha fatto accesso.

    Esiste gia' in DRF con questo nome: qui si ridichiara solo per tenere
    insieme, in un posto solo, i permessi che il progetto usa.
    """

    def has_permission(self, request, view):
        return (request.method in SAFE_METHODS
                or bool(request.user and request.user.is_authenticated))
