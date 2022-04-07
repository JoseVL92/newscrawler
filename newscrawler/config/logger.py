import logging
import os

from logging.handlers import RotatingFileHandler

# setup logger
logger = logging.getLogger(__name__)
logs_dir = '/var/log/newscrawler'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, "webcrawler.log")
formatter = logging.Formatter('%(asctime)s - %(filename)s - %(lineno)d - %(levelname)s - %(message)s')
file_handler = RotatingFileHandler(log_file, maxBytes=2000000, backupCount=3)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)
