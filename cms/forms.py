"""Form dell'admin per i tipi di articolo.

I campi che elencano scelte multiple (campi attivi, bottoni, ruoli, blocchi)
sono JSONField sul modello, perche' e' la forma giusta per il database. Ma il
widget predefinito di un JSONField e' una textarea di JSON grezzo: inusabile
anche per chi sa cos'e' il JSON, e fuori discussione per un admin non tecnico.

Qui vengono presentati come gruppi di checkbox.
"""

from django import forms
from wagtail.admin.forms.models import WagtailAdminModelForm

from cms import vocabularies as vocab


class CheckboxJSONField(forms.MultipleChoiceField):
    """MultipleChoiceField che legge e scrive una lista JSON."""

    widget = forms.CheckboxSelectMultiple

    def prepare_value(self, value):
        # Il modello puo' restituire None o una stringa JSON a seconda del backend.
        if value is None:
            return []
        if isinstance(value, str):
            import json
            try:
                return json.loads(value)
            except ValueError:
                return []
        return list(value)


class ArticleTypeForm(WagtailAdminModelForm):
    active_fields = CheckboxJSONField(
        choices=vocab.FIELD_CHOICES, required=False, label='Campi attivi',
        help_text='Quali campi esistono su questo tipo di articolo.',
    )
    required_fields = CheckboxJSONField(
        choices=vocab.FIELD_CHOICES, required=False, label='Campi obbligatori',
        help_text="Sottoinsieme dei campi attivi: senza questi l'articolo non "
                  'si puo pubblicare.',
    )
    buttons = CheckboxJSONField(
        choices=vocab.BUTTON_CHOICES, required=False, label='Azioni sulla card',
    )
    can_publish = CheckboxJSONField(
        choices=vocab.ROLE_CHOICES, required=False, label='Chi puo pubblicare',
        help_text='Se non selezioni nessuno, il tipo e di sola lettura: '
                  'gli articoli esistono ma nessuno ne puo creare di nuovi.',
    )
    body_blocks = CheckboxJSONField(
        choices=vocab.BODY_BLOCK_CHOICES, required=False,
        label='Blocchi ammessi nel corpo',
        help_text="Cosa puo inserire l'autore scrivendo l'articolo.",
    )

    class Meta:
        # I campi li definisce il pannello di Wagtail; qui si sovrascrivono
        # soltanto i widget.
        pass


class TraduzioneForm(WagtailAdminModelForm):
    """La revisione di una traduzione, frase per frase.

    `texts` e' un JSONField, e il widget predefinito e' una textarea di JSON
    grezzo: inusabile per lo stesso motivo per cui esiste `CheckboxJSONField`
    qui sopra. Qui diventa **un campo per percorso, con accanto l'originale**,
    nell'ordine in cui compaiono nel documento.

    Chi rivede vede due colonne, non un blob — e vede da cosa sta traducendo,
    che e' l'unica informazione che serve davvero per correggere.
    """

    PREFISSO = 'testo__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from traduzione.percorsi import estrai

        traduzione = self.instance
        originali = estrai(traduzione.oggetto) if traduzione.oggetto else {}
        self._percorsi = []

        bloccati = set(traduzione.locked_paths or [])
        for percorso in sorted(set(originali) | set(traduzione.texts or {})):
            originale = originali.get(percorso, '')
            tradotto = (traduzione.texts or {}).get(percorso, '')
            nome = f'{self.PREFISSO}{percorso}'
            lunga = len(originale) > 80 or len(tradotto) > 80
            self.fields[nome] = forms.CharField(
                required=False, initial=tradotto, label=percorso,
                widget=forms.Textarea(attrs={'rows': 3}) if lunga else forms.TextInput(),
                help_text=(f'{originale}' if originale else
                           'Non c e piu nell originale: si puo cancellare.'),
            )
            self._percorsi.append((percorso, nome, originale))
            if percorso in bloccati:
                self.fields[nome].label = f'{percorso}  (corretta a mano)'

    def save(self, commit=True):
        traduzione = super().save(commit=False)
        testi = dict(traduzione.texts or {})
        bloccati = set(traduzione.locked_paths or [])

        for percorso, nome, _ in self._percorsi:
            nuovo = (self.cleaned_data.get(nome) or '').strip()
            if nuovo != (testi.get(percorso) or ''):
                # Chi tocca una frase la rivendica: da qui in poi la
                # ritraduzione automatica la lascia stare. Per percorso, non
                # per oggetto: il resto continua a rinfrescarsi.
                bloccati.add(percorso)
            if nuovo:
                testi[percorso] = nuovo
            else:
                testi.pop(percorso, None)
                bloccati.discard(percorso)

        traduzione.texts = testi
        traduzione.locked_paths = sorted(bloccati)
        traduzione.needs_review = False
        if bloccati:
            traduzione.provider = 'umano'
        if commit:
            traduzione.save()
        return traduzione


def form_traduzione():
    """La classe del form, costruita quando i modelli ci sono.

    Non si puo' dichiarare `Meta.model` qui sopra: questo modulo viene
    importato prima che il registro delle app sia pronto, e l'import del
    modello esploderebbe.
    """
    from django.forms import modelform_factory
    from traduzione.models import Traduzione
    return modelform_factory(Traduzione, form=TraduzioneForm,
                             fields=['needs_review'])
