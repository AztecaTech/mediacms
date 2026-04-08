from django.core.cache import cache
from django.db import migrations


def clear_branding_cache(apps, schema_editor):
    # branding.models.BRANDING_CACHE_KEY — inline to avoid importing app models in migrations.
    cache.delete("branding_settings")


class Migration(migrations.Migration):

    dependencies = [
        ("branding", "0004_brandingsettings_site_announcement"),
    ]

    operations = [
        migrations.RunPython(clear_branding_cache, migrations.RunPython.noop),
    ]
