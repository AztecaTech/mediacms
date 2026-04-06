from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0015_add_external_video_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='requires_login',
            field=models.BooleanField(default=False, db_index=True, help_text='Visible to all signed-in users but hidden from anonymous visitors'),
        ),
    ]
