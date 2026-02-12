# Generated migration to add contact info to eccellenze-calabresi cards

from django.db import migrations


def add_contact_info(apps, schema_editor):
    """
    Adds a contact info element to all existing eccellenze-calabresi cards.
    For cards with only 1 info element (the old discount/benefit),
    adds a generic placeholder contact info as the 2nd element.
    """
    Card = apps.get_model('section', 'Card')

    for card in Card.objects.filter(section='eccellenze-calabresi'):
        if card.infoElementValues and len(card.infoElementValues) == 1:
            # Add generic contact placeholder as second element
            card.infoElementValues.append('Contattaci per informazioni')
            card.save(update_fields=['infoElementValues'])


def reverse_contact_info(apps, schema_editor):
    """
    Removes the contact info element (2nd element) from eccellenze-calabresi cards.
    """
    Card = apps.get_model('section', 'Card')

    for card in Card.objects.filter(section='eccellenze-calabresi'):
        if card.infoElementValues and len(card.infoElementValues) == 2:
            # Remove the last element (the contact placeholder we added)
            card.infoElementValues.pop()
            card.save(update_fields=['infoElementValues'])


class Migration(migrations.Migration):

    dependencies = [
        ('section', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_contact_info, reverse_contact_info),
    ]
