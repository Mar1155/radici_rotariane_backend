"""Crea i gruppi di permessi del CMS.

Due ruoli distinti, che e' la ragione per cui i tipi di articolo stanno in una
sezione separata dell'admin:

  Redazione     compone pagine, carica immagini e cambia i menu. E' il cliente.
  Gestione tipi definisce i tipi di articolo e la geografia. E' chi sviluppa.

Chi non ha i permessi sui tipi non vede nemmeno la voce di menu: Wagtail
nasconde da solo le voci per cui manca il permesso.

Idempotente.
"""

from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.documents.permissions import permission_policy as policy_documenti
from wagtail.images.permissions import permission_policy as policy_immagini
from wagtail.models import Collection, GroupCollectionPermission, GroupPagePermission

from cms.bootstrap import assicura_homepage

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

        def permessi_di(policy, azioni=('add', 'change', 'delete', 'choose')):
            """I permessi che una policy di Wagtail controlla davvero.

            Con un modello immagine o documento **proprio**, Wagtail non e'
            coerente con se stesso: un metodo costruisce i codename dal modello
            personalizzato (`add_cmsimage`), quello che esegue il controllo li
            costruisce dal modello base (`add_image`). Conta il secondo, quindi
            si usa la sua stessa espressione invece di scriverli a mano: il
            giorno che Wagtail cambia idea, questo codice lo segue.
            """
            meta = policy.auth_model._meta
            codename = [get_permission_codename(a, meta) for a in azioni]
            return list(Permission.objects.filter(
                content_type=policy._content_type, codename__in=codename))

        redazione, _ = Group.objects.get_or_create(name=REDAZIONE)
        media = permessi_di(policy_immagini) + permessi_di(policy_documenti)
        # Il menu e' roba del cliente: e' la prima cosa che deve poter
        # cambiare da se'. I tipi di articolo e la geografia no.
        proprie = permessi('cms', ['menu', 'menuitem'])
        # Rivedere le traduzioni e' lavoro della redazione: e' chi conosce i
        # contenuti a sapere quando una macchina ha sbagliato un nome.
        # Solo 'change': le righe le crea il comando, non una persona.
        proprie += permessi('traduzione', ['traduzione'], azioni=('change',))
        proprie += permessi('traduzione', ['lingua'])
        redazione.permissions.set(proprie + ([accesso] if accesso else []))

        # Immagini e documenti seguono le COLLEZIONI, come le pagine seguono
        # l'albero: un permesso di gruppo normale non basta, va legato a una
        # collezione. Senza, la Redazione ha il permesso e non vede la voce.
        radice_collezioni = Collection.objects.order_by('depth').first()
        for permesso in media:
            GroupCollectionPermission.objects.get_or_create(
                group=redazione, collection=radice_collezioni, permission=permesso)

        # I permessi sulle pagine non sono globali: si danno per ramo
        # dell'albero. Senza, la Redazione entra in /cms/ e non puo' toccare
        # niente — che e' esattamente il suo lavoro.
        home = assicura_homepage()
        for codename in ('add_page', 'change_page', 'publish_page'):
            permesso = Permission.objects.filter(
                content_type__app_label='wagtailcore',
                content_type__model='page', codename=codename).first()
            if permesso:
                GroupPagePermission.objects.get_or_create(
                    group=redazione, page=home, permission=permesso)

        gestione, _ = Group.objects.get_or_create(name=GESTIONE_TIPI)
        p = permessi('cms', ['articletype', 'articletypeinfoelement',
                             'articletypetag', 'geoarea'])
        if accesso:
            p.append(accesso)
        gestione.permissions.set(p)

        self.stdout.write(self.style.SUCCESS(
            f'{REDAZIONE}: pagine, immagini, documenti e menu | '
            f'{GESTIONE_TIPI}: {gestione.permissions.count()} permessi'))
        self.stdout.write(
            f'{REDAZIONE} puo aggiungere, modificare e pubblicare sotto la '
            f'radice del sito. Per restringerla a un ramo, si cambia da '
            f'/cms/groups/ (voce visibile solo ai superuser).')
