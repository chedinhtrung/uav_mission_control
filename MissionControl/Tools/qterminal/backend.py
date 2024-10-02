import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(path))
from mux import Multiplexer
from screen import QTerminalScreen
from stream import QTerminalStream
import paramiko
import threading
import time
import uuid


class BaseBackend(object):

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.screen = QTerminalScreen(width, height, history=9999, ratio=.3)
        self.stream = QTerminalStream(self.screen)
        self.id = str(uuid.uuid4())

    def write_to_screen(self, data):
        self.stream.feed(data)

    def read(self):
        pass

    def resize(self, width, height):
        self.width = width
        self.height = height
        self.screen.resize(columns=width, lines=height)
        print(width, height)

    def connect(self):
        pass

    def get_read_wait(self):
        pass

    def cursor(self):
        return self.screen.cursor

    def close(self):
        pass


class PtyBackend(BaseBackend):
    pass


class SSHBackend(BaseBackend):

    def __init__(self, width, height, ip, port=22, username=None, password=None):
        super(SSHBackend, self).__init__(width, height)
        self.ip = ip
        self.username = username
        self.password = password
        self.thread = threading.Thread(target=self.connect)
        self.ssh_client = None
        self.channel = None
        self.mux = Multiplexer()
        self.port = port
        self.thread.start()

    def connect(self):
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(hostname=self.ip, port=self.port, username=self.username, password=self.password)
        self.channel = self.ssh_client.get_transport().open_session()
        self.channel.get_pty(width=self.width, height=self.height)
        self.channel.invoke_shell()

        timeout = 60
        while not self.channel.recv_ready() and timeout > 0:
            time.sleep(1)
            timeout -= 1

        self.channel.resize_pty(width=self.width, height=self.height)

        self.mux.add_backend(self)

    def get_read_wait(self):
        return self.channel

    def write(self, data):
        self.channel.send(data)

    def read(self):
        output = self.channel.recv(1024)
        self.write_to_screen(output.replace(b'\t', b'   '))

    def resize(self, width, height):
        super(SSHBackend, self).resize(width, height)
        if self.channel:
            self.channel.resize_pty(width=width, height=height)

    def close(self):
        if self.ssh_client is not None:
            self.ssh_client.close()
        self.mux.remove_and_close(self)
