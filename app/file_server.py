from app_global_imports import *
from http.server import ThreadingHTTPServer as BaseHTTPServer, SimpleHTTPRequestHandler
import os
import threading
from io import BytesIO
import mimetypes
import re
from kafka import KafkaConsumer
from PIL import Image
import json

class HTTPHandler(SimpleHTTPRequestHandler):
    MSG_HANDLER = None

    """This handler uses server.base_path instead of always using os.getcwd()"""
    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        relpath = os.path.relpath(path, os.getcwd())
        fullpath = os.path.join(self.server.base_path, relpath)
        return fullpath

    def do_POST(self):
        """Serve a POST request"""
        r, info = self.deal_post_stream()
        f = BytesIO()
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>Upload Result Page</title>\n")
        f.write(b"<body>\n<h2>Upload Result Page</h2>\n")
        f.write(b"<hr>\n")
        if r:
            f.write(b"<strong>Success:</strong>")
        else:
            f.write(b"<strong>Failed:</strong>")
        f.write(info.encode())
        f.write(b"</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        if r: 
            self.send_response(200)
            if HTTPHandler.MSG_HANDLER:
                file_name = info
                device_id, _ = file_name.split('_')
                b_device_id = bytes(device_id, 'ascii')
                model_msg = json.dumps({'device_id': device_id, 'file_name': file_name})
                b_msg = bytes(model_msg, 'ascii')
                HTTPHandler.MSG_HANDLER.send_message(b_device_id, b_msg)
        else:
            self.send_response(500)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            self.copyfile(f, self.wfile)
            f.close()

    def deal_post_stream(self):
        content_type = self.headers['content-type']
        if not content_type:
            return (False, "Content-Type header doesn't contain boundary")
        boundary = content_type.split("=")[1].encode()
        remainbytes = int(self.headers['content-length'])
        line = self.rfile.readline()
        remainbytes -= len(line)
        if not boundary in line:
            return (False, "Content NOT begin with boundary")
        line = self.rfile.readline()
        remainbytes -= len(line)
        fn = re.findall(r'Content-Disposition.* filename="(.*)"', line.decode())
        if not fn:
            return (False, "Can't find out file name...")
        path = self.translate_path(self.path)
        if not os.path.exists(path):
            os.makedirs(path)
        fn = os.path.join(path, fn[0])
        line = self.rfile.readline()
        remainbytes -= len(line)
        #line = self.rfile.readline()
        #remainbytes -= len(line)
        try:
            out = open(fn, 'wb')
        except IOError:
            return (False, "Can't create file to write, do you have permission to write?")
                
        preline = self.rfile.readline()
        remainbytes -= len(preline)
        while remainbytes > 0:
            line = self.rfile.readline()
            remainbytes -= len(line)
            if boundary in line:
                preline = preline[0:-1]
                if preline.endswith(b'\r'):
                    preline = preline[0:-1]
                out.write(preline)
                out.close()
                return (True, fn)
            else:
                out.write(preline)
                preline = line
        return (False, "Unexpect Ends of data.")


class HTTPServer(BaseHTTPServer):
    """The main server, you pass in base_path which is the path you want to serve requests from"""
    def __init__(self, base_path, server_address, msg_handler=None, RequestHandlerClass=HTTPHandler):
        self.base_path = base_path
        HTTPHandler.MSG_HANDLER = msg_handler
        BaseHTTPServer.__init__(self, server_address, RequestHandlerClass)

class PicChannelReceiver():
    def __init__(self, brokers, consumer_topic):
        if not consumer_topic:
            raise InitializationException("No consumer topic was found")
        self.kafka_consumer = KafkaConsumer(consumer_topic, bootstrap_servers= brokers, api_version=(0,10))

    def _save_pic_file(self, device_id, file_name, bin_stream):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        device_dir = DATA_DIR + '/' + device_id
        if not os.path.exists(device_dir):
            os.makedirs(device_dir)
        image = Image.open(BytesIO(bin_stream))
        file_path = device_dir + '/' + file_name
        image.save(file_path)
        return os.path.exists(file_path)

    def receive_forever(self, msg_handler):
        for msg in self.kafka_consumer:
            try:
                b_key = msg.key
                file_name = b_key.decode('utf-8')
                device_id, _ = file_name.split('_')
                b_picstream = msg.value
                if self._save_pic_file(device_id, file_name, b_picstream):
                    b_device_id = bytes(device_id, 'ascii')
                    model_msg = json.dumps({'device_id': device_id, 'file_name': file_name})
                    b_msg = bytes(model_msg, 'ascii')
                    ## send model command to topic(model_commands)
                    msg_handler.send_message(b_device_id, b_msg)
            except Exception as e:
                pass ## TODO
        

class FileServer(threading.Thread):
    def __init__(self, msg_handler=None, brokers=[], consumer_topic=None, kafka_on=False):
        threading.Thread.__init__(self)
        ## message handler 
        ## used for sending command of `model_command`
        self.msg_handler = msg_handler
        self.httpd = HTTPServer(DATA_DIR, ("", 8000), msg_handler=self.msg_handler)
        self.flag_kafka_on = kafka_on
        self.kafka_receiver = None
        if self.flag_kafka_on:
            self.kafka_receiver = PicChannelReceiver(brokers, consumer_topic)
    
    def run(self):
        self.httpd.serve_forever()
        if self.flag_kafka_on:
            self.kafka_receiver.receive_forever(self.msg_handler)


if __name__ == "__main__":
    file_server = FileServer()
    file_server.start()