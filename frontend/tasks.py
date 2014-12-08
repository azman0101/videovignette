from __future__ import absolute_import
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)
logger.setLevel('WARNING')

from celery import shared_task
import os.path
import shutil

@shared_task()
def add(x, y):
    return x + y

@shared_task()
def delete_path(path):
    if os.path.exists(path):
        logger.warning('Removing {0}'.format(path))
        shutil.rmtree(path)
    else:
        logger.warning('Failed to remove {0} which doesn\'t exits !'.format(path))

