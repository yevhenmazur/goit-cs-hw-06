import logging
import mimetypes
import os
import pathlib
import signal
import socket
import sys
import urllib.parse
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from multiprocessing import Process

from pymongo import MongoClient, errors
from pymongo.server_api import ServerApi

### Всякі конфігурації

# MONGO_URI = "mongodb://mongodb:27017"
MONGO_URI = "mongodb://root:mongo_pass@localhost",

HTTPServer_Port = 3000
HTTPDocs = './httpdoc'
IP_ADDR = '127.0.0.1'
TCP_PORT = 5000

# Глобальні змінні для зберігання процесів
# Потрібна для того щоб ці процеси коректно завершувати
http_server_process = None
socket_server_process = None

class HttpGetHandler(SimpleHTTPRequestHandler):
    '''Вбудований у додаток веб-сервер'''

    def do_POST(self):
        '''
        Обробник POST запитів.
        Приймає дані з веб-форми і відправляє у SocketServer для обробки
        '''

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

    def log_message(self, format, *args):
        '''Перенаправляє access log вебсервера у основний логер'''
        logging.info("%s - %s", self.client_address[0], format % args)


def run_http_server(server_class=HTTPServer, handler_class=HttpGetHandler):
    '''Запускає вбудований веб-сервер і обробляє помилки у ньому'''
    server_address = ('0.0.0.0', HTTPServer_Port)
    logging.info("Changing working directory to %s", HTTPDocs)
    os.chdir(HTTPDocs)
    http = server_class(server_address, handler_class)
    logging.info("Starting HTTP server on port %s", HTTPServer_Port)

    try:
        http.serve_forever()
    # except KeyboardInterrupt:
    #     logging.info("Server stopped by user")
    except Exception as e:
        logging.error("Error: %s", e)
    finally:
        http.server_close()
        logging.info("Server closed")


def send_data_to_socket(data):

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((IP_ADDR, TCP_PORT))
            s.sendall(data)
            logging.debug("Sent to socket-server %s", data)
        except ConnectionRefusedError:
            logging.error("Unable to connect to the server")


def save_data(d: dict):
    '''Додає до словника дату і записує його в MongoDB'''
    try:
        client = MongoClient(
            MONGO_URI,
            server_api=ServerApi('1'),
            serverSelectionTimeoutMS=5000
        )

        client.admin.command('ping')
        logging.info("Connection to MongoDB is successful")

        current_time = datetime.now()
        d['date'] = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")

        db = client['database_1']
        collection = db['messages']
        collection.insert_one(d)
        logging.info("Document added to MongoDB collection")

    except errors.ServerSelectionTimeoutError:
        logging.error(
            "Unable to connect to MongoDB: the server is unavailable.")
        sys.exit(1)

    except errors.OperationFailure:
        logging.error("Authorization error: incorrect username or password.")
        sys.exit(1)

    except Exception as e:
        logging.error("An error occurred: %s", e)
        sys.exit(1)


def run_socket_server(host, port):
    '''Запускає сокет-сервер, який буде ловити байтстрінг із вебформи'''
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
                string_data = data.decode()
                decoded_data = urllib.parse.unquote_plus(string_data)
                data_dict = {}
                for el in decoded_data.split('&'):
                    key, value = el.split('=')
                    data_dict[key] = value

                logging.debug("Accepted on socket-server %s", data_dict)
                save_data(data_dict)

def signal_handler(sig, frame):
    '''Коректна обробка завершення процесів веб-сервера і сокет-сервера'''
    logging.info("Received SIGINT, shutting down servers...")
    if http_server_process is not None:
        http_server_process.terminate()
        http_server_process.join()
    if socket_server_process is not None:
        socket_server_process.terminate()
        socket_server_process.join()
    sys.exit(0)


if __name__ == '__main__':

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Обробник сигналів для Ctrl + C
    signal.signal(signal.SIGINT, signal_handler)

    # Запускаю веб- і сокет- сервери в окремих процесах
    http_server_process = Process(target=run_http_server)
    http_server_process.start()

    socket_server_process = Process(
        target=run_socket_server, args=(IP_ADDR, TCP_PORT))
    socket_server_process.start()

    # Дочекаємося завершення процесів
    http_server_process.join()
    socket_server_process.join()
