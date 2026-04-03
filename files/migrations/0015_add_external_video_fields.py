# Manual migration: external video embed fields on Media

from django.db import migrations, models

from files.models.utils import original_media_file_path


class Migration(migrations.Migration):
    dependencies = [
        ("files", "0014_alter_subtitle_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="media",
            name="source_url",
            field=models.URLField(
                blank=True,
                help_text="URL of external video (YouTube, Vimeo, etc.)",
                max_length=500,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="media",
            name="source_type",
            field=models.CharField(
                choices=[("local", "Local"), ("external", "External")],
                default="local",
                help_text="Whether media is a local upload or external embed",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="media",
            name="embed_html",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Cached oEmbed HTML for platforms without known embed URL patterns",
            ),
        ),
        migrations.AlterField(
            model_name="media",
            name="media_file",
            field=models.FileField(
                blank=True,
                help_text="media file",
                max_length=500,
                null=True,
                upload_to=original_media_file_path,
                verbose_name="media file",
            ),
        ),
    ]
