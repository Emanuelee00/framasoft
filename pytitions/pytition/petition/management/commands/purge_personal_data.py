from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from petition.models import Petition, Signature


### Command to launch with cron to delete or blank personal data past its retention period ###
class Command(BaseCommand):
    help = "Delete or blank personal data past its retention period (unconfirmed signatures, IP hashes, creators' IP/user agent)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help="Only count, do not modify anything.")

    def handle(self, *args, **options):
        now = timezone.now()
        unconfirmed = Signature.objects.filter(
            confirmed=False, date__lt=now - timedelta(days=settings.UNCONFIRMED_SIGNATURE_RETENTION_DAYS))
        ip_hashes = Signature.objects.filter(
            ipaddress__isnull=False, date__lt=now - timedelta(days=settings.SIGNATURE_IP_HASH_RETENTION_DAYS))
        creator_ips = Petition.objects.filter(
            creation_date__lt=now - timedelta(days=settings.CREATOR_IP_RETENTION_DAYS)
        ).exclude(ipaddr__isnull=True, user_agent__isnull=True)

        counts = [("unconfirmed_signatures", unconfirmed.count()),
                  ("signature_ip_hashes", ip_hashes.count()),
                  ("creator_ip_ua", creator_ips.count())]
        if not options['dry_run']:
            unconfirmed.delete()
            ip_hashes.update(ipaddress=None)
            creator_ips.update(ipaddr=None, user_agent=None)
        # counters only: no personal data in the output
        self.stdout.write(" ".join("{}={}".format(k, v) for k, v in counts)
                          + (" (dry-run)" if options['dry_run'] else ""))
