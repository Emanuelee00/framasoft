from .utils import get_spam_detectors
from petition.models import ModerationReason, Moderation, MonitoringReason, Monitoring
from petition.helpers import send_moderation_mail, send_mail_to_moderation, send_mail_to_moderation_monitor, send_monitoring_mail
from django.conf import settings

# controller function that launches the detectors and defines a 'spam' value between 0 and 2
# 0: not spam, 1: possible spam, 2: definite spam.
# does moderation actions depending on the value of 'spam'
def is_spam(petition, pytitionuser) -> int:
    moderation_reason, created = ModerationReason.objects.get_or_create(msg="petition_inappropriate")
    monitoring_reason, created = MonitoringReason.objects.get_or_create(msg="petition_inappropriate")
    spam = 0

    for detector in get_spam_detectors():
        if detector.__class__.__name__== 'AkismetSpamDetector':
            if not(settings.AKISMET_MODERATION_AUTO):
                if detector.is_spam(petition, pytitionuser) == 2:
                    spam = 1
                else:
                    spam = detector.is_spam(petition, pytitionuser)
            else:
                spam = detector.is_spam(petition, pytitionuser)
        else:
            if detector.is_spam(petition, pytitionuser) > spam:
                spam = detector.is_spam(petition, pytitionuser)
    
    if spam == 2:
        if not(petition.moderated):
            petition.moderate()
            petition.monitor(False)

        moderation = Moderation.objects.create(petition=petition, reason=moderation_reason)
        send_mail_to_moderation(settings.MODERATION_EMAIL, petition, moderation.reason.text, "petition")
        send_moderation_mail(pytitionuser.user.email, pytitionuser.user.username, moderation.reason.text, "petition", petition)

    elif spam == 1:
        if not(petition.moderated):
            petition.monitor()
            monitoring = Monitoring.objects.create(petition=petition, reason=monitoring_reason, priority="strong")
            send_mail_to_moderation_monitor(settings.MODERATION_EMAIL, petition, monitoring.reason.text, "petition", "strong") 
            send_monitoring_mail(pytitionuser.user.email, pytitionuser.user.username, "petition", petition, monitoring.reason.text)
