import pickle
from time import sleep

from PyQt5.QtCore import pyqtSignal, QObject, QTimer
import pygame
from datetime import datetime
from threading import Thread
from Logger.MissionControl_Logger import MCLogger

class Command(QObject):
    command_sig = pyqtSignal(object)
    mirror_sig = pyqtSignal()
    launch_sig = pyqtSignal(object)
    status_sig = pyqtSignal(str)

    def __init__(self, datachannel):
        super(Command, self).__init__()
        self.listening = True
        self.gear = 1
        self.launch_authorized = True
        self.thread = Thread(target=self.command_loop)
        self.datachannel = datachannel
        self.datachannel.parent = "Command"

    def command_loop(self):
        pygame.init()
        pygame.joystick.init()
        connected = False
        joystick = None
        while self.listening:
            for event in pygame.event.get():
                if event.type == pygame.JOYDEVICEADDED:
                    print("Joystick connected")
                    connected = True
                    joystick = pygame.joystick.Joystick(0)
                    self.status_sig.emit("JOYSTICK READY")
            while connected and self.listening:
                try:
                    tilt = 50+joystick.get_axis(1)*30
                    pan = 45-joystick.get_axis(2)*30
                    control_status = (
                        'C', int(pan), int(tilt), self.gear)
                    #print(control_status)
                    #self.command_sig.emit(control_status)
                    self.datachannel.source.put(pickle.dumps(control_status))
                except Exception as e: 
                    print(e)
                    MCLogger.logError(f"Command error: {e}")
                    connected = False
                    break
                
                try:
                    for event in pygame.event.get():
                        pass
                except:
                    pass
                sleep(0.05)
            sleep(0.02)
        print("command stopped")


    def start(self):
        self.thread.start()

    def stop(self):
        try:
            self.listening = False
            pygame.quit()
        except Exception as e:
            print(e)
