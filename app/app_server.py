from app_global_imports import *
from flask import Flask, jsonify
from flask_restful import Api, Resource, reqparse, abort
from server_conf import ServerConf
from zk_service import ZookeeperService
from msg_handler import CommandMsgHandler 
from file_server import FileServer
from prediction_collector import CollectManager

STATUS_OK = 200
STATUS_ERROR = 404

app = Flask(__name__)
api = Api(app)
parser = reqparse.RequestParser()
configurer = ServerConf()
configurer.start()
zookeeper_service = ZookeeperService(configurer)


class DevicesModify(Resource):
    def post(self):
        parser.add_argument('device_id', type=str)
        parser.add_argument('duration', type=str)
        parser.add_argument('instruction', type=str)
        args = parser.parse_args()
        if not args['device_id']:
            return {
                'code': 500,
                'status': False,
                'message': "missing argument 'device_id'" 
            }
        try:
            status, msg = zookeeper_service.set_device_info(args['device_id'], 
            duration=args['duration'], instruction=args['instruction'])
        except Exception as e:
            status = False
            msg = repr(e)

        if status:
            return {
                'code': 200,
                'status': status,
                'message': msg
            }
        else:
            return {
                'code': 500,
                'status': status,
                'message': msg
            }
        
class DevicesQuery(Resource):
    def post(self):
        parser.add_argument('device_id', type=str)
        args = parser.parse_args()
        device_id = args['device_id']
        try:
            results = zookeeper_service.get_devices_info(device_id)
            return jsonify(results)
        except Exception as e:
            pass

api.add_resource(DevicesModify, '/api/modify/')
api.add_resource(DevicesQuery, '/api/query/')
    
if __name__ == "__main__":
    kafka_brokers = configurer.get_kafka_brokers()
    cmd_sender = CommandMsgHandler(kafka_brokers, KAFKA_COMMANDS_TOPIC)
    collector = CollectManager(brokers=kafka_brokers, topic=KAFKA_PREDICTION_TOPIC, configurer=configurer, use_publisher=False)
    collector.start()

    file_server = FileServer(msg_handler=cmd_sender)
    file_server.start()
    app.run()