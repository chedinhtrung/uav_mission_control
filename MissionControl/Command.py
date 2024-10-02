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
        self.control_status = {
            "HEADER": 'M',
            "LEFT": 0.0,
            "RIGHT": 0.0
        }
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
                    self.control_status["HEADER"] = 'M'
                    backforth = joystick.get_axis(3)
                    leftright = joystick.get_axis(0)
                    self.control_status["LEFT"] = round(
                        backforth - (pow(2, -abs(backforth)))*leftright, 2)
                    self.control_status["RIGHT"] = round(
                        backforth + (pow(2, -abs(backforth)))*leftright, 2)

                    if (joystick.get_button(4) > 0.5) or (joystick.get_button(5) > 0.5):
                        self.control_status["HEADER"] = "L"
                        sleep(0.07)

                    if joystick.get_axis(5) > 0.5:
                        self.control_status["RIGHT"] = 0
                    if joystick.get_axis(4) > 0.5:
                        self.control_status["LEFT"] = 0
                    if (joystick.get_axis(5) > 0.5) and (joystick.get_axis(4) > 0.5):
                        self.control_status["HEADER"] = 'B'
                        self.launch_authorized = False
                except Exception as e:
                    print(e)
                    MCLogger.logError(f"Command error: {e}")
                    connected = False
                    break

                control_status = (
                    self.control_status["HEADER"], self.gear*self.control_status["LEFT"], self.gear*self.control_status["RIGHT"], self.gear)
                self.command_sig.emit(control_status)
                self.datachannel.source.put(pickle.dumps(control_status))

                try:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self.listening = False
                            connected = False
                            break

                        elif event.type == pygame.JOYDEVICEREMOVED:
                            self.status_sig.emit("JOYSTICK DISCONNECTED")
                            print("JOYSTICK DISCONNECTED")
                            connected = False
                            break
                        if event.type == pygame.JOYBUTTONDOWN:
                            if joystick.get_button(3) > 0:
                                self.control_status["HEADER"] = 'D'
                                control_status = (
                                    self.control_status["HEADER"], self.control_status["LEFT"], self.control_status["RIGHT"], self.gear)
                                self.command_sig.emit(control_status)
                                self.datachannel.source.put(pickle.dumps(control_status))

                            if joystick.get_button(6) > 0.5 and joystick.get_button(7) > 0.5:
                                self.control_status["HEADER"] = 'R'
                                control_status = (
                                    self.control_status["HEADER"], self.control_status["LEFT"], self.control_status["RIGHT"], self.gear)
                                self.command_sig.emit(control_status)
                                self.datachannel.source.put(pickle.dumps(control_status))
                                MCLogger.logCritical("REBOOTING ROVER...")
                            if joystick.get_button(2) > 0:
                                self.control_status["HEADER"] = 'F'
                                self.launch_authorized = True
                                control_status = (
                                    self.control_status["HEADER"], self.control_status["LEFT"], self.control_status["RIGHT"], self.gear)
                                countdown = 10
                                while countdown >= 0:
                                    self.launch_sig.emit(round(countdown, 2))
                                    for event in pygame.event.get():
                                        if event.type != pygame.JOYBUTTONUP:
                                            self.launch_sig.emit("CANCELED")
                                            countdown = -10
                                            self.launch_authorized = False
                                            break
                                    countdown -= 0.01
                                    sleep(0.01)
                                if self.launch_authorized:
                                    self.command_sig.emit(control_status)
                                    self.datachannel.source.put(pickle.dumps(control_status))

                        if event.type == pygame.JOYHATMOTION:
                            hat = joystick.get_hat(0)
                            pan = hat[0]*5
                            tilt = hat[1]*5
                            self.control_status["LEFT"] = pan
                            self.control_status["RIGHT"] = tilt
                            self.control_status["HEADER"] = 'C'
                            if pan * tilt < -0.5:
                                self.control_status["HEADER"] = 'D'
                            control_status = (
                                self.control_status["HEADER"], self.control_status["LEFT"], self.control_status["RIGHT"], self.gear)
                            self.command_sig.emit(control_status)
                            self.datachannel.source.put(pickle.dumps(control_status))
                                
                except Exception as e:
                    print(e)
                sleep(0.04)
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
    
    def switch_cammode(self, mode):
        if mode == "Data saving":
            self.datachannel.source.put(pickle.dumps(("V", 0, 0, 0)))
        
        elif mode == "Normal":
            self.datachannel.source.put(pickle.dumps(("N", 0, 0, 0)))
    
    def switch_mirror(self):
        print("Starting mirror")
        self.datachannel.source.put(pickle.dumps(("K", 0, 0, 0)))
    



