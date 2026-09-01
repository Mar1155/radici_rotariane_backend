"""Personalizzazioni dell'admin Wagtail.

Due amministrazioni convivono in questa fase:

  /admin/  Jazzmin  — utenti, club, moderazione articoli
  /cms/    Wagtail  — pagine, tipi di articolo, menu, immagini

**Perché la gestione utenti resta fuori da Wagtail.** Non perché i suoi form
siano incompatibili — funzionano, e mostrano correttamente `email` al posto di
`username`. Il problema è più insidioso: `users.User` eredita da AbstractUser,
quindi ha `username` unique, ma `username` non compare nel form di Wagtail e
resta stringa vuota. Il primo utente creato da /cms/ funziona; il secondo va in
IntegrityError 500 ("duplicate key ... Key (username)=() already exists").
Un errore che sembra funzionare è peggio di uno che non funziona, quindi le
voci si nascondono **sempre**, superuser inclusi.

Verificato su Wagtail 7.4.3. Se un giorno servisse davvero la gestione utenti
qui, la strada è WAGTAIL_USER_CREATION_FORM / _EDIT_FORM che valorizzino
`username` (per esempio derivandolo dall'email).
"""

from wagtail import hooks

# Rotte gestite da Jazzmin: nasconderle a tutti, superuser inclusi.
_SEMPRE_NASCOSTE = {'users', 'groups'}

# Strumenti da sviluppatore: inutili al cliente, utili a chi lavora al progetto.
_SOLO_SVILUPPO = {'sites', 'reports', 'workflows', 'workflow-tasks',
                  'redirects', 'collections', 'forms'}


def _e_superuser(request):
    return bool(getattr(request.user, 'is_superuser', False))


def _filtra(menu_items, request):
    menu_items[:] = [
        item for item in menu_items
        if item.name not in _SEMPRE_NASCOSTE
        and (item.name not in _SOLO_SVILUPPO or _e_superuser(request))
    ]


@hooks.register('construct_main_menu')
def trim_main_menu(request, menu_items):
    _filtra(menu_items, request)


@hooks.register('construct_settings_menu')
def trim_settings_menu(request, menu_items):
    _filtra(menu_items, request)
