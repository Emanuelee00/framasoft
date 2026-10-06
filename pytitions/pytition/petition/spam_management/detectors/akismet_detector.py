from .base import BaseSpamDetector
from bs4 import BeautifulSoup
from django.conf import settings
from akismet import Akismet
from petition.helpers import send_mail_to_moderation_info
from django.utils.translation import gettext as _

class AkismetSpamDetector(BaseSpamDetector):
    def is_spam(self, petition, pytitionuser) -> int:
        # initialize Akismet
        akismet = Akismet(settings.AKISMET_KEY, blog=settings.AKISMET_URL)
        # get the needed content to check it the petition is spam
        soup = BeautifulSoup(petition.text, "html.parser")
        text_msg = soup.get_text(separator = " ")
        clean_text_msg = ' '.join(text_msg.split())

        content = str(petition.title) + " " + clean_text_msg
        
        # Use akismet.check to see if spam. Returns 0: not spam, 1: possible spam, 2: definite spam. If Akismet doesn't work return 0 and send mail to moderation
        try:
            is_spam = akismet.check(petition.ipaddr, petition.user_agent,
                                    comment_type = "blog-post",
                                    comment_author = pytitionuser.username,
                                    comment_author_email = pytitionuser.user.email,
                                    comment_content = content, 
                                    is_test = 1) # is_test to change in production
        except Exception as e:
            is_spam = 0
            send_mail_to_moderation_info(settings.MODERATION_EMAIL, _("Akismet is down: {e}").format(e=e))
     
        return is_spam