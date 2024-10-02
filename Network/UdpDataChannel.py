import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))
from queue import Queue, Empty
import socket
from threading import Thread
from Logger.MissionControl_Logger import MCLogger
from time import sleep
from Network.ConnectionStatus import ConnectionStatus

class UdpDataChannel:
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
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if localhost is not None:
            self.socket.bind(localhost)
        self.socket.settimeout(10)
        self.sendthread = Thread(target=self.sendloop)
        self.recvthread = Thread(target=self.recvloop)
        self.recvactive = True
        self.sendactive = True
        self.status = ConnectionStatus()
        self.parent = parent
        self.send_enabled = send
        self.recv_enabled = recv
        self.started = False

    def sendloop(self):
        while self.source is not None and self.sendactive:
            try:
                data = self.source.get(timeout=1)
                self.socket.sendto(data, self.remote_host)
                self.status.set_sendingtimedout(False)
                self.status.set_sending(True)
                self.status.set_sending_err(False)
            except Empty:
                if not self.sendactive:
                    return
                else:
                    continue
            except socket.error as e:
                if not self.sendactive:
                    print(f"UDP sending stopped at {self.parent}")
                    return
                if not self.status.sending_err:
                    MCLogger.logControl(f"Network error: {e} from {self.parent}")
                    self.status.set_sending_err(True)
            except Exception as e: 
                if not self.sendactive:
                    print(f"UDP sending stopped at {self.parent}")
                    return

    def recvloop(self):
        MCLogger.logControl("Waiting for connection...")
        while self.sink is not None and self.recvactive:
            if not self.send_enabled:
                self.socket.sendto('i'.encode(), self.remote_host)  # push data to the remote if not in send mode to initiate the comm
            try:
                data, remote = self.socket.recvfrom(65536)
                #print(data)
                self.sink.put(data)
                self.status.set_receivingtimedout(False)
                self.status.set_receiving(True)
                initialized = True
            except socket.timeout:
                if not self.recvactive:
                    print(f"UDP receiving at {self.parent} stopped.")
                    return
                if self.status.receiving:
                    if self.status.receiving:
                        MCLogger.logProblem(f"Receive loop timeout from {self.parent}")
                        self.status.receiving = False 
                    self.status.set_receivingtimedout(True)
                    sleep(1)
                continue

            except socket.error as e:
                if not self.recvactive:
                    print(f"UDP receiving at {self.parent} stopped.")
                    return
                MCLogger.logError(f"Network error: {e} from {self.parent}")
                self.status.set_receiving_err(e)
                sleep(1)
            
            except Exception as e:
                MCLogger.logError(f"Network error: {e} from {self.parent}")
                sleep(1)
                if not self.recvactive:
                    print(f"UDP receiving at {self.parent} stopped.")
                    return
            
            sleep(0)

    def start(self):
        self.started = True
        self.send_thread = Thread(target=self.sendloop)
        self.recvthread = Thread(target=self.recvloop)
        if self.send_enabled:
            self.sendthread.start()
        if self.recv_enabled:
            self.recvthread.start()

    def stop(self):
        self.sendactive = False
        self.recvactive = False

    def destroy(self):
        self.stop()
        self.socket.close()
    
if __name__ == "__main__":
    from time import sleep
    source = Queue()
    sink = Queue()
    channel = UdpDataChannel(source=source, sink=sink, remote_host=("127.0.0.1", 9000), localhost=None)
    channel.start()
    for i in range(40):
        source.put(bytes("Hello", "utf-8"))
        print("sent")
        sleep(1)