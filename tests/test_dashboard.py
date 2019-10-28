import os
import sys
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app_path = parent_path + '/app'
sys.path.append(parent_path)
sys.path.append(app_path)

import pytest
from app.msg_handler import DashboardMsgHandler
from app.prediction_collector import dashboard_data
from app.app_global_imports import *
import time

class TestDashboard():

    def test_valid_sending(self):
        publisher = DashboardMsgHandler(appname=DASHBOARD_APPNAME, secret=DASHBOARD_PSWORD)
        publisher.register_schema(DASHBOARD_SCHEMA_PATH, eventname=DASHBOARD_EVENTNAME)
        for _ in range(10):
            time.sleep(1)
            publisher.send_data(dashboard_data('test_id', 'test', 'no_file', []))

if __name__ == '__main__':
    TestDashboard().test_valid_sending()