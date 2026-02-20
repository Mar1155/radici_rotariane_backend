from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_rename_users_email_user_id_4b7ebf_idx_users_email_user_id_0b55cf_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClubPreRegistration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('normalized_name', models.CharField(editable=False, max_length=200, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_claimed', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
    ]
