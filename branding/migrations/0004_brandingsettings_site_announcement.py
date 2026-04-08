from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("branding", "0003_homepromoslide"),
    ]

    operations = [
        migrations.AddField(
            model_name="brandingsettings",
            name="site_announcement",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Optional plain-text message at the top of every page. "
                    "Line breaks are preserved. Leave blank to hide."
                ),
            ),
        ),
    ]
