import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))
from PyQt5.QtCore import pyqtSignal, QObject
from Logger.MissionControl_Logger import MCLogger
import json

class ConfigureEmitter(QObject):
    status_sent_signal = pyqtSignal(object)
    status_written_signal = pyqtSignal(object)
    config_signal = pyqtSignal(object)

class Configurator:
    config = {}
    config_file = ""
    datachannel = None
    emitter = ConfigureEmitter()

    @classmethod
    def send_configuration(cls, message):
        if cls.datachannel is not None and cls.datachannel.connected:
            cls.datachannel.source.put(message.encode("utf-8"))
            cls.emitter.status_signal.emit(True)
        else:
            MCLogger.logCritical("Couldn't send rover configuration because not connected")
            cls.emitter.status_sent_signal.emit(False)
    
    @classmethod
    def write_config_file(cls, content):
        cls.config = content
        with open(cls.config_file, "w") as file:
            json.dump(content, file)
        cls.emitter.status_written_signal.emit(True)

    @classmethod
    def load_config_file(cls):
        cls.config = json.load(cls.config_file)





