from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from petition.expiry import send_expiry_reminders


### Command to launch daily with cron (purge_personal_data also runs it) ###
class Command(BaseCommand):
    help = "Email petition creators PETITION_EXPIRY_REMINDER_DAYS days before the deletion date of their petition."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help="Only count, do not send anything.")

    def handle(self, *args, **options):
        if not options['dry_run'] and not settings.SITE_BASE_URL:
            raise CommandError("SITE_BASE_URL is not set: the reminders would have no valid link.")
        sent = send_expiry_reminders(dry_run=options['dry_run'])
        self.stdout.write("expiry_reminders={}".format(sent) + (" (dry-run)" if options['dry_run'] else ""))
