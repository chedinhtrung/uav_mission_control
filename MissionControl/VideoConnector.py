import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))
from queue import Queue, Empty
import subprocess
from Network.UdpDataChannel import UdpDataChannel
from threading import Thread
import numpy as np
from config import *
from time import sleep
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import pyqtSignal, QObject, Qt
from Logger.MissionControl_Logger import MCLogger
import time
from base64 import b64decode
import cv2
from numpy import frombuffer, uint8
import datetime

class Decoder:
    def __init__(self, config, source: Queue, sink: Queue):
        """
        Contains the ffmpeg subprocess pipeline for decoding and returning frames
        """
        self.config = config
        self.source = source
        self.sink = sink
        self.subprocess = None
        self.decode_inthread = Thread(target=self.decode_inloop)
        self.decode_outthread = Thread(target=self.decode_outloop)
        self.active = True
        ffmpeg_cmd = ['./ffmpeg.exe',
        #'-err_detect', 'ignore_err', 
        '-avioflags', 'direct',
        '-analyzeduration','0', 
        '-probesize', '32',
        '-flags', 'low_delay',
        '-hwaccel', 'd3d11va',
        '-fflags', 'nobuffer', 
        '-i', '-',
        '-c:v', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-f', 'rawvideo',
         #'-fps_mode', 'drop',
        '-']
        self.process = subprocess.Popen(
            ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.start()

    def decode_inloop(self):
        """
        Continuously read from the source and write into the ffmpeg subprocess
        """
        while self.active:
            try:
                undecoded_frame = self.source.get(timeout=2)
                #print(len(undecoded_frame))
                self.process.stdin.write(undecoded_frame)
            except Empty:
                if not self.active:
                    return

    def decode_outloop(self):
        """
        Continuously read from the ffmpeg subprocess and write into the sink
        """
        frame_size = self.config["width"] * self.config["height"] * 3
        while self.active:
            try:
                decoded_frame = self.process.stdout.read(frame_size)
                self.sink.put(decoded_frame)
            except Empty:
                if not self.active:
                    return
            sleep(0)
    
    def start(self):
        self.decode_inthread.start()
        self.decode_outthread.start()
    
    def stop(self):
        self.active = False
    
    def destroy(self):
        self.stop() 
        self.process.terminate()

class VideoConnector(QObject):

    frame_signal = pyqtSignal(object)
    status_signal = pyqtSignal(str)

    def __init__(self, datachannel, config=None, name: str = ""):
        super(VideoConnector, self).__init__()
        self.datachannel = datachannel
        self.datachannel.parent = f"Video Connector {name}"
        self.config = config
        self.source = Queue()  # Decoder pushes his results here
        self.sink = Queue() # Eats frames from VideoForker
        self.decoder = Decoder(
            config=config, source=self.datachannel.sink, sink=self.source)  # Decoder eats data from datachannel
        self.streamthread = Thread(target=self.streamloop)
        self.active = True
        self.display = None

    def streamloop(self):
        MCLogger.logOK("Streaming started. Waiting for rover...")
        receiving = False
        while self.active:
            try:
                raw_frame = self.source.get(timeout=1)
                preframe = np.frombuffer(raw_frame, dtype=np.uint8).reshape(self.config["height"], self.config["width"], 3)
                frame = np.ascontiguousarray(np.fliplr(np.flipud(preframe)))
                # Process the frame as needed (e.g., display or save)
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qimage = QImage(
                    frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
                qimage = QImage(
                    frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
                if self.display is not None:
                    scaled_img = qimage.scaled(int(self.display.width()*0.99), int(self.display.height()*0.98), Qt.KeepAspectRatio)
                    pixmap = QPixmap.fromImage(scaled_img)
                    self.frame_signal.emit(pixmap)
                else: 
                    pixmap = QPixmap.fromImage(qimage)
                    self.frame_signal.emit(pixmap)
                if not receiving: 
                    MCLogger.logOK("Receiving video from rover...")
                receiving = True
            except Empty:
                if self.active:
                    pass
                else:
                    return
            except ValueError:
                pass

            except Exception as e:
                MCLogger.logError("Video error: " + e)
    
    def start(self):
        self.streamthread.start()
    
    def stop(self):
        self.active = False
        self.streamthread.join()
    
    def destroy(self):
        self.stop()
        self.decoder.destroy()

class MirrorConnector(QObject):
    frame_signal = pyqtSignal(object)
    status_signal = pyqtSignal(str)

    def __init__(self, datachannel, config=None, name: str = "mirror"):
        super(MirrorConnector, self).__init__()

        self.datachannel = datachannel
        self.datachannel.parent = f"Video Connector {name}"
        self.config = config
        self.source = self.datachannel.sink  # Decoder pushes his results here
        self.streamthread = None
        self.keepalivethread = None
        self.active = False
        self.display = None

    def streamloop(self):
        MCLogger.logOK("Streaming started. Waiting for rover...")
        receiving = False
        while self.active:
            try:
                raw_frame = self.source.get(timeout=1)
                print(len(raw_frame))
                jpeg_data = b64decode(raw_frame)
                jpeg_data = frombuffer(raw_frame, dtype=uint8)
                np_img = cv2.imdecode(jpeg_data, 1)

                # Convert the NumPy array to a QImage
                height, width, channel = np_img.shape
                bytes_per_line = channel * width
                qimage = QImage(np_img.data, width, height, bytes_per_line, QImage.Format_RGB888)
                
                self.frame_signal.emit(qimage)
                if not receiving: 
                    MCLogger.logOK("Receiving mirror from rover...")
                receiving = True
            except Empty:
                if self.active:
                    pass
                else:
                    return
            except ValueError:
                pass

            except Exception as e:
                print(e)
    
    def keepaliveloop(self):
        while self.active:
            self.datachannel.source.put('i'.encode())
            sleep(1)

    def start(self):
        if not self.datachannel.started:
            self.datachannel.start()
        self.streamthread = Thread(target=self.streamloop)
        self.keepalivethread = Thread(target=self.keepaliveloop)
        self.active = True
        self.streamthread.start()
        self.keepalivethread.start()
    
    def stop(self):
        self.active = False
        self.datachannel.stop()
        if self.streamthread is not None:
            self.streamthread.join()
    
    def destroy(self):
        self.stop()
        self.datachannel.destroy()

class Recorder:
    def __init__(self, datachannel=None):
        self.active = False
        self.datachannel = datachannel
        self.ffmpeg_command = [
            'ffmpeg',
            '-framerate', '30',
            '-hwaccel', 'cuda',
            '-f', 'h264',           # Input format is raw H.264
            '-i', '-',              # Read input from stdin
            '-c:v', 'copy',         # Copy the video codec (no re-encoding)
            './record.mp4'            # Output file
        ]
        
    def loop(self):
        while self.active:
            try:
                frame = self.source.get()
                self.process.stdin.write(frame)
            except:
                pass
    
    def start(self):
        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Drone_{current_time}.mp4"
        self.ffmpeg_command = [
            'ffmpeg',
            '-framerate', '20',
            '-hwaccel', 'cuda',
            '-f', 'h264',           # Input format is raw H.264
            '-i', '-',              # Read input from stdin
            '-c:v', 'copy',         # Copy the video codec (no re-encoding)
            f"./Recordings/{filename}"            # Output file
        ]
        if self.datachannel is not None:
            self.source = self.datachannel.get_extra_sink()
            self.active = True
        else:
            self.sink = None
            self.active = False
        self.process = subprocess.Popen(self.ffmpeg_command, stdin=subprocess.PIPE)
        self.recthread = Thread(target=self.loop)
        self.recthread.start()
    
    def stop(self):
        self.active = False
        self.process.stdin.close()

