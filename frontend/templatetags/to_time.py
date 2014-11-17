from django import template
import logging
import time

logger = logging.getLogger('videovignette')
logger.setLevel('WARNING')

register = template.Library()

@register.simple_tag()
def to_time(term_a, term_b, *args, **kwargs):
    logger.warning("Multiply: " + str(term_a) + " x " + str(term_b))
    time_float = term_a / term_b
    return time.strftime('%H:%M:%S', time.gmtime(int(time_float)))