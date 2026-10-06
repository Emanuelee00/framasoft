# framapetitions: BE-11 / S15
from datetime import timedelta

import matplotlib.pyplot as plt
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from petition.models import PytitionUser, Signature
from petition.views import SIGNATURES_PER_PAGE
from .utils import add_default_data


class SignatureAreaTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.client.login(username='julia', password='julia')
        self.petition = PytitionUser.objects.get(user__username='julia').petition_set.first()

    def add_signatures(self, count, when=None):
        when = when or timezone.now()
        Signature.objects.bulk_create([
            Signature(first_name="First%d" % i, last_name="Last", email="s%d@example.org" % i,
                      petition=self.petition, date=when)
            for i in range(count)
        ])

    def test_signatures_are_paginated(self):
        self.add_signatures(SIGNATURES_PER_PAGE + 1)
        url = reverse("show_signatures", args=[self.petition.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['signatures']), SIGNATURES_PER_PAGE)
        self.assertTrue(response.context['page_obj'].has_next())
        self.assertContains(response, 'class="fp-pagination"')
        response = self.client.get(url, {'page': 2})
        self.assertEqual(len(response.context['signatures']), 1)
        # invalid page numbers fall back to an existing page
        response = self.client.get(url, {'page': 'x'})
        self.assertEqual(response.context['page_obj'].number, 1)

    def test_single_page_has_no_pagination(self):
        self.add_signatures(3)
        response = self.client.get(reverse("show_signatures", args=[self.petition.id]))
        self.assertEqual(len(response.context['signatures']), 3)
        self.assertNotContains(response, 'class="fp-pagination"')

    def test_graph_closes_its_figure(self):
        plt.close('all')
        self.add_signatures(2, timezone.now() - timedelta(days=1))
        self.add_signatures(3)
        response = self.client.get(reverse("show_signatures_graph", args=[self.petition.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "petition/signature_graph.html")
        self.assertTrue(response.context['image_base64'])
        self.assertEqual(plt.get_fignums(), [])
        self.assertEqual(plt.get_backend().lower(), 'agg')

    def test_graph_without_signatures(self):
        response = self.client.get(reverse("show_signatures_graph", args=[self.petition.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "petition/signature_data.html")
        self.assertNotIn('image_base64', response.context)
