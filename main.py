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
TCP_IP = '127.0.0.1'
TCP_PORT = 5000


class HttpGetHandler(BaseHTTPRequestHandler):
    '''Вбудований у додаток веб-сервер'''

    def do_POST(self):
        '''Обробник POST запитів. Приймає дані з веб-форми і відправляє у SocketServer для обробки'''
        logging.info("POST request received: %s", self.path)
        data = self.rfile.read(int(self.headers['Content-Length']))
        self.send_response(302)
        self.send_header('Location', '/message.html')
        self.end_headers()
        
        send_data_to_socket(data)


    def do_GET(self):
        '''Обробник GET запитів. Віддає сторінку, відповідну до URL'''
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
        '''Віддає файл, чи сторінку 404'''
        try:
            with open(filename, 'rb') as f:
                self.send_response(status_code)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.send_html_file('error.html', 404)

    def send_static(self):
        '''Віддає статичні ресурси чи повідомляє про помилку'''
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
    '''Запускає вбудований веб-сервер і обробляє помилки у ньому'''
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

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((TCP_IP, TCP_PORT))
            s.sendall(data) 
            # print(f'Data sent: {data}')
        except ConnectionRefusedError:
            logging.error("Unable to connect to the server")


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
    

def run_socket_server(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(1)
        logging.info("SocketServer started")

        conn, addr = s.accept()
        logging.info("SocketServer started")

        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                string_data = (data.decode())
                decoded_data = urllib.parse.unquote_plus(string_data)
                data_dict = {key: value for key, value in [el.split('=') for el in decoded_data.split('&')]}

                print(f"Прийнято на сокет-сервері: {data_dict}")
    #TODO Дописати логіку прийняття даних та їх збереження в БД

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(threadName)s %(message)s')

    # Запускаю веб- і сокет- сервери в окремих процесах
    http_server_process = Process(target=run_http_server)
    http_server_process.start()

    socket_server_process = Process(target=run_socket_server, args=(TCP_IP, TCP_PORT))
    socket_server_process.start()
    