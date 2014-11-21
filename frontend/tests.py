from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase, RequestFactory
import os
import logging
from frontend.models import VideoUploadModel

logger = logging.getLogger('videovignette')
logger.setLevel('WARNING')

TEST_DIR = os.path.dirname(os.path.dirname(__file__))

class SimpleTest(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.client = Client()
        self.filetodelete = None

    def test_video_ogv(self):

        with open(TEST_DIR + '/frontend/test_data/out.ogv') as fp:

            response = self.client.post('/upload/', {'files[]': fp})
        #TODO: DELETE HEREEEEEEE
        self.filetodelete = response.FILES[0]
        self.assertEqual(response.status_code, 200)

    def test_nonvideo_pdf(self):

        with open(TEST_DIR + '/frontend/test_data/enveloppes.pdf') as fp:

            response = self.client.post('/upload/', {'files[]': fp})

        self.assertEqual(response.status_code, 400)

    def tearDown(self):
        #TODO: remove file upload by test_video_ogv from media if exists
        super(SimpleTest, self).tearDown()

