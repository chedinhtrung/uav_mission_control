from VideoConnector import MirrorConnector
from UDPVideoConnector import VideoConnector
from Network.UdpDataChannel import UdpDataChannel
from config import *
from queue import Queue
from Command import Command
from Telemetry import Telemetry
from Logger.MissionControl_Logger import MCLogger
from Network.TcpDataChannel import TcpDataChannel

class MissionControlCore:
    def __init__(self, ui):
        
        self.telemetry_datachannel = UdpDataChannel(source=Queue(), sink=Queue(), remote_host=telemetry_datachannel["remote_host"])
        #self.video_connector = VideoConnector(self.video_cmd_datachannel, config=video, name="Main Video Feed")
        #self.video_datachannel = TcpDataChannel(source=Queue(), sink=Queue(), remote_host=tcp_gateB, send=False)
        self.video_datachannel = UdpDataChannel(source=Queue(), sink=Queue(), remote_host=video_cmd_datachannel["remote_host"], send=False)
        self.video_connector = VideoConnector(self.video_datachannel, config=video, name="Main Video Feed")
        self.videodisplay = ui.maintab.videodisplay
        self.videodisplay.set_videosource(self.video_connector)
        self.command = Command(self.telemetry_datachannel)
        self.telemetry = Telemetry(datachannel=self.telemetry_datachannel)
        MCLogger.set_logging_element(ui.flightindicator.logdisplay)
        ui.flightindicator.set_backend(self.telemetry)
        self.networkstatus = ui.maintab.networkstatusbar
        self.telemetry.signal_telemetry.connect(self.networkstatus.update)

    def start(self):
        self.video_datachannel.start()
        self.telemetry.start()
        self.telemetry_datachannel.start()
        self.video_connector.start()
        self.command.start()

    def stop(self):
        self.video_connector.destroy()
        self.telemetry_datachannel.destroy()
        self.command.stop()
        self.telemetry.stop()
        self.video_datachannel.destroy()
    


