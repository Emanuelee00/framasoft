from django.test import TestCase
from django.urls import reverse

from .utils import add_default_data

from petition.forms import SignatureForm
from petition.models import Petition, Signature


class SignatureFormRenderingTest(TestCase):
    """Accessible rendering of the signature form on the petition page"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.petition = Petition.objects.filter(published=True).first()

    def test_inputs_have_visible_labels_and_autocomplete(self):
        response = self.client.get(reverse('detail', args=[self.petition.id]))
        for field, autocomplete in (('first_name', 'given-name'), ('last_name', 'family-name'),
                                    ('email', 'email'), ('phone', 'tel')):
            self.assertContains(response, '<label class="fp-label" for="id_{}">'.format(field))
            self.assertContains(response, 'autocomplete="{}"'.format(autocomplete))
        self.assertNotContains(response, 'group_class')
        self.assertNotContains(response, 'eaFullWidthContent')
        self.assertContains(response, 'Sign the petition</button>')

    def test_invalid_post_links_errors_to_fields(self):
        data = {'first_name': 'Alan', 'last_name': '', 'email': 'wrong-mail.org', 'consent': 'on'}
        response = self.client.post(reverse('create_signature', args=[self.petition.id]), data)
        self.assertEqual(Signature.objects.count(), 0)
        self.assertContains(response, 'id="form-errors"')
        self.assertContains(response, 'href="#id_last_name"')
        self.assertContains(response, 'href="#id_email"')
        self.assertContains(response, 'aria-describedby="id_email-error"')
        self.assertContains(response, 'id="id_email-error"')
        self.assertContains(response, 'aria-invalid="true"', count=2)
        # The form keeps what the user typed
        self.assertContains(response, 'value="Alan"')

    def test_newsletter_checkbox_is_not_checked_by_default(self):
        self.petition.has_newsletter = True
        self.petition.newsletter_text = "Keep me informed"
        self.petition.save()
        form = SignatureForm(petition=self.petition)
        self.assertFalse(form['subscribed_to_mailinglist'].value())
        response = self.client.get(reverse('detail', args=[self.petition.id]))
        self.assertContains(response, 'Keep me informed')
        self.assertNotContains(response, 'checked')
