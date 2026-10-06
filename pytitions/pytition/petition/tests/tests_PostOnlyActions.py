import itertools

from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from petition.models import Organization, Petition, PetitionTemplate, PytitionUser, Signature, SlugModel
from .utils import add_default_data


CSRF_SECRET = "a" * 32
_titles = itertools.count()


def pu(name):
    return PytitionUser.objects.get(user__username=name)


def title():
    return "Action target %d" % next(_titles)


def julia_petition(**kwargs):
    return Petition.objects.create(title=title(), user=pu("julia"), published=True, **kwargs)


# Each case builds its own state and returns (url, check) where check(done) asserts
# that the action happened (done=True) or that nothing changed (done=False).

def case_petition_in_bin():
    p = julia_petition()
    def check(test, done):
        p.refresh_from_db()
        test.assertEqual(p.in_bin_date is not None, done)
    return reverse("petition_in_bin", args=[p.id]), check


def case_petition_restore():
    p = julia_petition(in_bin_date=timezone.now())
    def check(test, done):
        p.refresh_from_db()
        test.assertEqual(p.in_bin_date is None, done)
    return reverse("petition_restore", args=[p.id]), check


def case_petition_delete():
    p = julia_petition()
    def check(test, done):
        test.assertEqual(Petition.objects.filter(pk=p.pk).exists(), not done)
    return reverse("petition_delete", args=[p.id]), check


def case_petition_publish():
    p = Petition.objects.create(title=title(), user=pu("julia"), published=False)
    def check(test, done):
        p.refresh_from_db()
        test.assertEqual(p.published, done)
    return reverse("petition_publish", args=[p.id]), check


def case_petition_unpublish():
    p = julia_petition()
    def check(test, done):
        p.refresh_from_db()
        test.assertEqual(p.published, not done)
    return reverse("petition_unpublish", args=[p.id]), check


def case_del_slug():
    p = julia_petition()
    slug = p.slugmodel_set.first()
    def check(test, done):
        test.assertEqual(SlugModel.objects.filter(pk=slug.pk).exists(), not done)
    return reverse("del_slug", args=[p.id]) + "?slugid=%d" % slug.id, check


def case_leave_org():
    org = Organization.objects.get(name="Alternatiba")
    def check(test, done):
        test.assertEqual(org.members.filter(pk=pu("julia").pk).exists(), not done)
    return reverse("leave_org", args=[org.slugname]), check


def case_org_add_user():
    org = Organization.objects.get(name="RAP")
    def check(test, done):
        test.assertEqual(pu("sarah").invitations.filter(pk=org.pk).exists(), done)
    return reverse("org_add_user", args=[org.slugname]) + "?user=sarah", check


def case_invite_accept():
    org = Organization.objects.get(name="Attac")
    pu("julia").invitations.add(org)
    def check(test, done):
        test.assertEqual(org.members.filter(pk=pu("julia").pk).exists(), done)
    return reverse("invite_accept", args=[org.slugname]), check


def case_invite_dismiss():
    org = Organization.objects.get(name="Attac")
    pu("julia").invitations.add(org)
    def check(test, done):
        test.assertEqual(pu("julia").invitations.filter(pk=org.pk).exists(), not done)
    return reverse("invite_dismiss", args=[org.slugname]), check


def case_org_delete_member():
    org = Organization.objects.get(name="Les Amis de la Terre")
    def check(test, done):
        test.assertEqual(org.members.filter(pk=pu("max").pk).exists(), not done)
    return reverse("org_delete_member", args=[org.slugname]) + "?member=max", check


def case_template_delete():
    t = PetitionTemplate.objects.create(name="To delete", user=pu("julia"))
    def check(test, done):
        test.assertEqual(PetitionTemplate.objects.filter(pk=t.pk).exists(), not done)
    return reverse("template_delete", args=[t.id]), check


def case_template_fav_toggle():
    t = PetitionTemplate.objects.create(name="Favourite", user=pu("julia"))
    def check(test, done):
        test.assertEqual(pu("julia").default_template_id == t.pk, done)
    return reverse("template_fav_toggle", args=[t.id]), check


def case_resend_confirmation_email():
    s = Signature.objects.create(first_name="Alan", last_name="John", email="alan@john.org",
                                 petition=julia_petition())
    mail.outbox = []
    def check(test, done):
        test.assertEqual(len(mail.outbox), 1 if done else 0)
    return reverse("resend_confirmation_email", args=[s.id]), check


# (case, user allowed to act)
CASES = [
    (case_petition_in_bin, "julia"),
    (case_petition_restore, "julia"),
    (case_petition_delete, "julia"),
    (case_petition_publish, "julia"),
    (case_petition_unpublish, "julia"),
    (case_del_slug, "julia"),
    (case_leave_org, "julia"),
    (case_org_add_user, "julia"),
    (case_invite_accept, "julia"),
    (case_invite_dismiss, "julia"),
    (case_org_delete_member, "julia"),
    (case_template_delete, "julia"),
    (case_template_fav_toggle, "julia"),
    (case_resend_confirmation_email, "admin"),
]


class PostOnlyActionsTest(TestCase):
    """Every view that changes data needs a logged in user, POST and a valid CSRF token"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def csrf_client(self, username=None):
        client = Client(enforce_csrf_checks=True)
        if username:
            client.login(username=username, password=username)
        return client

    def post_with_token(self, client, url):
        client.cookies["csrftoken"] = CSRF_SECRET
        return client.post(url, HTTP_X_CSRFTOKEN=CSRF_SECRET)

    def test_anonymous_is_sent_to_login(self):
        for case, _user in CASES:
            with self.subTest(case.__name__):
                url, check = case()
                for method in ("get", "post"):
                    response = getattr(self.client, method)(url)
                    self.assertEqual(response.status_code, 302)
                    self.assertTrue(response["Location"].startswith(reverse("login") + "?next="))
                check(self, False)

    def test_get_is_not_allowed(self):
        for case, user in CASES:
            with self.subTest(case.__name__):
                url, check = case()
                self.client.login(username=user, password=user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 405)
                check(self, False)

    def test_post_without_csrf_token_is_forbidden(self):
        for case, user in CASES:
            with self.subTest(case.__name__):
                url, check = case()
                response = self.csrf_client(user).post(url)
                self.assertEqual(response.status_code, 403)
                check(self, False)

    def test_post_with_csrf_token_acts(self):
        for case, user in CASES:
            with self.subTest(case.__name__):
                url, check = case()
                response = self.post_with_token(self.csrf_client(user), url)
                self.assertIn(response.status_code, (200, 302))
                check(self, True)


class BinActionsPermissionTest(TestCase):
    """petition_in_bin and petition_restore keep refusing people who do not own the petition"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def test_in_bin_refused_to_another_user(self):
        p = julia_petition()
        self.client.login(username="max", password="max")
        response = self.client.post(reverse("petition_in_bin", args=[p.id]))
        self.assertEqual(response.status_code, 403)
        p.refresh_from_db()
        self.assertIsNone(p.in_bin_date)
        self.assertTrue(p.published)

    def test_in_bin_refused_without_org_permission(self):
        org = Organization.objects.get(name="Les Amis de la Terre")
        p = Petition.objects.create(title=title(), org=org, published=True)
        self.client.login(username="max", password="max")  # member without can_delete_petitions
        response = self.client.post(reverse("petition_in_bin", args=[p.id]))
        self.assertEqual(response.status_code, 403)
        p.refresh_from_db()
        self.assertIsNone(p.in_bin_date)

    def test_in_bin_unpublishes(self):
        p = julia_petition()
        self.client.login(username="julia", password="julia")
        response = self.client.post(reverse("petition_in_bin", args=[p.id]))
        self.assertEqual(response.status_code, 200)
        p.refresh_from_db()
        self.assertIsNotNone(p.in_bin_date)
        self.assertFalse(p.published)

    def test_restore_refused_to_another_user(self):
        p = julia_petition(in_bin_date=timezone.now())
        self.client.login(username="max", password="max")
        response = self.client.post(reverse("petition_restore", args=[p.id]))
        self.assertRedirects(response, reverse("user_dashboard"))
        p.refresh_from_db()
        self.assertIsNotNone(p.in_bin_date)

    def test_restore_refused_without_org_permission(self):
        org = Organization.objects.get(name="Les Amis de la Terre")
        p = Petition.objects.create(title=title(), org=org, in_bin_date=timezone.now())
        self.client.login(username="sarah", password="sarah")  # not a member
        response = self.client.post(reverse("petition_restore", args=[p.id]))
        self.assertRedirects(response, reverse("org_bin", args=[org.slugname]), fetch_redirect_response=False)
        p.refresh_from_db()
        self.assertIsNotNone(p.in_bin_date)

    def test_restore_goes_back_to_the_bin_page(self):
        p = julia_petition(in_bin_date=timezone.now())
        self.client.login(username="julia", password="julia")
        response = self.client.post(reverse("petition_restore", args=[p.id]), HTTP_REFERER=reverse("user_bin"))
        self.assertRedirects(response, reverse("user_bin"))
        p.refresh_from_db()
        self.assertIsNone(p.in_bin_date)


class ResendConfirmationAdminFormTest(TestCase):
    """The admin button re-sending a confirmation email posts with a CSRF token"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def test_admin_form_is_post(self):
        s = Signature.objects.create(first_name="Alan", last_name="John", email="alan@john.org",
                                     petition=julia_petition())
        self.client.login(username="admin", password="admin")
        response = self.client.get(reverse("admin:petition_signature_change", args=[s.id]))
        self.assertContains(response, 'method="post" action="%s"' % reverse("resend_confirmation_email", args=[s.id]))
