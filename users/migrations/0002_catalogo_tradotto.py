"""I cataloghi del profilo passano al meccanismo unico di traduzione.

Prima ogni riga portava un `translations` JSONField con **una** lingua dentro:
`name` era il nome inglese e `translations['it']` quello italiano. In spagnolo,
portoghese, francese e tedesco il frontend non trovava niente e ricadeva
sull'inglese; le aree d'intervento, che hanno il nome in italiano, restavano
italiane in ogni lingua.

Questa migrazione non butta via quelle due lingue, le sposta dove stanno tutte
le altre:

- il nome italiano diventa `name`, perche' il sito si scrive in italiano;
- il nome inglese diventa una riga di traduzione **bloccata** e scritta da una
  persona, esattamente come i nomi inglesi delle regioni in `seed_geo`: nessuno
  deve trovarsi "Six Sigma" ritradotto dal modello linguistico;
- la sigla delle aree d'intervento, che stava nello stesso JSON insieme a due
  valori che si ricavano da lei, diventa una colonna.

L'ordine delle operazioni conta: la colonna nuova si aggiunge **prima** di
leggere i dati, e `translations` si toglie **dopo**.
"""

import re

from django.db import migrations, models

# La sigla stava nel JSON, ma non sempre: dove manca si ripesca dal nome, che
# e' quello che faceva il codice a valle.
SIGLA = re.compile(r'^\s*([A-Z])(\d*)\b')


def porta_le_traduzioni_nella_tabella(apps, schema_editor):
    Traduzione = apps.get_model('traduzione', 'Traduzione')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    for app_label, nome_modello in (('users', 'Skill'), ('users', 'SoftSkill'),
                                    ('users', 'FocusArea')):
        modello = apps.get_model(app_label, nome_modello)
        tipo = ContentType.objects.get_for_model(modello)
        # I nomi gia' presi: rinominare una riga su un nome che esiste
        # violerebbe l'unicita'. Non e' mai capitato con i dati dei seed, ma la
        # migrazione girera' anche su database che non ho visto.
        presi = set(modello.objects.values_list('name', flat=True))

        for riga in modello.objects.all():
            testi = riga.translations if isinstance(riga.translations, dict) else {}
            da_salvare = []

            if nome_modello == 'FocusArea':
                sigla = str(testi.get('code') or '').strip().upper()
                if not sigla:
                    trovata = SIGLA.match((riga.name or '').strip())
                    sigla = f'{trovata.group(1)}{trovata.group(2)}' if trovata else ''
                riga.code = sigla
                da_salvare.append('code')

            italiano = str(testi.get('it') or '').strip()
            inglese = (riga.name or '').strip()
            if italiano and italiano != inglese and italiano not in presi:
                # Il nome inglese era scritto da una persona: si conserva
                # bloccato, cosi' nessuna ritraduzione lo riscrive.
                Traduzione.objects.update_or_create(
                    content_type=tipo, object_id=str(riga.pk), target_language='en',
                    defaults=dict(source_language='it', texts={'name': inglese},
                                  locked_paths=['name'], provider='umano',
                                  needs_review=False),
                )
                presi.discard(inglese)
                presi.add(italiano)
                riga.name = italiano
                da_salvare.append('name')

            if da_salvare:
                riga.save(update_fields=da_salvare)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('traduzione', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='focusarea',
            name='code',
            field=models.CharField(blank=True, db_index=True, max_length=8,
                                   verbose_name='sigla'),
        ),
        migrations.RunPython(porta_le_traduzioni_nella_tabella,
                             migrations.RunPython.noop),
        migrations.RemoveField(model_name='focusarea', name='translations'),
        migrations.RemoveField(model_name='skill', name='translations'),
        migrations.RemoveField(model_name='softskill', name='translations'),
        migrations.AlterModelOptions(
            name='focusarea',
            options={'ordering': ['code', 'name']},
        ),
        migrations.AlterField(
            model_name='focusarea',
            name='name',
            field=models.CharField(max_length=600, unique=True, verbose_name='nome'),
        ),
        migrations.AlterField(
            model_name='skill',
            name='name',
            field=models.CharField(max_length=100, unique=True, verbose_name='nome'),
        ),
        migrations.AlterField(
            model_name='softskill',
            name='name',
            field=models.CharField(max_length=100, unique=True, verbose_name='nome'),
        ),
    ]
