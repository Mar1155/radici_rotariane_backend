from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_delete_clubpreregistration'),
    ]

    operations = [
        migrations.AlterField(
            model_name='focusarea',
            name='name',
            field=models.CharField(max_length=600, unique=True),
        ),
    ]
