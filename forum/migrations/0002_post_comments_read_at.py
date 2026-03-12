from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='comments_read_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
