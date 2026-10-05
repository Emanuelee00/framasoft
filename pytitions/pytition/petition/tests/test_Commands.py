import logging
from datetime import timedelta
from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import User
from django.utils import timezone

from petition.models import Organization, Permission, Petition, Signature

logging.disable(logging.CRITICAL)


class CommandTestCase(TestCase):
    def test_gen_orga_command(self):
        self.assertEqual(Organization.objects.count(), 0)

        call_command('gen_orga', 'test-org')
        self.assertEqual(Organization.objects.count(), 1)

        call_command('gen_orga', 'test-org')
        self.assertEqual(Organization.objects.count(), 1)

    def test_gen_user_command(self):
        self.assertEqual(User.objects.count(), 0)

        call_command('gen_user', 'user', 'password')
        self.assertEqual(User.objects.count(), 1)
        self.assertTrue(User.objects.first().check_password('password'))

        call_command('gen_user', 'user', 'password2', '--first-name', 'User')
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.first().first_name, 'User')
        self.assertTrue(User.objects.first().check_password('password2'))

    def test_join_org_command(self):
        org = Organization.objects.create(name="org")
        User.objects.create_user(username="user", password="pass")
        self.assertEqual(Permission.objects.count(), 0)
        self.assertEqual(org.members.count(), 0)

        call_command('join_org', 'user', 'org')
        self.assertEqual(Permission.objects.count(), 1)
        self.assertEqual(org.members.count(), 1)

        call_command('join_org', 'user2', 'org')
        self.assertEqual(Permission.objects.count(), 1)
        self.assertEqual(org.members.count(), 1)

        call_command('join_org', 'user', 'org2')
        self.assertEqual(Permission.objects.count(), 1)
        self.assertEqual(org.members.count(), 1)

    def test_gen_pet_command(self):
        Organization.objects.create(name="org")
        User.objects.create_user(username="user", password="pass")
        self.assertEqual(Petition.objects.count(), 0)

        call_command('gen_pet', '--user', 'user')
        self.assertEqual(Petition.objects.count(), 1)

        call_command('gen_pet', '--orga', 'org', '--number', '9')
        self.assertEqual(Petition.objects.count(), 10)

    def test_gen_sig_command(self):
        org = Organization.objects.create(name="org")
        user = User.objects.create_user(username="user", password="pass")
        pet = Petition.objects.create(title="Test", user=user.pytitionuser)
        self.assertEqual(Signature.objects.count(), 0)

        call_command('gen_sig', pet.id)
        self.assertEqual(Signature.objects.count(), 1)

        call_command('gen_sig', '2')
        self.assertEqual(Signature.objects.count(), 1)

        call_command('gen_sig', 'Test')
        self.assertEqual(Signature.objects.count(), 2)

        Petition.objects.create(title="Test", org=org)
        call_command('gen_sig', 'Test')
        self.assertEqual(Signature.objects.count(), 2)

        call_command('gen_sig', pet.id, '--number', '8')
        self.assertEqual(Signature.objects.count(), 10)

    def test_cron_command_unschedules_checked_petitions(self):
        user = User.objects.create_user(username="user", password="pass")
        pet = Petition.objects.create(title="Test", user=user.pytitionuser, published=True,
                                      cron_to_schedule=True)
        call_command('cron')
        pet.refresh_from_db()
        self.assertFalse(pet.cron_to_schedule)
    def test_purge_personal_data_command(self):
        user = User.objects.create_user(username="user", password="pass")
        old_pet = Petition.objects.create(title="Old", user=user.pytitionuser, ipaddr="1.2.3.4", user_agent="UA")
        new_pet = Petition.objects.create(title="New", user=user.pytitionuser, ipaddr="5.6.7.8", user_agent="UA")
        Petition.objects.filter(pk=old_pet.pk).update(creation_date=timezone.now() - timedelta(days=31))
        s_old = Signature.objects.create(first_name="A", last_name="B", email="a@b.org", petition=new_pet)
        s_new = Signature.objects.create(first_name="C", last_name="D", email="c@d.org", petition=new_pet)
        s_conf = Signature.objects.create(first_name="E", last_name="F", email="e@f.org", petition=new_pet,
                                          confirmed=True, ipaddress="x")
        s_conf_new = Signature.objects.create(first_name="G", last_name="H", email="g@h.org", petition=new_pet,
                                              confirmed=True, ipaddress="y")
        Signature.objects.filter(pk__in=[s_old.pk, s_conf.pk]).update(date=timezone.now() - timedelta(days=8))

        out = StringIO()
        call_command('purge_personal_data', '--dry-run', stdout=out)
        self.assertIn("unconfirmed_signatures=1 signature_ip_hashes=1 creator_ip_ua=1 (dry-run)", out.getvalue())
        self.assertEqual(Signature.objects.count(), 4)
        self.assertEqual(Signature.objects.get(pk=s_conf.pk).ipaddress, "x")

        call_command('purge_personal_data', stdout=StringIO())
        self.assertFalse(Signature.objects.filter(pk=s_old.pk).exists())
        self.assertTrue(Signature.objects.filter(pk=s_new.pk).exists())
        self.assertIsNone(Signature.objects.get(pk=s_conf.pk).ipaddress)
        self.assertTrue(Signature.objects.get(pk=s_conf.pk).confirmed)
        self.assertEqual(Signature.objects.get(pk=s_conf_new.pk).ipaddress, "y")
        old_pet.refresh_from_db()
        new_pet.refresh_from_db()
        self.assertIsNone(old_pet.ipaddr)
        self.assertIsNone(old_pet.user_agent)
        self.assertEqual(new_pet.ipaddr, "5.6.7.8")

        out = StringIO()
        call_command('purge_personal_data', stdout=out)  # idempotent
        self.assertIn("unconfirmed_signatures=0 signature_ip_hashes=0 creator_ip_ua=0", out.getvalue())
