"""
WSGI config for videovignette project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/howto/deployment/wsgi/
"""

import os
#from pydev import pydevd

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "videovignette.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()


# def application(environ, start_response):
#     #pydevd.settrace('192.168.1.145', port=8999, stdoutToServer=True, stderrToServer=True, suspend=False)
#     return _application(environ, start_response)