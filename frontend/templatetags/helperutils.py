from django import template
from django.conf import settings
import logging
from time import gmtime, strftime
from datetime import timedelta, datetime
from math import modf
from PIL import Image
import os

logger = logging.getLogger('videovignette')
logger.setLevel('WARNING')

register = template.Library()

@register.simple_tag()
def to_time(term_a, term_b, *args, **kwargs):
    logger.warning("to_time: " + str(term_a) + " x " + str(term_b))
    time_float = term_a / term_b
    return strftime('%H:%M:%S', gmtime(int(time_float)))

@register.simple_tag()
def global_duration(term, *args, **kwargs):
    microseconds, seconds = modf(float(term))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    seconds = float(seconds) + microseconds
    td = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    logger.warning("global_duration: " + str(hours) + ' - ' + str(minutes) + ' - ' + str(seconds) + ' - ' + str(microseconds))
    logger.warning("global_duration: " + str(td))
    return str(td).strip('0')

@register.filter()
def getimgsize(term):
    #Fix path to the file
    path = os.path.dirname(settings.MEDIA_ROOT.rstrip('/')) + term
    if not os.path.isfile(path):
        return '100%', '100%'
    im = Image.open(path)
    return im.size # (width,height) tuple