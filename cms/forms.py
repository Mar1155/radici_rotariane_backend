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
