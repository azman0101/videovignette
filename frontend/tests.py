from django.test import TestCase
from django.test.client import Client
from django.test import TestCase, RequestFactory
from django.conf import settings
import os
import json
import shutil
import logging
from django.test.utils import override_settings
from time import sleep

logger = logging.getLogger('videovignette')
logger.setLevel('WARNING')

TEST_DIR = os.path.dirname(os.path.dirname(__file__))

class SimpleTest(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.client = Client()
        self.filetodelete = []

    @override_settings(MEDIA_URL='/media_test/',
                       MEDIA_ROOT=os.path.join(TEST_DIR, 'media_test/'))
    def test_video_ogv(self):
	logger.info(TEST_DIR)
        with open(TEST_DIR + '/frontend/test_data/out.ogv') as fp:
            logger.warning("test_video_ogv settings: " + settings.MEDIA_ROOT)
            response = self.client.post('/upload/', {'files[]': fp})
            response_json = json.loads(response.content)
            for f in response_json['files']:
                self.filetodelete.append(f)

            self.assertEqual(response.status_code, 200)

    @override_settings(MEDIA_URL='/media_test/',
                       MEDIA_ROOT=os.path.join(TEST_DIR, 'media_test/'))
    def test_nonvideo_pdf(self):

        with open(TEST_DIR + '/frontend/test_data/enveloppes.pdf') as fp:

            response = self.client.post('/upload/', {'files[]': fp})

        self.assertEqual(response.status_code, 400)

    @override_settings(MEDIA_URL='/media_test/',
                       MEDIA_ROOT=os.path.join(TEST_DIR, 'media_test/'))
    def tearDown(self):
        super(SimpleTest, self).tearDown()
        if os.path.exists(settings.MEDIA_ROOT):
            logger.info('Remove folder : ' + settings.MEDIA_ROOT)
            shutil.rmtree(settings.MEDIA_ROOT)
            sleep(1)

