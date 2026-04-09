from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0007_ldap_directory_source"),
    ]

    operations = [
        migrations.AddField(
            model_name="discussionnotificationpreference",
            name="email_mentions",
            field=models.BooleanField(
                default=True,
                help_text="When false, @mention emails are skipped (in-app mention notifications still created).",
            ),
        ),
    ]
