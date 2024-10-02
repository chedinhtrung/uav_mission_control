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
import struct
import bisect

class FrameWithSequenceNr:
    def __init__(self, bytearray) -> None:
        try:
            seqnr_bytes = bytearray[-4:]
            self.seqnr = struct.unpack('>I', seqnr_bytes)[0]
            self.payload = bytearray[:-4]
        except:
            self.seqnr = -10
            self.payload = b''
    
    def __lt__(self, other):
        return self.seqnr < other.seqnr

def insertion_sort(data):
    for i in range(1, len(data)):
        key = data[i]
        j = i - 1
        while j >= 0 and key[0] < data[j][0]:
            data[j + 1] = data[j]
            j -= 1
        data[j + 1] = key
    return data

class LaneController:
    def __init__(self, source:Queue, sink:Queue):
        self.source = source
        self.sink = sink
        self.buffer = []
        self.thread = Thread(target=self.lanecontrolloop)
        self.active = True
        self.buff_size = 10
        self.current_seqnr = -1

    
    def lanecontrolloop(self):
        while self.current_seqnr < 0:
            try:
                undecoded_frame = self.source.get(timeout=2)
                frame_with_seqnr = FrameWithSequenceNr(undecoded_frame)
                self.sink.put(frame_with_seqnr.payload)
                self.current_seqnr = frame_with_seqnr.seqnr
            except: 
                pass

        while self.active:
            try:
                if len(self.buffer) == self.buff_size:
                    for entry in self.buffer:
                        self.sink.put(entry.payload)
                    self.current_seqnr = self.buffer[-1].seqnr
                    #print(f"buffer flushed: {seqnr}")
                    self.buffer = []

                undecoded_frame = self.source.get(timeout=2)
                frame_with_seqnr = FrameWithSequenceNr(undecoded_frame)
                
                #print(frame_with_seqnr.seqnr)
                if frame_with_seqnr.seqnr == self.current_seqnr + 1: 
                    self.sink.put(frame_with_seqnr.payload)
                    self.current_seqnr += 1
                    continue

                bisect.insort(self.buffer, frame_with_seqnr)
                #print(f"using buffer: {frame_with_seqnr.seqnr}")
                while len(self.buffer) > 0 and self.buffer[0].seqnr < self.current_seqnr:
                    frame = self.buffer.pop(0)
                    #print(frame.seqnr)
                
                while len(self.buffer) > 0 and self.buffer[0].seqnr == self.current_seqnr + 1:
                    frame = self.buffer.pop(0)
                    self.sink.put(frame.payload)
                    self.current_seqnr = frame.seqnr

            except Empty:
                if not self.active:
                    return
    
    def start(self):
        self.thread.start()

    def stop(self):
        self.active = False

class Decoder:
    def __init__(self, config, source: Queue, sink: Queue):
        """
        Contains the ffmpeg subprocess pipeline for decoding and returning frames
        """
        self.config = config
        self.lanecontroller = LaneController(source=source, sink=Queue())
        self.source = self.lanecontroller.sink
        self.sink = sink
        self.subprocess = None
        self.decode_inthread = Thread(target=self.decode_inloop)
        self.decode_outthread = Thread(target=self.decode_outloop)
        self.active = True
        self.buffer = []
        self.buff_size = 5 
        self.current_seqnr = -1
        ffmpeg_cmd = ['./ffmpeg.exe',
        '-err_detect', 'ignore_err', 
        #'-avioflags', 'direct',
        '-analyzeduration','0', 
        '-probesize', '32',
        '-flags', 'low_delay',
        '-hwaccel', 'cuda',
        '-fflags', 'nobuffer', 
        '-i', '-',
        '-c:v', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-f', 'rawvideo',
         #'-fps_mode', 'drop',
        '-']
        self.process = subprocess.Popen(
            ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        
        self.lanecontroller.start()
        self.start()

    def decode_inloop(self):
        """
        Continuously read from the source and write into the ffmpeg subprocess
        """
        while self.active:
            try:
                undecoded_frame = self.source.get(timeout=2)
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
    
    def start(self):
        self.decode_inthread.start()
        self.decode_outthread.start()
    
    def stop(self):
        self.active = False
        self.lanecontroller.stop()
    
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
                #print(raw_frame)
                frame = np.frombuffer(
                    raw_frame, dtype=np.uint8).reshape(self.config["height"], self.config["width"], 3)
                # Process the frame as needed (e.g., display or save)
                h, w, ch = frame.shape
                bytes_per_line = ch * w
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
      

