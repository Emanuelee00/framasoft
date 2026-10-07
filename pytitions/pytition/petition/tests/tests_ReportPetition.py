from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from .utils import add_default_data

from petition.models import Moderation, ModerationReason, Petition


class ReportPetitionViewTest(TestCase):
    """Test report_petition view"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()
        cls.reason = ModerationReason.objects.create(msg="petition_spam", visible=True)
        cls.hidden_reason = ModerationReason.objects.create(msg="manual_moderation", visible=False)

    def setUp(self):
        cache.clear()
        self.petition = Petition.objects.filter(published=True).first()
        self.url = reverse("report_petition", args=[self.petition.id])

    def test_get_shows_form_without_reporting(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "petition/report.html")
        self.assertEqual(response["X-Robots-Tag"], "noindex")
        self.assertContains(response, 'method="post"')
        self.assertContains(response, 'value="{}"'.format(self.reason.pk))
        self.assertContains(response, self.reason.text)
        self.assertNotContains(response, 'ModerationReason object')
        self.assertNotContains(response, 'value="{}"'.format(self.hidden_reason.pk))
        self.assertEqual(Moderation.objects.count(), 0)

    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(self.url, {"reason": self.reason.pk})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Moderation.objects.count(), 0)

    def test_post_creates_one_report(self):
        response = self.client.post(self.url, {"reason": self.reason.pk})
        self.assertRedirects(response, self.petition.url)
        moderation = Moderation.objects.get()
        self.assertEqual(moderation.petition, self.petition)
        self.assertEqual(moderation.reason, self.reason)

    def test_post_shows_confirmation_on_petition_page(self):
        response = self.client.post(self.url, {"reason": self.reason.pk}, follow=True)
        self.assertContains(response, "Thank you, your report has been sent to the moderation team.")

    def test_repeated_posts_from_same_client_create_one_report(self):
        for _ in range(5):
            response = self.client.post(self.url, {"reason": self.reason.pk})
            self.assertEqual(response.status_code, 302)
        self.assertEqual(Moderation.objects.count(), 1)

    def test_hidden_reason_is_refused(self):
        response = self.client.post(self.url, {"reason": self.hidden_reason.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Moderation.objects.count(), 0)

    def test_unpublished_petition_is_not_found(self):
        petition = Petition.objects.filter(published=False).first()
        url = reverse("report_petition", args=[petition.id])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, {"reason": self.reason.pk}).status_code, 404)
        self.assertEqual(Moderation.objects.count(), 0)

    def test_moderated_petition_is_not_found(self):
        self.petition.moderated = True
        self.petition.save()
        response = self.client.post(self.url, {"reason": self.reason.pk})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Moderation.objects.count(), 0)

    def test_no_email_is_sent(self):
        self.client.post(self.url, {"reason": self.reason.pk})
        self.assertEqual(len(mail.outbox), 0)

    def test_other_methods_are_not_allowed(self):
        self.assertEqual(self.client.put(self.url).status_code, 405)

    def test_petition_page_has_report_link_and_dialog(self):
        response = self.client.get(reverse("detail", args=[self.petition.id]))
        self.assertContains(response, 'href="{}"'.format(self.url))
        self.assertContains(response, '<dialog id="fp-report"')
        self.assertContains(response, 'data-fp-dialog-open="fp-report"')
        self.assertContains(response, 'data-fp-dialog-close')
        self.assertNotContains(response, 'id="report_modal"')
