"""Le sole soft skill, quando non si vuole rifare tutto il catalogo.

Le coppie e la regola sono quelle di `seed_skills`: ripeterle qui vorrebbe dire
che un giorno i due comandi scriveranno due cataloghi diversi.
"""

from django.core.management.base import BaseCommand

from users.models import SoftSkill
from users.management.commands.seed_skills import SOFT_SKILLS
from users.management.commands.seed_skills import Command as Catalogo


class Command(BaseCommand):
    help = "Popola un catalogo esteso di SoftSkill senza duplicati."

    def handle(self, *args, **options):
        create, aggiornate = Catalogo()._upsert_items(SoftSkill, SOFT_SKILLS)
        self.stdout.write(self.style.SUCCESS(
            f"Seed soft skills completato: create={create}, aggiornate={aggiornate}."
        ))
