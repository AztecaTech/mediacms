from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0006_discussion_notification_preferences"),
    ]

    operations = [
        migrations.CreateModel(
            name="LdapDirectorySource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("server_uri", models.CharField(help_text="e.g. ldap://ldap.example.org:389", max_length=512)),
                ("bind_dn", models.CharField(blank=True, max_length=512)),
                ("bind_password", models.CharField(blank=True, max_length=256)),
                ("user_search_base", models.CharField(max_length=512)),
                (
                    "user_search_filter",
                    models.CharField(
                        blank=True,
                        help_text="Optional; default (objectClass=person) used when empty.",
                        max_length=512,
                    ),
                ),
                ("enabled", models.BooleanField(default=False)),
                ("last_sync_at", models.DateTimeField(blank=True, null=True)),
                ("last_sync_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
    ]
