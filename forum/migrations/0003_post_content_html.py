from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0002_comment_parent'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='content_html',
            field=models.TextField(blank=True),
        ),
    ]
