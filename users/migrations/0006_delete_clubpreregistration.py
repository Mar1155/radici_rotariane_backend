from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_clubpreregistration'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ClubPreRegistration',
        ),
    ]
