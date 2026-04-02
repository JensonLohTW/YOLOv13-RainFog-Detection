from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("system", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="systemconfigitem",
            name="is_sensitive",
            field=models.BooleanField(default=False),
        ),
    ]
