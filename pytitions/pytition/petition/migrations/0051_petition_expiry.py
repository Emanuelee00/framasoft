import datetime

from django.db import migrations, models
from django.utils import timezone

import petition.models

# Lifetime given to the petitions that exist when this migration runs
EXISTING_PETITIONS_LIFETIME_DAYS = 365


def set_existing_expiry(apps, schema_editor):
    Petition = apps.get_model('petition', 'Petition')
    expires_at = timezone.localdate() + datetime.timedelta(days=EXISTING_PETITIONS_LIFETIME_DAYS)
    Petition.objects.filter(expires_at__isnull=True).update(expires_at=expires_at)


class Migration(migrations.Migration):

    dependencies = [
        ('petition', '0050_signature_indexes_gdpr'),
    ]

    operations = [
        migrations.AddField(
            model_name='petition',
            name='expires_at',
            field=models.DateField(null=True, verbose_name='Deletion date'),
        ),
        migrations.RunPython(set_existing_expiry, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='petition',
            name='expires_at',
            field=models.DateField(default=petition.models.default_expires_at, verbose_name='Deletion date'),
        ),
        migrations.AddField(
            model_name='petition',
            name='expiry_reminder_days',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
