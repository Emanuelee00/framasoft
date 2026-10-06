from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from petition.models import Petition


class ExpiryDataMigrationTest(TransactionTestCase):
    """0051 gives the existing petitions one year from the migration day"""

    # flush with TRUNCATE ... CASCADE (an unmanaged model keeps a foreign key in the schema)
    available_apps = ['petition', 'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
                      'django.contrib.sessions']
    before = [('petition', '0050_signature_indexes_gdpr')]
    after = [('petition', '0051_petition_expiry')]

    def tearDown(self):
        # leave the schema as the other tests expect it
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_existing_petitions_get_one_year(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        old_apps = executor.loader.project_state(self.before).apps
        OldUser = old_apps.get_model('auth', 'User')
        OldPytitionUser = old_apps.get_model('petition', 'PytitionUser')
        OldPetition = old_apps.get_model('petition', 'Petition')
        owner = OldPytitionUser.objects.create(user=OldUser.objects.create(username="old"))
        long_ago = timezone.now() - timedelta(days=900)
        pk = OldPetition.objects.create(title="Old", user=owner, creation_date=long_ago,
                                        last_modification_date=long_ago).pk

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.after)
        new_apps = executor.loader.project_state(self.after).apps
        migrated = new_apps.get_model('petition', 'Petition').objects.get(pk=pk)
        self.assertEqual(migrated.expires_at, timezone.localdate() + timedelta(days=365))
        self.assertIsNone(migrated.expiry_reminder_days)


class ExpiryModelTest(TestCase):

    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="owner", password="pass").pytitionuser

    @override_settings(PETITION_DEFAULT_LIFETIME_DAYS=100)
    def test_default_is_creation_day_plus_default_lifetime(self):
        petition = Petition.objects.create(title="P", user=self.owner)
        self.assertEqual(petition.expires_at, timezone.localdate() + timedelta(days=100))
        petition.refresh_from_db()
        self.assertEqual(petition.expires_at, timezone.localdate() + timedelta(days=100))

    def test_is_expired_from_the_deletion_day(self):
        petition = Petition.objects.create(title="P", user=self.owner)
        today = timezone.localdate()
        petition.expires_at = today + timedelta(days=1)
        self.assertFalse(petition.is_expired)
        petition.expires_at = today
        self.assertTrue(petition.is_expired)

    @override_settings(PETITION_MAX_LIFETIME_DAYS=730)
    def test_bounds(self):
        today = timezone.localdate()
        self.assertEqual(Petition.expiry_bounds(), (today + timedelta(days=1), today + timedelta(days=730)))

    def test_new_date_restarts_reminders(self):
        petition = Petition.objects.create(title="P", user=self.owner, expiry_reminder_days=20)
        petition.set_expires_at(petition.expires_at)
        self.assertEqual(petition.expiry_reminder_days, 20)
        petition.set_expires_at(petition.expires_at + timedelta(days=1))
        self.assertIsNone(petition.expiry_reminder_days)


class ExpiryFormTest(TestCase):

    def form(self, value, form_class=None):
        from petition.forms import ExpiryForm
        return (form_class or ExpiryForm)(data={'expires_at': value})

    @override_settings(PETITION_MAX_LIFETIME_DAYS=730)
    def test_bounds(self):
        today = timezone.localdate()
        self.assertFalse(self.form(today.isoformat()).is_valid())
        self.assertIn('expires_at', self.form(today.isoformat()).errors)
        self.assertEqual(self.form(today.isoformat()).errors.as_data()['expires_at'][0].code, 'min_value')
        self.assertTrue(self.form((today + timedelta(days=1)).isoformat()).is_valid())
        self.assertTrue(self.form((today + timedelta(days=730)).isoformat()).is_valid())
        too_late = self.form((today + timedelta(days=731)).isoformat())
        self.assertFalse(too_late.is_valid())
        self.assertEqual(too_late.errors.as_data()['expires_at'][0].code, 'max_value')
        self.assertFalse(self.form('').is_valid())
        self.assertFalse(self.form('not a date').is_valid())

    def test_widget_exposes_bounds(self):
        earliest, latest = Petition.expiry_bounds()
        html = str(self.form(None)['expires_at'])
        self.assertIn('type="date"', html)
        self.assertIn('min="%s"' % earliest.isoformat(), html)
        self.assertIn('max="%s"' % latest.isoformat(), html)

    def test_wizard_step_accepts_empty_date(self):
        from petition.forms import PetitionCreationStep3
        self.assertTrue(PetitionCreationStep3(data={'expires_at': ''}).is_valid())
        self.assertFalse(PetitionCreationStep3(data={'expires_at': timezone.localdate().isoformat()}).is_valid())


class ExpiryViewsTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        from petition.models import Organization, Permission
        User = get_user_model()
        cls.julia = User.objects.create_user(username="julia", password="julia").pytitionuser
        cls.max = User.objects.create_user(username="max", password="max").pytitionuser
        cls.john = User.objects.create_user(username="john", password="john").pytitionuser
        cls.org = Organization.objects.create(name="Org")
        cls.org.members.add(cls.julia)
        cls.org.members.add(cls.max)
        Permission.objects.filter(organization=cls.org, user=cls.max).update(can_modify_petitions=False)

    def setUp(self):
        # the wizard reads the User-Agent header unconditionally
        self.client.defaults['HTTP_USER_AGENT'] = 'test'

    def edit(self, petition, value):
        from django.urls import reverse
        return self.client.post(reverse('edit_petition', args=[petition.id]),
                                {'expiry_form_submitted': 'yes', 'expires_at': value})

    def wizard(self, url, title, expires_at):
        prefix = 'petition_creation_wizard-current_step'
        self.client.post(url, {prefix: 'step1', 'step1-title': title})
        self.client.post(url, {prefix: 'step2', 'step2-message': 'Text'})
        return self.client.post(url, {prefix: 'step3', 'step3-expires_at': expires_at, 'step3-template_id': 0})

    # the spam detectors are out of scope here (and fail with the numpy of some environments)
    @mock.patch('petition.views.is_spam')
    def test_wizard_sets_chosen_or_default_date(self, is_spam):
        from django.urls import reverse
        self.client.login(username="julia", password="julia")
        chosen = timezone.localdate() + timedelta(days=40)
        self.wizard(reverse('user_petition_wizard'), "Chosen", chosen.isoformat())
        self.assertEqual(Petition.objects.get(title="Chosen").expires_at, chosen)
        self.wizard(reverse('user_petition_wizard'), "Default", "")
        self.assertEqual(Petition.objects.get(title="Default").expires_at,
                         timezone.localdate() + timedelta(days=365))
        self.wizard(reverse('org_petition_wizard', args=[self.org.slugname]), "Org", chosen.isoformat())
        self.assertEqual(Petition.objects.get(title="Org", org=self.org).expires_at, chosen)

    def test_wizard_refuses_out_of_range_date(self):
        from django.urls import reverse
        self.client.login(username="julia", password="julia")
        response = self.wizard(reverse('user_petition_wizard'), "Late",
                               (timezone.localdate() + timedelta(days=731)).isoformat())
        self.assertEqual(response.status_code, 200)
        self.assertIn('expires_at', response.context['form'].errors)
        self.assertFalse(Petition.objects.filter(title="Late").exists())

    def test_wizard_initial_date(self):
        from django.urls import reverse
        self.client.login(username="julia", password="julia")
        url = reverse('user_petition_wizard')
        prefix = 'petition_creation_wizard-current_step'
        self.client.post(url, {prefix: 'step1', 'step1-title': "T"})
        response = self.client.post(url, {prefix: 'step2', 'step2-message': 'Text'})
        self.assertEqual(response.context['form']['expires_at'].value(),
                         timezone.localdate() + timedelta(days=365))

    def test_owner_extends(self):
        petition = Petition.objects.create(title="P", user=self.julia, expiry_reminder_days=10)
        self.client.login(username="julia", password="julia")
        new_date = timezone.localdate() + timedelta(days=700)
        response = self.edit(petition, new_date.isoformat())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['expiry_form_submitted'])
        petition.refresh_from_db()
        self.assertEqual(petition.expires_at, new_date)
        self.assertIsNone(petition.expiry_reminder_days)

    def test_edit_page_renders_the_expiry_form(self):
        from django.urls import reverse
        petition = Petition.objects.create(title="P", user=self.julia)
        self.client.login(username="julia", password="julia")
        response = self.client.get(reverse('edit_petition', args=[petition.id]))
        self.assertContains(response, 'id="expiry"')
        self.assertContains(response, 'name="expiry_form_submitted"')
        self.assertContains(response, 'name="expires_at"')
        self.assertContains(response, 'max="{}"'.format(Petition.expiry_bounds()[1].isoformat()))
        response = self.edit(petition, (timezone.localdate() + timedelta(days=731)).isoformat())
        self.assertContains(response, 'class="fp-field-error" id="id_expires_at-error"')

    def test_extension_out_of_range_is_refused(self):
        petition = Petition.objects.create(title="P", user=self.julia)
        before = petition.expires_at
        self.client.login(username="julia", password="julia")
        response = self.edit(petition, (timezone.localdate() + timedelta(days=731)).isoformat())
        self.assertIn('expires_at', response.context['expiry_form'].errors)
        petition.refresh_from_db()
        self.assertEqual(petition.expires_at, before)

    def test_expired_petition_can_still_be_extended_before_purge(self):
        petition = Petition.objects.create(title="P", user=self.julia, expires_at=timezone.localdate())
        self.client.login(username="julia", password="julia")
        from django.urls import reverse
        response = self.client.get(reverse('edit_petition', args=[petition.id]))
        self.assertFalse(response.context['expiry_form'].is_bound)
        self.edit(petition, (timezone.localdate() + timedelta(days=30)).isoformat())
        petition.refresh_from_db()
        self.assertFalse(petition.is_expired)

    def test_org_permissions(self):
        petition = Petition.objects.create(title="P", org=self.org)
        before = petition.expires_at
        new_date = timezone.localdate() + timedelta(days=500)
        for name in ("max", "john"):  # member without can_modify_petitions, non-member
            self.client.login(username=name, password=name)
            self.edit(petition, new_date.isoformat())
            petition.refresh_from_db()
            self.assertEqual(petition.expires_at, before)
        self.client.login(username="julia", password="julia")
        self.edit(petition, new_date.isoformat())
        petition.refresh_from_db()
        self.assertEqual(petition.expires_at, new_date)


class ExpiredPetitionTest(TestCase):
    """Between its deletion date and the purge, a petition no longer accepts signatures"""

    def setUp(self):
        from petition.models import Signature
        owner = get_user_model().objects.create_user(username="owner", password="pass").pytitionuser
        self.petition = Petition.objects.create(title="P", user=owner, published=True,
                                                expires_at=timezone.localdate())
        self.pending = Signature.objects.create(first_name="A", last_name="B", email="a@example.org",
                                                petition=self.petition)

    def test_page_shows_closed_state(self):
        from django.urls import reverse
        for url in (reverse('detail', args=[self.petition.id]), self.petition.url):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['sign_state'], "closed")
            self.assertContains(response, "This petition no longer accepts signatures")
            self.assertNotContains(response, 'name="first_name"')

    def test_sign_is_refused(self):
        from django.urls import reverse
        from petition.models import Signature
        data = {'first_name': 'Alan', 'last_name': 'John', 'email': 'alan@john.org', 'consent': 'on'}
        response = self.client.post(reverse('create_signature', args=[self.petition.id]), data)
        self.assertEqual(response.status_code, 410)
        self.assertContains(response, "reached its deletion date", status_code=410)
        self.assertFalse(Signature.objects.filter(email='alan@john.org').exists())

    def test_confirm_is_refused(self):
        from django.urls import reverse
        url = reverse('confirm', args=[self.petition.id, self.pending.confirmation_hash])
        response = self.client.get(url)
        self.assertEqual(response.context['confirm_state'], "closed")
        self.assertContains(response, "reached its deletion date")
        self.assertNotContains(response, "This confirmation link is not valid")
        self.assertEqual(self.client.post(url).context['confirm_state'], "closed")
        self.pending.refresh_from_db()
        self.assertFalse(self.pending.confirmed)

    def test_open_petition_unchanged(self):
        from django.urls import reverse
        Petition.objects.filter(pk=self.petition.pk).update(expires_at=timezone.localdate() + timedelta(days=1))
        response = self.client.get(reverse('detail', args=[self.petition.id]))
        self.assertNotIn('sign_state', response.context)
        response = self.client.post(reverse('confirm', args=[self.petition.id, self.pending.confirmation_hash]))
        self.assertEqual(response.status_code, 302)


class ExpiryContextTest(TestCase):
    """The deletion date is available where signatories are informed"""

    def setUp(self):
        from petition.models import Signature
        owner = get_user_model().objects.create_user(username="owner", password="pass").pytitionuser
        self.petition = Petition.objects.create(title="P", user=owner, published=True)
        self.signature = Signature.objects.create(first_name="A", last_name="B", email="a@example.org",
                                                  petition=self.petition)

    def test_confirmation_email_context(self):
        from django.test import RequestFactory
        from petition import helpers
        with mock.patch.object(helpers, 'render_to_string', wraps=helpers.render_to_string) as render:
            helpers.send_confirmation_email(RequestFactory().get('/'), self.signature)
        for call in render.call_args_list:
            self.assertEqual(call.args[1]['expires_at'], self.petition.expires_at)

    def test_confirmation_email_shows_the_date(self):
        from django.core import mail
        from django.test import RequestFactory
        from django.utils.formats import date_format
        from petition import helpers
        helpers.send_confirmation_email(RequestFactory().get('/'), self.signature)
        message = mail.outbox[-1]
        expected = "will be deleted on {}.".format(date_format(self.petition.expires_at))
        self.assertIn(expected, message.body)
        self.assertIn(expected, message.alternatives[0][0])

    def test_pages_have_the_petition(self):
        from django.urls import reverse
        from petition.helpers import make_manage_token
        pages = [reverse('detail', args=[self.petition.id]),
                 reverse('confirm', args=[self.petition.id, self.signature.confirmation_hash]),
                 reverse('manage_signature', args=[make_manage_token(self.signature)])]
        for url in pages:
            self.assertEqual(self.client.get(url).context['petition'].expires_at, self.petition.expires_at)


@override_settings(SITE_BASE_URL="https://petitions.example/", PETITION_EXPIRY_REMINDER_DAYS=[30, 20, 10])
class ExpiryReminderTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        from petition.models import Organization, Permission
        User = get_user_model()
        cls.julia = User.objects.create_user(username="julia", password="julia", email="julia@example.org").pytitionuser
        cls.max = User.objects.create_user(username="max", password="max", email="max@example.org").pytitionuser
        cls.ann = User.objects.create_user(username="ann", password="ann", email="ann@example.org").pytitionuser
        cls.bob = User.objects.create_user(username="bob", password="bob", email="bob@example.org").pytitionuser
        cls.gone = User.objects.create_user(username="gone", password="gone", email="gone@example.org",
                                            is_active=False).pytitionuser
        cls.org = Organization.objects.create(name="Org")
        for member in (cls.julia, cls.max, cls.ann, cls.bob, cls.gone):
            cls.org.members.add(member)
        perms = Permission.objects.filter(organization=cls.org)
        perms.update(can_modify_petitions=False, can_view_signatures=False)
        perms.filter(user=cls.julia).update(can_modify_petitions=True)
        perms.filter(user=cls.max).update(can_view_signatures=True)
        perms.filter(user=cls.gone).update(can_modify_petitions=True)

    def in_days(self, days):
        return timezone.localdate() + timedelta(days=days)

    def run_command(self, *args):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('send_expiry_reminders', *args, stdout=out)
        return out.getvalue()

    def test_user_reminder_content_and_idempotence(self):
        from django.core import mail
        from petition.models import Signature
        petition = Petition.objects.create(title="Save <b>the</b> bees", user=self.julia, expires_at=self.in_days(30))
        Signature.objects.create(first_name="A", last_name="B", email="a@example.org", petition=petition,
                                 confirmed=True)
        Signature.objects.create(first_name="C", last_name="D", email="c@example.org", petition=petition)
        self.assertIn("expiry_reminders=1", self.run_command())
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["julia@example.org"])
        self.assertIn("Save the bees", message.subject)
        self.assertIn("its 1 signature will be permanently deleted", message.body)
        self.assertIn("https://petitions.example/petition/%d/get_csv_confirmed_signature" % petition.id, message.body)
        self.assertIn("https://petitions.example/petition/%d/edit#expiry" % petition.id, message.body)
        self.assertIn("because you created this petition", message.body)
        self.assertNotIn("<b>", message.body)
        self.assertEqual(message.alternatives[0][1], "text/html")
        petition.refresh_from_db()
        self.assertEqual(petition.expiry_reminder_days, 30)
        # same day, next days before the next threshold: nothing more
        self.assertIn("expiry_reminders=0", self.run_command())
        Petition.objects.filter(pk=petition.pk).update(expires_at=self.in_days(21))
        petition.refresh_from_db()
        self.assertIn("expiry_reminders=0", self.run_command())
        Petition.objects.filter(pk=petition.pk).update(expires_at=self.in_days(20))
        self.assertIn("expiry_reminders=1", self.run_command())
        Petition.objects.filter(pk=petition.pk).update(expires_at=self.in_days(10))
        self.assertIn("expiry_reminders=1", self.run_command())
        self.assertIn("expiry_reminders=0", self.run_command())
        self.assertEqual(len(mail.outbox), 3)

    def test_late_run_sends_only_the_latest_reminder(self):
        from django.core import mail
        petition = Petition.objects.create(title="P", user=self.julia, expires_at=self.in_days(15))
        self.run_command()
        self.assertEqual(len(mail.outbox), 1)
        petition.refresh_from_db()
        self.assertEqual(petition.expiry_reminder_days, 20)

    def test_out_of_window_and_binned_petitions(self):
        from django.core import mail
        Petition.objects.create(title="Far", user=self.julia, expires_at=self.in_days(31))
        Petition.objects.create(title="Today", user=self.julia, expires_at=self.in_days(0))
        Petition.objects.create(title="Bin", user=self.julia, expires_at=self.in_days(10), in_bin_date=timezone.now())
        self.assertIn("expiry_reminders=0", self.run_command())
        self.assertEqual(len(mail.outbox), 0)

    def test_extension_restarts_reminders(self):
        from django.core import mail
        petition = Petition.objects.create(title="P", user=self.julia, expires_at=self.in_days(10))
        self.run_command()
        petition.refresh_from_db()
        petition.set_expires_at(self.in_days(30))
        petition.save()
        self.run_command()
        self.assertEqual(len(mail.outbox), 2)

    def test_organization_recipients(self):
        from django.core import mail
        Petition.objects.create(title="P", org=self.org, expires_at=self.in_days(30))
        self.run_command()
        # julia may extend, max may export; ann and bob may do neither; gone is inactive
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ["julia@example.org", "max@example.org"])
        self.assertTrue(all(len(m.to) == 1 and not m.cc and not m.bcc for m in mail.outbox))
        self.assertIn("manage the petitions of Org", mail.outbox[0].body)

    def test_dry_run(self):
        from django.core import mail
        petition = Petition.objects.create(title="P", user=self.julia, expires_at=self.in_days(30))
        self.assertIn("expiry_reminders=1 (dry-run)", self.run_command('--dry-run'))
        self.assertEqual(len(mail.outbox), 0)
        petition.refresh_from_db()
        self.assertIsNone(petition.expiry_reminder_days)

    @override_settings(SITE_BASE_URL="")
    def test_no_base_url(self):
        from django.core.management.base import CommandError
        Petition.objects.create(title="P", user=self.julia, expires_at=self.in_days(30))
        with self.assertRaises(CommandError):
            self.run_command()

    def test_failed_send_is_retried(self):
        from django.core import mail
        petition = Petition.objects.create(title="P", user=self.julia, expires_at=self.in_days(30))
        # (the logger is mocked: test_Commands disables logging for the whole test run)
        with mock.patch('petition.expiry.send_reminder', side_effect=OSError), \
                mock.patch('petition.expiry.logger') as logger:
            self.assertIn("expiry_reminders=0", self.run_command())
        logger.exception.assert_called_once()
        petition.refresh_from_db()
        self.assertIsNone(petition.expiry_reminder_days)
        self.run_command()
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(LANGUAGE_CODE='fr')
    def test_french(self):
        from django.core import mail
        Petition.objects.create(title="P", user=self.julia, expires_at=self.in_days(30))
        self.run_command()
        self.assertIn("sera supprimée le", mail.outbox[0].subject)
        self.assertIn("Bonjour", mail.outbox[0].body)


@override_settings(SITE_BASE_URL="https://petitions.example", PETITION_EXPIRY_REMINDER_DAYS=[30, 20, 10])
class ExpiredPurgeTest(TestCase):

    def setUp(self):
        from petition.models import Signature, Moderation, Monitoring, ModerationReason, SlugModel
        self.owner = get_user_model().objects.create_user(username="owner", password="pass",
                                                          email="o@example.org").pytitionuser
        self.expired = Petition.objects.create(title="Expired", user=self.owner, published=True,
                                               expires_at=timezone.localdate())
        self.alive = Petition.objects.create(title="Alive", user=self.owner, published=True)
        for i in range(5):
            Signature.objects.create(first_name="A", last_name="B", email="e%d@example.org" % i,
                                     petition=self.expired, confirmed=True)
        Signature.objects.create(first_name="A", last_name="B", email="alive@example.org", petition=self.alive)
        reason = ModerationReason.objects.create(msg="reason")
        Moderation.objects.create(petition=self.expired, reason=reason)
        Monitoring.objects.create(petition=self.expired)
        self.assertTrue(SlugModel.objects.filter(petition=self.expired).exists())

    def purge(self, *args):
        from io import StringIO
        from django.core.management import call_command
        out, err = StringIO(), StringIO()
        call_command('purge_personal_data', *args, stdout=out, stderr=err)
        return out.getvalue(), err.getvalue()

    def test_dry_run(self):
        out, _ = self.purge('--dry-run')
        self.assertIn("expired_petitions=1 expired_signatures=5 (dry-run)", out)
        self.assertTrue(Petition.objects.filter(pk=self.expired.pk).exists())

    def test_expired_petition_and_related_rows_are_deleted(self):
        from petition.models import Signature, Moderation, Monitoring, SlugModel
        expired_pk = self.expired.pk
        out, _ = self.purge('--batch-size', '2')
        self.assertIn("expired_petitions=1 expired_signatures=5", out)
        self.assertFalse(Petition.objects.filter(pk=expired_pk).exists())
        self.assertFalse(Signature.objects.filter(petition_id=expired_pk).exists())
        self.assertFalse(SlugModel.objects.filter(petition_id=expired_pk).exists())
        self.assertFalse(Moderation.objects.filter(petition_id=expired_pk).exists())
        self.assertFalse(Monitoring.objects.filter(petition_id=expired_pk).exists())
        self.assertTrue(Petition.objects.filter(pk=self.alive.pk).exists())
        self.assertTrue(Signature.objects.filter(petition=self.alive).exists())
        out, _ = self.purge()
        self.assertIn("expired_petitions=0 expired_signatures=0", out)

    def test_signatures_are_deleted_in_batches(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            self.purge('--batch-size', '2')
        deletes = [q['sql'] for q in ctx.captured_queries
                   if q['sql'].startswith('DELETE FROM "petition_signature"')]
        # 2 + 2 + 1, then the (empty) cascade of the petition itself
        self.assertEqual(len(deletes), 4)

    def test_ip_hashes_are_blanked_in_batches(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from petition.models import Signature
        Signature.objects.filter(petition=self.alive).delete()
        for i in range(5):
            Signature.objects.create(first_name="A", last_name="B", email="ip%d@example.org" % i,
                                     petition=self.alive, confirmed=True, ipaddress="h%d" % i)
        Signature.objects.filter(petition=self.alive).update(date=timezone.now() - timedelta(days=30))
        with CaptureQueriesContext(connection) as ctx:
            out, _ = self.purge('--batch-size', '2')
        self.assertIn("signature_ip_hashes=5", out)
        self.assertFalse(Signature.objects.filter(ipaddress__isnull=False).exists())
        updates = [q for q in ctx.captured_queries if q['sql'].startswith('UPDATE "petition_signature"')]
        self.assertEqual(len(updates), 3)

    def test_extended_petition_is_kept(self):
        self.expired.set_expires_at(timezone.localdate() + timedelta(days=1))
        self.expired.save()
        out, _ = self.purge()
        self.assertIn("expired_petitions=0", out)
        self.assertTrue(Petition.objects.filter(pk=self.expired.pk).exists())

    def test_reminders_are_sent_by_the_purge(self):
        from django.core import mail
        Petition.objects.filter(pk=self.alive.pk).update(expires_at=timezone.localdate() + timedelta(days=10))
        out, _ = self.purge()
        self.assertIn("expiry_reminders=1", out)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(SITE_BASE_URL="")
    def test_nothing_deleted_without_base_url(self):
        out, err = self.purge()
        self.assertIn("SITE_BASE_URL", err)
        self.assertNotIn("expired_petitions", out)
        self.assertTrue(Petition.objects.filter(pk=self.expired.pk).exists())

    def test_unused_media_files_are_deleted(self):
        import tempfile
        from django.core.files.base import ContentFile
        from django.core.files.storage import FileSystemStorage
        from petition.models import PetitionTemplate
        with tempfile.TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            storage = FileSystemStorage()
            own, shared, in_template = (storage.save("owner/%s.png" % n, ContentFile(b"x"))
                                        for n in ("own", "shared", "template"))
            url = storage.url
            Petition.objects.filter(pk=self.expired.pk).update(
                twitter_image=url(own),
                text='<p><img src="%s"> <img src="https://petitions.example%s"></p>' % (url(shared), url(in_template)))
            Petition.objects.filter(pk=self.alive.pk).update(side_text='<img src="%s">' % url(shared))
            PetitionTemplate.objects.create(name="T", user=self.owner, text='<img src="%s">' % url(in_template))
            self.purge()
            self.assertFalse(storage.exists(own))
            self.assertTrue(storage.exists(shared))
            self.assertTrue(storage.exists(in_template))

    def test_media_outside_media_root_is_never_deleted(self):
        from petition.expiry import delete_unused_media
        from django.conf import settings
        with mock.patch('petition.expiry.logger') as logger:
            self.assertEqual(delete_unused_media({settings.MEDIA_URL + "../../etc/passwd"}), 0)
        logger.warning.assert_called_once()


class PrivacyNoticeExpiryTest(TestCase):

    @override_settings(PETITION_DEFAULT_LIFETIME_DAYS=365, PETITION_MAX_LIFETIME_DAYS=730)
    def test_retention_of_petitions_is_explained(self):
        from django.urls import reverse
        response = self.client.get(reverse('privacy_notice'))
        self.assertContains(response, "by default 365 days after its creation")
        self.assertContains(response, "never more than 730 days ahead")
        self.assertContains(response, '<div class="fp-page-header">')
        self.assertContains(response, '<div class="fp-prose">')

    def test_french(self):
        from django.urls import reverse
        response = self.client.get(reverse('privacy_notice'), HTTP_ACCEPT_LANGUAGE='fr')
        self.assertContains(response, "définitivement supprimées du site")


class ConfirmQueriesTest(TestCase):
    """confirm() reads the signature and its petition once"""

    def setUp(self):
        from petition.models import Signature
        owner = get_user_model().objects.create_user(username="owner", password="pass").pytitionuser
        self.petition = Petition.objects.create(title="P", user=owner, published=True)
        self.signature = Signature.objects.create(first_name="A", last_name="B", email="a@example.org",
                                                  petition=self.petition)

    def url(self, confirmation_hash):
        from django.urls import reverse
        return reverse('confirm', args=[self.petition.id, confirmation_hash])

    def test_get_is_one_query(self):
        with self.assertNumQueries(1):
            response = self.client.get(self.url(self.signature.confirmation_hash))
        self.assertEqual(response.context['confirm_state'], "pending")

    def test_post_reads_signature_and_petition_once(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            self.client.post(self.url(self.signature.confirmation_hash))
        selects = [q['sql'] for q in ctx.captured_queries]
        self.assertEqual(sum(s.startswith('SELECT "petition_signature"') for s in selects), 1)
        self.assertFalse(any(s.startswith('SELECT "petition_petition"') for s in selects))
        self.signature.refresh_from_db()
        self.assertTrue(self.signature.confirmed)

    def test_unknown_hash_still_finds_the_petition(self):
        response = self.client.get(self.url("unknown"))
        self.assertEqual(response.context['confirm_state'], "invalid_link")
        self.assertEqual(response.context['petition'], self.petition)
        from django.urls import reverse
        self.assertEqual(self.client.get(reverse('confirm', args=[999999, "x"])).status_code, 404)
