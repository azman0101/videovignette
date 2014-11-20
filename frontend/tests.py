from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase, RequestFactory
import os

TEST_DIR = os.path.dirname(os.path.dirname(__file__))

class SimpleTest(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.client = Client()

    def test_details(self):

        with open(TEST_DIR + '/frontend/test_data/out.ogv') as fp:
            response = self.client.post('upload/', {'name': 'fred', 'attachment': fp})

        self.assertEqual(response.status_code, 200)