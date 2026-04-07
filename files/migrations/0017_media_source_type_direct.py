from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("files", "0016_category_requires_login"),
    ]

    operations = [
        migrations.AlterField(
            model_name="media",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("local", "Local"),
                    ("external", "External"),
                    ("direct", "Direct video URL"),
                ],
                default="local",
                help_text="Local upload, iframe embed (external), or direct progressive video URL",
                max_length=20,
            ),
        ),
    ]
