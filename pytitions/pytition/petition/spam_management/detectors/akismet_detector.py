from .base import BaseSpamDetector
from bs4 import BeautifulSoup
from django.conf import settings
from akismet import Akismet
from petition.helpers import send_mail_to_moderation_info
from django.utils.translation import gettext as _

def akismet_kwargs(author, email, content):
    # only send what Akismet needs: the author's email is optional and off unless AKISMET_SEND_EMAIL
    kwargs = dict(comment_type="blog-post", comment_author=author, comment_content=content,
                  is_test=1 if settings.AKISMET_IS_TEST else 0)
    if settings.AKISMET_SEND_EMAIL and email:
        kwargs["comment_author_email"] = email
    return kwargs


class AkismetSpamDetector(BaseSpamDetector):
    def is_spam(self, petition, pytitionuser) -> int:
        if not settings.AKISMET_KEY:
            return 0
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
                                    **akismet_kwargs(pytitionuser.username, pytitionuser.user.email, content))
        except Exception as e:
            is_spam = 0
            send_mail_to_moderation_info(settings.MODERATION_EMAIL, _("Akismet is down: {e}").format(e=e))
     
        return is_spam