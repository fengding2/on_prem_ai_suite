from app_global_imports import *
import time
import os
import asyncio
import we.eventcollector.ec as event_collector
from we.eventcollector.serialization import parse_schema
from kafka import KafkaProducer

class CommandMsgHandler():
    def __init__(self, brokers, topic):
        self.topic = topic
        self.kafka_client = KafkaProducer(bootstrap_servers=brokers, api_version=(0,10))
    
    def send_message(self, key, value):
        self.kafka_client.send(self.topic, key=key, value=value, partition=0)


class DashboardMsgHandler():
    def __init__(self, appname='appliedscience', version="v1", secret="a test secret", timeout=10):
        self.ec = event_collector.EventRegister(DASHBOARD_URL, appname, version, secret, timeout=timeout)

    def _set_loop(self):
        try:
            loop=asyncio.get_event_loop()
            print ('use event loop in main thread')
        except RuntimeError:
            print ('use event loop in spawned thread')
            loop=asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    async def _register_schema(self, filename, eventname):
        self.sender =  await self.ec.register_schema_from_file(filename, eventname)

    async def _send_data(self, json_data):
        print ('send async data')
        return await self.sender.send_event(json_data)

    def register_schema(self, filename, eventname='engagemint-event'):
        print ('register schema loop')
        self._set_loop()
        asyncio.get_event_loop().run_until_complete(self._register_schema(filename, eventname))

    def send_data(self, json_data):
        print ('send data loop')
        ## TODO: WHY set loop
        self._set_loop()
        asyncio.get_event_loop().run_until_complete(self._send_data(json_data))


if __name__ == "__main__":
    from prediction_collector import dashboard_data
    dashboard_sender = DashboardMsgHandler(appname=DASHBOARD_APPNAME, secret=DASHBOARD_PSWORD)
    dashboard_sender.register_schema(DASHBOARD_SCHEMA_PATH, eventname=DASHBOARD_EVENTNAME)
    i = 0
    while True:
        data = dashboard_data('test_device1', 'desc_test', 'a.jpg', [])
        dashboard_sender.send_data(data)
        time.sleep(1)
        i = i + 1
        if i > 10:
            break