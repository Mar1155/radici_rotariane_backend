"""Creazione della radice del sito.

Sta qui e non dentro un comando perche' serve a piu' di uno: la HomePage e' il
genitore di tutte le altre pagine, ma a sua volta rimanda a loro. Senza un
guscio creato per primo, i comandi si aspetterebbero a vicenda.
"""

from wagtail.models import Locale, Page, Site


def assicura_homepage(titolo='Radici Rotariane', slug='home'):
    """Restituisce la HomePage, creandola vuota se non c'e'.

    La imposta anche come radice del sito: senza, Wagtail continuerebbe a
    servire la pagina di benvenuto installata dalle migrazioni.
    """
    from cms.models import HomePage

    locale = Locale.get_default()
    radice = Page.objects.get(depth=1)
    home = HomePage.objects.filter(locale=locale).first()
    if home is None:
        # Le migrazioni di Wagtail installano una pagina di benvenuto con lo
        # stesso slug: va tolta di mezzo, altrimenti la nostra non entra.
        # Attenzione: Site.root_page cancella a cascata, quindi questa riga si
        # porta via anche il Site di default. Lo ricreiamo qui sotto.
        Page.objects.child_of(radice).filter(slug=slug).exclude(
            pk__in=HomePage.objects.values('pk')).delete()
        radice.add_child(instance=HomePage(title=titolo, slug=slug, locale=locale))
        home = HomePage.objects.get(locale=locale)
        home.save_revision().publish()

    assicura_sito(home)
    return home


def assicura_sito(home, hostname='localhost', porta=80):
    """Punta il sito di default alla nostra homepage, creandolo se manca.

    Su un database appena creato il Site non c'e' piu': la pagina di benvenuto
    ne era la radice, e cancellarla lo ha cancellato a cascata. Senza Site,
    Wagtail non risolve nessun percorso e l'API risponde 404 a tutto tranne
    che alla homepage.
    """
    sito = Site.objects.filter(is_default_site=True).first()
    if sito is None:
        return Site.objects.create(
            hostname=hostname, port=porta, site_name=home.title,
            root_page=home, is_default_site=True)
    if sito.root_page_id != home.pk:
        sito.root_page = home
        sito.save()
    return sito
