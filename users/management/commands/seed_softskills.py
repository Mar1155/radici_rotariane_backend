from django.core.management.base import BaseCommand

from users.models import SoftSkill
from users.management.commands.seed_skills import SOFT_SKILLS


class Command(BaseCommand):
    help = "Popola un catalogo esteso di SoftSkill senza duplicati."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite-translations",
            action="store_true",
            help="Sovrascrive sempre la traduzione italiana esistente.",
        )

    def handle(self, *args, **options):
        overwrite = options["overwrite_translations"]
        created_count = 0
        updated_count = 0

        for name, it_translation in SOFT_SKILLS:
            obj, created = SoftSkill.objects.get_or_create(name=name)
            translations = dict(obj.translations or {})

            if created:
                created_count += 1

            if overwrite or not translations.get("it"):
                translations["it"] = it_translation
                obj.translations = translations
                obj.save(update_fields=["translations"])
                if not created:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Seed soft skills completato: "
                f"create={created_count}, aggiornate={updated_count}."
            )
        )
