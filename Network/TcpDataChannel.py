
import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))
from queue import Queue, Empty
import socket
from config import *
from threading import Thread
from Logger.MissionControl_Logger import MCLogger
from time import sleep
from Network.ConnectionStatus import ConnectionStatus

class TcpDataChannel:
    def __init__(self, source: Queue, sink: Queue, remote_host: tuple, localhost:tuple=None, parent=None, send=True, recv=True):
        """
        source: FIFO Queue used to buffer data to send to the remote
        sink: FIFO Queue used to buffer data for internal processes
        parent: a string roughly describing what is using the socket. For logging and debug purpose
        if localhost is not specified, it does not bind the socket
        """
        self.sink = sink
        self.source = source
        self.remote_host = remote_host
        self.localhost = localhost
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if localhost is not None:
            self.socket.bind(localhost)
        self.socket.settimeout(5)
        self.sendthread = Thread(target=self.sendloop)
        self.recvthread = Thread(target=self.recvloop)
        self.recvactive = True
        self.sendactive = True
        self.status = ConnectionStatus()
        self.parent = parent
        self.send_enabled = send
        self.recv_enabled = recv
        self.connected = False
        self.connecting = False
        self.errored = False
        self.keepalivethread = Thread(target=self.keepalive)
        self.extra_sink = Queue()
        self.extra_sink_active = False

    def get_extra_sink(self):
        self.extra_sink_active = True
        return self.extra_sink
    
    def deregister_extra_sink(self):
        self.extra_sink_active = False

    def sendloop(self):
        self.connect()
        while self.source is not None and self.sendactive:
            try:
                data = self.source.get(timeout=1)
                self.socket.sendall(data)
                self.status.set_sending(True)
            except Empty:
                if not self.sendactive:
                    print(f"TCP receiving at {self.parent} stopped.")
                    return
                else:
                    continue
            
            except Exception as e: 
                if not self.sendactive:
                    print(f"TCP receiving at {self.parent} stopped.")
                    return
                if not self.connected:
                    self.connected = False
                    MCLogger.logError(f"TCP sending error: {e}")
                self.connect()
            sleep(0)

    def recvloop(self):
        self.connect()
        MCLogger.logControl("Waiting for connection...")
        while self.sink is not None and self.recvactive:
            try:
                data = self.socket.recv(262144)
                if not data:
                    self.errored = True
                    self.connected = False
                    self.connect()
                self.sink.put(data)
                if self.extra_sink_active:
                    self.extra_sink.put(data)
                self.status.set_receivingtimedout(False)
                self.status.set_receiving(True)
                initialized = True
            
            except socket.timeout:
                if not self.recvactive:
                    print(f"TCP receiving stopped at {self.parent}")
                    return
                if not self.connected:
                    self.connect()
            
            except Exception as e:
                if self.status.receiving:
                    if self.connected:
                        MCLogger.logError(f"Network error: {e} from {self.parent}")
                    if not self.recvactive:
                        print(f"TCP receiving at {self.parent} stopped.")
                        return
                    self.errored = True
                    self.connected = False
                    self.connect()
            sleep(0)
        print(f"TCP receiving stopped at {self.parent}")

    def connect(self):
        if self.errored:
            try:
                self.socket.close()
            except:
                pass
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(3)
        attempted = False
        while (self.sendactive or self.recvactive) and not self.connected:
            try:
                try:
                    self.socket.close()
                except:
                    self.socket = None
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(3)
                self.connecting = True
                self.socket.connect(self.remote_host)
                self.connected = True
                self.connecting = False
                MCLogger.logOK(f"Connected to TCP port of {self.parent}")
            except Exception as e:
                if (not self.recvactive) or (not self.sendactive):
                    print(f"TCP connecting at {self.parent} stopped.")
                    return
                if not attempted:
                    MCLogger.logError(f"Connection to TCP port of {self.parent} failed: {e}")
                    attempted = True
                self.connected = False
                
                sleep(3)

    def start(self):
        self.send_thread = Thread(target=self.sendloop)
        self.recvthread = Thread(target=self.recvloop)
        if self.send_enabled:
            self.sendthread.start()
        if self.recv_enabled:
            self.recvthread.start()
        if not self.send_enabled:
            self.keepalivethread.start()

    def stop(self):
        self.sendactive = False
        self.recvactive = False

    def keepalive(self):
        while self.sendactive:
            try:
                self.socket.send('i'.encode('utf-8'))
                self.connected = True
                sleep(1)
            except socket.error:
                self.connected = False
        
        print(f"TCP Keepalive stopped at {self.parent}")
    
    def destroy(self):
        self.stop()
        self.socket.close()