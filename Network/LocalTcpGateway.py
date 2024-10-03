from threading import Thread
from queue import Queue
import socket
from config import local_gateway
from time import sleep

class LocalTcpGateway:
    def __init__(self, local_gateway:tuple) -> None:
        self.sink = Queue()
        self.buf_length = 10
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.active = True
        self.listen_thread = Thread(target=self.listen_loop)
        self.recvthread = Thread(target=self.recv_loop)
        self.local_gateway = local_gateway
        self.client = None
        self.parent = None         # Name for debugging purpose, compliant with VideoConnector datachannel
        self.extra_sink = Queue()   # Sink for video recording
        self.extra_sink_active = False
        try:
            self.socket.bind(local_gateway)
        except Exception as e:
            print(e)
            self.active = False

    def get_extra_sink(self):
        self.extra_sink_active = True
        return self.extra_sink
    
    def deregister_extra_sink(self):
        self.extra_sink_active = False
    
    def listen_loop(self):
        print(f"Gate A listening on {self.local_gateway}")
        while self.active: 
            self.socket.listen()
            try:
                client, ip = self.socket.accept()
            except Exception as e:
                print(e)
            try:
                self.client.close()
                print("New connection. Shut down old one on side A")
            except:
                pass
            self.client = client
            if self.client is not None:
                self.client.settimeout(2)
            print(f"Rover: {ip}")
    
    def recv_loop(self):
        while self.active:
            if self.client is not None:
                try:
                    data = self.client.recv(262144)
                    if not data:
                        try:
                            self.client.close()
                            print("ouch, no data. shutting down connection on side A")
                        except:
                            pass
                        self.client = None
                    self.sink.put(data)
                    if self.extra_sink_active:
                        self.extra_sink.put(data)
                    sleep(0)
                except socket.error:
                    pass
                except Exception as e:
                    print(e)
    
    def start(self):
        self.listen_thread.start()
        self.recvthread.start()
    
    def stop(self):
        self.active = False
        try:
            self.socket.close()
        except:
            pass    
    def destroy(self):
        self.stop()