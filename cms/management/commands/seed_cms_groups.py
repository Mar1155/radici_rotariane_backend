"""Crea i gruppi di permessi del CMS.

Due ruoli distinti, che e' la ragione per cui i tipi di articolo stanno in una
sezione separata dell'admin:

  Redazione     compone pagine e carica immagini. E' il cliente.
  Gestione tipi definisce i tipi di articolo. E' chi sviluppa.

Chi non ha i permessi sui tipi non vede nemmeno la voce di menu: Wagtail
nasconde da solo le voci per cui manca il permesso.

Idempotente.
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

REDAZIONE = 'Redazione'
GESTIONE_TIPI = 'Gestione tipi'


class Command(BaseCommand):
    help = 'Crea i gruppi Redazione e Gestione tipi con i relativi permessi.'

    @transaction.atomic
    def handle(self, *args, **options):
        # Accesso all'admin Wagtail: senza questo non si entra proprio.
        accesso = Permission.objects.filter(
            content_type__app_label='wagtailadmin', codename='access_admin'
        ).first()

        def permessi(app_label, modelli, azioni=('add', 'change', 'delete')):
            return list(Permission.objects.filter(
                content_type__app_label=app_label,
                codename__in=[f'{a}_{m}' for m in modelli for a in azioni],
            ))

        redazione, _ = Group.objects.get_or_create(name=REDAZIONE)
        p = permessi('wagtailimages', ['image']) + permessi('wagtaildocs', ['document'])
        if accesso:
            p.append(accesso)
        redazione.permissions.set(p)

        gestione, _ = Group.objects.get_or_create(name=GESTIONE_TIPI)
        p = permessi('cms', ['articletype', 'articletypeinfoelement', 'articletypetag'])
        if accesso:
            p.append(accesso)
        gestione.permissions.set(p)

        self.stdout.write(self.style.SUCCESS(
            f'{REDAZIONE}: {redazione.permissions.count()} permessi | '
            f'{GESTIONE_TIPI}: {gestione.permissions.count()} permessi'))
        self.stdout.write(
            'I permessi sulle PAGINE non sono globali in Wagtail: si assegnano '
            'per ramo dell albero da /cms/groups/ (ma quella voce e nascosta ai '
            'non superuser).')
