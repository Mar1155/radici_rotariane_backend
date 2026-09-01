"""Costruisce /cip nel CMS.

Porta nel contenuto anche i referenti, che oggi stanno dentro
ReferentiCIP.tsx con un commento che lo ammette: "Mock data - sostituire con
dati reali". Da qui in avanti il cliente li aggiorna quando cambiano gli
incarichi, senza chiamare nessuno.

Idempotente.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Locale

from cms.models import HomePage, StandardPage


class Command(BaseCommand):
    help = 'Crea (o aggiorna) la pagina /cip.'

    def add_arguments(self, parser):
        parser.add_argument('--content', required=True)
        parser.add_argument('--people', required=True,
                            help='JSON dei referenti estratti dal componente')

    @transaction.atomic
    def handle(self, *args, **options):
        d = json.loads(Path(options['content']).read_text(encoding='utf-8'))
        persone = json.loads(Path(options['people']).read_text(encoding='utf-8'))
        locale = Locale.get_default()
        home = HomePage.objects.filter(locale=locale).first()

        w = d['whatAreCIP']
        r = d['cipResponsibilities']
        o = d['officialWebsite']
        rf = d['referenti']

        corpo = [
            ('hero', {'title': d['hero']['title'], 'description': d['hero']['description'],
                      'tag': d['hero'].get('tag', ''), 'surface': 'brand-gradient',
                      'scroll_to_id': 'contenuto'}),
            ('quote', {
                'quote': 'Se i Comitati Inter-Paese non esistessero, bisognerebbe inventarli.',
                'author': 'Frank Devlyn', 'role': 'Presidente del Rotary International',
                'place_and_date': 'Lilla, Francia • 25 Marzo 2001'}),
            ('text_band', {'title': w['title'], 'body': w['description'], 'surface': 'light'}),
            ('task_list', {
                'title': r['title'], 'subtitle': r.get('subtitle', ''),
                'note': r.get('missionContext', ''), 'surface': 'white',
                'items': [
                    {'title': t['title'],
                     'link': ({'label': t.get('linkText', ''), 'route': '',
                               'external_url': t.get('href', ''), 'page': None}
                              if t.get('href') and t.get('linkText') else
                              {'label': '', 'route': '', 'external_url': '', 'page': None})}
                    for t in r['tasks']
                ]}),
            ('cta_banner', {
                'title': o['title'], 'description': o.get('description', ''),
                'surface': 'light',
                'primary_cta': {'label': o['buttonText'], 'route': '',
                                'external_url': o['href'], 'page': None},
                'secondary_cta': {'label': '', 'route': '', 'external_url': '', 'page': None}}),
            ('people_grid', {
                'title': rf['title'], 'description': rf.get('description', ''),
                'columns': '2', 'surface': 'white',
                'items': [{'name': p['name'], 'role': p['role'], 'email': p['email'],
                           'photo': None, 'areas': p['countries']} for p in persone]}),
        ]

        pagina = StandardPage.objects.filter(slug='cip', locale=locale).first()
        if pagina is None:
            pagina = StandardPage(title='Comitati Inter-Paese', slug='cip', locale=locale)
            home.add_child(instance=pagina)
        pagina.body = corpo
        pagina.save()
        pagina.save_revision().publish()
        self.stdout.write(self.style.SUCCESS(
            f'/cip creata con {len(corpo)} blocchi e {len(persone)} referenti.'))
