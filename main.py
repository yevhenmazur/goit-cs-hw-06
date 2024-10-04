from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from multiprocessing import Process
import mimetypes
import json
import urllib.parse
import pathlib
import socket
import logging
import os

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb://mongodb:27017"

HTTPServer_Port = 3000
HTTPDocs = './httpdoc'
UDP_IP = '127.0.0.1'
UDP_PORT = 5000
logging.basicConfig(level=logging.INFO)


class HttpGetHandler(BaseHTTPRequestHandler):
    '''Базовий веб-сервер'''

    def do_POST(self):
        logging.info("POST request received: %s", self.path)
        pass


    def do_GET(self):
        logging.info("GET request received: %s", self.path)
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/message.html':
            self.send_html_file('message.html')
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_error(404, "File Not Found")

    def send_html_file(self, filename, status_code=200):
        try:
            with open(filename, 'rb') as f:
                self.send_response(status_code)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.send_html_file('error.html', 404)

    def send_static(self):
        file_path = pathlib.Path(self.path[1:])
        self.send_response(200)
        mt = mimetypes.guess_type(file_path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()

        with open(file_path, 'rb') as f:
            self.wfile.write(f.read())


def run_http_server(server_class=HTTPServer, handler_class=HttpGetHandler):
    server_address = ('0.0.0.0', HTTPServer_Port)
    logging.info("Changing working directory to %s", HTTPDocs)
    os.chdir(HTTPDocs)
    http = server_class(server_address, handler_class)
    logging.info("Starting HTTP server on port %s", HTTPServer_Port)
    
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error("Error: %s", e)
    finally:
        http.server_close()
        logging.info("Server closed")


def send_data_to_socket(data):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = UDP_IP, UDP_PORT
    #TODO Дописати відправку даних

def save_data(data):
    client = MongoClient(uri, server_api=ServerApi("1"))
    db = client.DB_NAME

    # Дописати логіку збереження даних в БД з відповідними вимогами до структурою документу
    """
    { 
	    "date": "2024-04-28 20:21:11.812177",
        "username": "Who",    
	    "message": "What"  
    }
    """
    # Ключ "date" кожного повідомлення — це час отримання повідомлення: datetime.now()
    data_parse = urllib.parse.unquote_plus(data.decode())
    

def run_socket_server(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    sock.bind(server)
    #TODO Дописати логіку прийняття даних та їх збереження в БД

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(threadName)s %(message)s')

    #TODO Зробити два процеса для кожного з серверів
    # http_server_process = Process()
    # http_server_process.start()

    # socket_server_process = Process()
    # socket_server_process.start()
    run_http_server()
    