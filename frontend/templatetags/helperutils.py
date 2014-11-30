from django import template
import logging
from time import gmtime, strftime
from datetime import timedelta
from math import modf

logger = logging.getLogger('videovignette')
logger.setLevel('WARNING')

register = template.Library()

@register.simple_tag()
def to_time(frame, fps, *args, **kwargs):
    logger.warning("to_time: " + str(frame) + " x " + str(fps))
    time_float = frame / fps
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
