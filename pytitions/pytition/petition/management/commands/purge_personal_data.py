from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from petition.expiry import delete_in_batches, purge_expired_petitions, send_expiry_reminders, update_in_batches
from petition.models import Petition, Signature


### Command to launch daily with cron to delete or blank personal data past its retention period ###
class Command(BaseCommand):
    help = ("Delete or blank personal data past its retention period (unconfirmed signatures, IP hashes, "
            "creators' IP/user agent), send the expiry reminders and permanently delete expired petitions.")

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help="Only count, do not modify or send anything.")
        parser.add_argument('--batch-size', type=int, default=settings.PURGE_BATCH_SIZE,
                            help="Rows deleted or updated per statement (default: PURGE_BATCH_SIZE).")

    def handle(self, *args, **options):
        dry_run, batch_size = options['dry_run'], max(1, options['batch_size'])
        suffix = " (dry-run)" if dry_run else ""
        now = timezone.now()
        unconfirmed = Signature.objects.filter(
            confirmed=False, date__lt=now - timedelta(days=settings.UNCONFIRMED_SIGNATURE_RETENTION_DAYS))
        ip_hashes = Signature.objects.filter(
            ipaddress__isnull=False, date__lt=now - timedelta(days=settings.SIGNATURE_IP_HASH_RETENTION_DAYS))
        creator_ips = Petition.objects.filter(
            creation_date__lt=now - timedelta(days=settings.CREATOR_IP_RETENTION_DAYS)
        ).exclude(ipaddr__isnull=True, user_agent__isnull=True)

        if dry_run:
            counts = [unconfirmed.count(), ip_hashes.count(), creator_ips.count()]
        else:
            # each processed row leaves its queryset, so the batches stop by themselves
            counts = [delete_in_batches(unconfirmed, batch_size),
                      update_in_batches(ip_hashes, batch_size, ipaddress=None),
                      update_in_batches(creator_ips, batch_size, ipaddr=None, user_agent=None)]
        # counters only: no personal data in the output
        self.stdout.write("unconfirmed_signatures={} signature_ip_hashes={} creator_ip_ua={}".format(*counts) + suffix)

        # Expired petitions: the reminders first; without SITE_BASE_URL they cannot be sent,
        # so nothing is deleted (the petitions stay closed to signatures)
        if not settings.SITE_BASE_URL and not dry_run:
            self.stderr.write("SITE_BASE_URL is not set: no expiry reminder sent, no expired petition deleted.")
            return
        reminders = send_expiry_reminders(dry_run=dry_run)
        petitions, signatures = purge_expired_petitions(batch_size, dry_run=dry_run)
        self.stdout.write("expiry_reminders={} expired_petitions={} expired_signatures={}".format(
            reminders, petitions, signatures) + suffix)
