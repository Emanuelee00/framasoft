from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase

from .utils import add_default_data

from petition.models import Petition


class ConfirmTemplateTest(TestCase):
    """petition/confirm.html: what the tests of the confirm view (tests_Confirm) do not check (FE-03)"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.petition = Petition.objects.filter(published=True).first()

    def render(self, confirm_state):
        return render_to_string('petition/confirm.html', {'petition': self.petition, 'confirm_state': confirm_state},
                                request=RequestFactory().get('/'))

    def test_error_states_are_alerts_linking_back_to_the_form(self):
        for state in ('expired', 'invalid_link'):
            html = self.render(state)
            self.assertIn('role="alert"', html)
            self.assertIn('href="{}#signer"'.format(self.petition.url), html)

    def test_states_have_a_single_focusable_heading(self):
        for state in ('already_confirmed', 'expired', 'invalid_link'):
            html = self.render(state)
            self.assertEqual(html.count('<h1'), 1, state)
            self.assertIn('data-autofocus', html)
