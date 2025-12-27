from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_user_club'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='club_president',
            field=models.CharField(blank=True, max_length=150),
        ),
    ]
