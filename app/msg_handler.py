from app_global_imports import *
import time
import os
import asyncio

from kafka import KafkaProducer

class CommandMsgHandler():
    def __init__(self, brokers, topic):
        self.topic = topic
        self.kafka_client = KafkaProducer(bootstrap_servers=brokers, api_version=(0,10))
    
    def send_message(self, key, value):
        self.kafka_client.send(self.topic, key=key, value=value, partition=0)

class DashboardMsgHandler():
    def __init__(self, appname='appliedscience', version="v1", secret="a test secret", timeout=10):
        import we.eventcollector.ec as event_collector
        from we.eventcollector.serialization import parse_schema
        self.ec = event_collector.EventRegister(DASHBOARD_URL, appname, version, secret, timeout=timeout)
        self.timeout = timeout

    def _set_loop(self):
        try:
            loop = asyncio.get_event_loop()
            print ('use event loop in main thread')
        except RuntimeError as e:
            print(traceback.format_exc())
            print ('use event loop in spawned thread')
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    async def _register_schema(self, filename, eventname):
        self.sender = await self.ec.register_schema_from_file(filename, eventname)

    async def _send_data(self, json_data):
        print ('send async data')
        return await self.sender.send_event(json_data)

    def register_schema(self, filename, eventname='engagement-event'):
        print ('register schema loop')
        self._set_loop()
        asyncio.get_event_loop().run_until_complete(self._register_schema(filename, eventname))

    def send_data(self, json_data):
        print ('send data loop')
        ## TODO: WHY set loop
        self._set_loop()
        # send_fut = asyncio.run_coroutine_threadsafe(self._send_data(json_data), asyncio.get_event_loop())
        # try:
        #     send_fut.result(self.timeout)
        # except Exception as exc:
        #     print(traceback.format_exc())
        asyncio.get_event_loop().run_until_complete(self._send_data(json_data))
