import pytest
import logging
import json
import sys
import os
import time
dir_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(dir_path)
from tools.logger_utils import JsonFormatter, LoggerFactory
    

DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(module)s - %(levelname)s - %(message)s'


class TestJsonFormatter():

    def test_json_log(self):
        logger = logging.getLogger()
        formatter = JsonFormatter(fmt=DEFAULT_FORMAT)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.debug({"special": "value", "run": 12})
        logger.error("classic message", extra={"special": "value", "run": 12})

    def test_log_factory(self):
        factory = LoggerFactory("test", 'INFO')
        factory.add_handler(
                handler='CONSOLE', 
                is_json='False', 
                format=DEFAULT_FORMAT, 
                level='INFO')
        factory.add_handler(
                handler='FILE', 
                is_json='True', 
                format=DEFAULT_FORMAT)
        logger = factory.get_logger()
        logger.info({"special": "value", "run": 12, "message": "test"})
        logger.error("classic message", extra={"special": "value", "run": 12})

    def _test_rotating_file_log(self):
        factory = LoggerFactory("test", 'INFO')
        factory.add_handler(handler='CONSOLE', format=DEFAULT_FORMAT, level='INFO')
        factory.add_handler(handler='TIME_FILE', format=DEFAULT_FORMAT, level='INFO')
        logger = factory.get_logger()
        total = 100
        cnt = 0
        while True:
            logger.warning("test message")
            time.sleep(20)
            cnt = cnt + 1
            if cnt > total:
                break

if __name__ == "__main__":
    test = TestJsonFormatter()
    test.test_log_factory()

