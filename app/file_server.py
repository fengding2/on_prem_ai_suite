from http.server import HTTPServer as BaseHTTPServer, SimpleHTTPRequestHandler
import os
import threading
import os
from os.path import dirname, abspath

CURRENT_DIR = os.path.split(os.path.realpath(__file__))[0]
PARENT_DIR = abspath(dirname(CURRENT_DIR))
DATA_DIR = PARENT_DIR + '/data'

class HTTPHandler(SimpleHTTPRequestHandler):
    """This handler uses server.base_path instead of always using os.getcwd()"""
    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        relpath = os.path.relpath(path, os.getcwd())
        fullpath = os.path.join(self.server.base_path, relpath)
        return fullpath

class HTTPServer(BaseHTTPServer):
    """The main server, you pass in base_path which is the path you want to serve requests from"""
    def __init__(self, base_path, server_address, RequestHandlerClass=HTTPHandler):
        self.base_path = base_path
        BaseHTTPServer.__init__(self, server_address, RequestHandlerClass)

class FileServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.httpd = HTTPServer(DATA_DIR, ("", 8000)) 
    
    def run(self):
        self.httpd.serve_forever()

if __name__ == "__main__":
    fileserver  = FileServer()
    fileserver.start()