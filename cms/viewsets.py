"""Registrazione dei tipi di articolo nell'admin Wagtail.

I tipi di articolo vivono in una sezione separata ("Struttura") rispetto a
pagine e immagini. La ragione e' pratica: comporre una pagina e' un'attivita'
quotidiana del cliente, definire un tipo di articolo e' un'attivita' rara e
strutturale, che nella maggior parte dei casi resta a chi sviluppa.

L'accesso si governa con i permessi standard di Django: chi non ha
`cms.change_articletype` non vede nemmeno la voce di menu, perche' Wagtail
nasconde da solo le voci per cui manca il permesso. Basta quindi un gruppo
dedicato per decidere chi puo' entrarci.
"""

from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from cms.models import ArticleType, GeoArea, Menu
from traduzione.models import Lingua, Traduzione


class ArticleTypeViewSet(SnippetViewSet):
    model = ArticleType
    icon = 'tasks'
    menu_label = 'Tipi di articolo'
    menu_name = 'article-types'
    list_display = ['name', 'name_plural', 'key']
    search_fields = ['name', 'name_plural', 'key']
    ordering = ['name']
    add_to_admin_menu = False   # sta dentro il gruppo, non da solo


class GeoAreaViewSet(SnippetViewSet):
    model = GeoArea
    icon = 'site'
    menu_label = 'Aree geografiche'
    menu_name = 'geo-areas'
    list_display = ['name', 'level', 'code', 'path']
    list_filter = ['level', 'is_active']
    search_fields = ['name', 'key', 'code']
    ordering = ['path']
    add_to_admin_menu = False


class MenuViewSet(SnippetViewSet):
    model = Menu
    icon = 'list-ul'
    menu_label = 'Menu'
    menu_name = 'menus'
    list_display = ['name', 'key']
    search_fields = ['name', 'key']
    # Il menu, a differenza dei tipi di articolo, e' roba che il cliente tocca:
    # sta nel menu principale dell'admin, non dentro "Struttura".
    add_to_admin_menu = True
    menu_order = 300


class LinguaViewSet(SnippetViewSet):
    """Le lingue in cui il sito si legge.

    Aggiungerne una qui basta per il contenuto: al primo giro di
    `translate_pending` tutto cio' che non ce l'ha viene tradotto. Le etichette
    dell'app (bottoni, form, errori) restano nel codice e arrivano con il
    deploy successivo: e' il confine fra cio' che scrive l'admin e cio' che
    scrive lo sviluppatore.
    """

    model = Lingua
    icon = 'globe'
    menu_label = 'Lingue'
    menu_name = 'lingue'
    list_display = ['nome', 'codice', 'attiva', 'ordine']
    search_fields = ['nome', 'codice']
    ordering = ['ordine', 'codice']
    add_to_admin_menu = False


class TraduzioneViewSet(SnippetViewSet):
    """Le traduzioni da rivedere.

    Sta nel menu principale e non dentro "Struttura" perche' rivedere una
    traduzione e' lavoro quotidiano, mentre definire un tipo di articolo non lo
    e' — la stessa distinzione gia' fatta per i menu.

    Le righe con `da rivedere` acceso vengono prima: sono quelle che una
    macchina ha prodotto e nessuno ha ancora guardato.
    """

    model = Traduzione
    icon = 'globe'
    menu_label = 'Traduzioni'
    menu_name = 'traduzioni'
    list_display = ['__str__', 'target_language', 'provider',
                    'needs_review', 'human_locked', 'updated_at']
    list_filter = ['target_language', 'provider', 'needs_review', 'human_locked']
    ordering = ['-needs_review', '-updated_at']
    add_to_admin_menu = True
    menu_order = 400

    def get_form_class(self, for_update=False):
        from cms.forms import form_traduzione
        return form_traduzione()


class StrutturaGroup(SnippetViewSetGroup):
    items = (ArticleTypeViewSet, GeoAreaViewSet, LinguaViewSet)
    menu_icon = 'cogs'
    menu_label = 'Struttura'
    menu_name = 'struttura'
    menu_order = 900   # in fondo: non e' roba di uso quotidiano


register_snippet(MenuViewSet)
register_snippet(TraduzioneViewSet)
register_snippet(StrutturaGroup)
