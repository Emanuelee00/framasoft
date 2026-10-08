from django.core.management.base import BaseCommand
from petition.models import Petition
from petition.spam_management.anti_bot_tests.check_signature_number import check_signature_number, check_signature_variation, check_unconfirmed_signatures, check_creation_signatures

### Command to launch with cron to trigger anti-bot tests on signatures in petitions with cron_to_schedule = True ###
class Command(BaseCommand):
    help = "launch cron script for bot signatures tests"

    def handle(self, *args, **options):
        for petition in Petition.objects.filter(cron_to_schedule=True):
            check_signature_number(petition)
            check_signature_variation(petition, "yesterday")
            check_signature_variation(petition, "last week")
            check_unconfirmed_signatures(petition)
            check_creation_signatures(petition)
            # checked: wait for a new signature before checking this petition again
            Petition.objects.filter(pk=petition.pk).update(cron_to_schedule=False)
