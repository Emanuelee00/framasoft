import datetime
from types import SimpleNamespace
from unittest import mock

from django import forms
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from petition.models import Organization, Permission, Petition, PytitionUser
from petition.templatetags.fp_dashboard import fp_days_left, fp_expires_soon


def make_user(name):
    get_user_model().objects.create_user(name, password=name)
    return PytitionUser.objects.get(user__username=name)


class ExpiryHelpersTest(TestCase):
    """Days left before Petition.expires_at and the 'expires soon' threshold (30 days)"""

    def test_days_left(self):
        today = timezone.localdate()
        self.assertEqual(fp_days_left(today + datetime.timedelta(days=12)), 12)
        self.assertEqual(fp_days_left(timezone.now() + datetime.timedelta(days=3)), 3)
        self.assertIsNone(fp_days_left(None))
        self.assertIsNone(fp_days_left(""))

    def test_expires_soon(self):
        today = timezone.localdate()
        self.assertTrue(fp_expires_soon(today + datetime.timedelta(days=30)))
        self.assertTrue(fp_expires_soon(today))
        self.assertFalse(fp_expires_soon(today + datetime.timedelta(days=31)))
        self.assertFalse(fp_expires_soon(None))

    def test_badge(self):
        soon = SimpleNamespace(expires_at=timezone.localdate() + datetime.timedelta(days=12))
        later = SimpleNamespace(expires_at=timezone.localdate() + datetime.timedelta(days=200))
        self.assertIn("Expires in 12 days", render_to_string("petition/expiry_badge.html", {"petition": soon}))
        self.assertNotIn("Expires", render_to_string("petition/expiry_badge.html", {"petition": later}))
        self.assertNotIn("Expires", render_to_string("petition/expiry_badge.html", {"petition": SimpleNamespace()}))


class ExpiryFieldTest(TestCase):
    """petition/expiry_field.html renders any form field named expires_at (contract with the GDPR branch)"""

    class Form(forms.Form):
        expires_at = forms.DateField(label="Deletion date", widget=forms.DateInput(attrs={"type": "date", "max": "2028-10-06"}))

    def test_field_explains_and_offers_extension(self):
        form = self.Form(data={"expires_at": "2027-10-06"})
        html = render_to_string("petition/expiry_field.html", {"field": form["expires_at"]})
        self.assertIn('<label class="fp-label" for="id_expires_at">Deletion date</label>', html)
        self.assertIn('30, 20 and 10 days before', html)
        self.assertIn('aria-describedby="id_expires_at-explain"', html)
        self.assertIn('data-fp-extend="id_expires_at"', html)
        self.assertIn('max="2028-10-06"', html)

    def test_errors_are_linked(self):
        form = self.Form(data={"expires_at": "not a date"})
        html = render_to_string("petition/expiry_field.html", {"field": form["expires_at"]})
        self.assertIn('aria-invalid="true"', html)
        self.assertIn('id="id_expires_at-error"', html)


class DashboardTest(TestCase):
    """Dashboard rows: status, actions as POST forms, no inline behaviour"""

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user("camille")
        cls.draft = Petition.objects.create(title="Draft one", user=cls.user)
        cls.published = Petition.objects.create(title="Published one", user=cls.user, published=True)
        Petition.objects.create(title="Old one", user=cls.user, in_bin_date=timezone.now())

    def setUp(self):
        self.client.login(username="camille", password="camille")

    def test_rows_and_actions(self):
        html = self.client.get(reverse("user_dashboard")).content.decode()
        self.assertIn('id="petition-{}"'.format(self.draft.id), html)
        self.assertIn("Draft, not visible", html)
        self.assertIn('action="{}" data-fp-async'.format(reverse("petition_publish", args=[self.draft.id])), html)
        self.assertIn('action="{}" data-fp-async'.format(reverse("petition_unpublish", args=[self.published.id])), html)
        self.assertIn('data-fp-dialog-open="bin-{}"'.format(self.draft.id), html)
        self.assertIn('js/fp-dashboard.js', html)
        self.assertNotIn('onclick=', html)
        self.assertNotIn('Old one', html)

    def test_bin(self):
        html = self.client.get(reverse("user_bin")).content.decode()
        self.assertIn('Old one', html)
        self.assertIn('Delete permanently', html)
        self.assertNotIn('Draft one', html)

    def test_publish_by_post(self):
        response = self.client.post(reverse("petition_publish", args=[self.draft.id]))
        self.assertEqual(response.status_code, 200)
        self.draft.refresh_from_db()
        self.assertTrue(self.draft.published)

    def test_empty_state(self):
        make_user("lea")
        self.client.login(username="lea", password="lea")
        html = self.client.get(reverse("user_dashboard")).content.decode()
        self.assertIn('class="fp-empty ', html)
        self.assertIn(reverse("user_petition_wizard"), html)


class OrgBinTest(TestCase):
    """The organization bin knows the member's permissions (restore and delete buttons)"""

    def test_restore_button(self):
        user = make_user("yanis")
        org = Organization.objects.create(name="Collectif")
        org.members.add(user)
        Permission.objects.get(organization=org, user=user).set_all(True)
        Petition.objects.create(title="Binned", org=org, in_bin_date=timezone.now())
        self.client.login(username="yanis", password="yanis")
        html = self.client.get(reverse("org_bin", args=[org.slugname])).content.decode()
        self.assertIn("Restore", html)
        self.assertIn("Delete permanently", html)


@mock.patch("petition.views.is_spam", lambda petition, user: None)
class WizardTest(TestCase):
    """Three steps, then two explicit submits: settings or dashboard"""

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user("julia")

    def setUp(self):
        self.client.login(username="julia", password="julia")
        self.url = reverse("user_petition_wizard")
        response = self.client.get(self.url)
        self.prefix = response.context["wizard"]["management_form"].prefix
        self.assertContains(response, 'class="fp-stepper"')
        self.assertContains(response, 'aria-current="step"')

    def post(self, step, data):
        data = dict(data, **{self.prefix + "-current_step": step})
        return self.client.post(self.url, data, HTTP_USER_AGENT="tests")

    def run_wizard(self, redirect_value):
        self.post("step1", {"step1-title": "Clean water for everyone"})
        self.post("step2", {"step2-message": "<p>We ask for fountains.</p>"})
        return self.post("step3", {"step3-use_template": "", "step3-template_id": "", "redirect": redirect_value})

    def test_finish_the_settings(self):
        response = self.run_wizard("1")
        petition = Petition.objects.get(title="Clean water for everyone")
        self.assertRedirects(response, reverse("edit_petition", args=[petition.id]), fetch_redirect_response=False)
        self.assertFalse(petition.published)

    def test_go_to_dashboard(self):
        response = self.run_wizard("0")
        self.assertRedirects(response, reverse("user_dashboard"), fetch_redirect_response=False)

    def test_title_is_limited(self):
        response = self.post("step1", {"step1-title": "x" * 81})
        self.assertContains(response, 'class="fp-error-summary"')
        self.assertFalse(Petition.objects.exists())


class EditPageTest(TestCase):
    """Tabs, status cards and forms posting back to their tab"""

    def test_tabs_and_status(self):
        user = make_user("max")
        petition = Petition.objects.create(title="Edit me", user=user)
        self.client.login(username="max", password="max")
        html = self.client.get(reverse("edit_petition", args=[petition.id])).content.decode()
        self.assertIn('data-fp-tabs', html)
        for panel in ("tab_content_form", "tab_social_network_form", "tab_email_form", "tab_preview"):
            self.assertIn('id="{}"'.format(panel), html)
        self.assertIn('action="#tab_email_form"', html)
        self.assertIn('action="{}" data-fp-async'.format(reverse("petition_publish", args=[petition.id])), html)
        self.assertIn('js/fp-editor.js', html)
        self.assertNotIn('<style>', html)
