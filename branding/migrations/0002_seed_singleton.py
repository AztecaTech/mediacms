from django.db import migrations


def create_singleton(apps, schema_editor):
    branding_settings = apps.get_model("branding", "BrandingSettings")
    branding_settings.objects.update_or_create(pk=1, defaults={})


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("branding", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_singleton, noop_reverse),
    ]
