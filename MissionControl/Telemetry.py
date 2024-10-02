import pickle
from time import sleep

from PyQt5.QtCore import pyqtSignal, QObject, QTimer
from datetime import datetime
from threading import Thread
from queue import Empty
import json

from Logger.MissionControl_Logger import MCLogger

class Telemetry(QObject):
    signal_telemetry = pyqtSignal(object)
    def __init__(self, datachannel) -> None:
        super(Telemetry, self).__init__()
        self.thread = Thread(target=self.telemetry_loop)
        self.pingthread = Thread(target=self.ping)
        self.datachannel = datachannel
        self.datachannel.parent="Telemetry"
        self.active = True
        self.connected = False
    
    def telemetry_loop(self):
        initialized = False
        MCLogger.logControl(f"Waiting for telemetry data...")
        while self.active:
            try:
                data = self.datachannel.sink.get(timeout=3)
                data = json.loads(data.decode("utf-8"))
                #print(data)
                data["Online"] = True
                self.connected = True
                self.signal_telemetry.emit(data)
                #print(data)
                for s in data["Err"]:
                    MCLogger.logRover(s)
                if not initialized:
                    MCLogger.logOK(f"Receiving telemetry data...")
                    initialized = True
            except Empty:
                if not self.active:
                    return 
                else:
                    self.signal_telemetry.emit({"Online": False})
                    if self.connected:
                        MCLogger.logProblem("Lost connection to rover")
                        self.connected = False
                    pass #TODO: use this to inform connection is broken
    def ping(self):
        while self.active:
            self.datachannel.source.put("ping".encode("utf-8"))
            sleep(1)

    def start(self):
        self.thread.start()
        self.pingthread.start()
    
    def stop(self):
        self.active = False
                    