from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0004_remove_forum_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="MessageTranslation",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("target_language", models.CharField(max_length=10)),
                ("translated_text", models.TextField()),
                (
                    "provider",
                    models.CharField(
                        choices=[("deepl", "DeepL"), ("google", "Google Cloud Translation")],
                        max_length=20,
                    ),
                ),
                (
                    "detected_source_language",
                    models.CharField(blank=True, max_length=10, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="chat.message",
                    ),
                ),
            ],
            options={
                "unique_together": {("message", "target_language")},
            },
        ),
        migrations.AddIndex(
            model_name="messagetranslation",
            index=models.Index(fields=["message", "target_language"], name="chat_message_message_1a73a1_idx"),
        ),
        migrations.AddIndex(
            model_name="messagetranslation",
            index=models.Index(fields=["target_language"], name="chat_message_target__62e6f5_idx"),
        ),
    ]
