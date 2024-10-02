from MissionControl.VideoConnector import VideoConnector, Recorder
from Network.UdpDataChannel import UdpDataChannel
from config import *
from queue import Queue
from MissionControl.Command import Command
from MissionControl.Telemetry import Telemetry
from Logger.MissionControl_Logger import MCLogger
from Network.TcpDataChannel import TcpDataChannel
from Network.LocalTcpGateway import LocalTcpGateway

class MissionControlCore:
    def __init__(self, ui):
        
        self.video_cmd_datachannel = UdpDataChannel(source=Queue(), sink=Queue(), remote_host=video_cmd_datachannel["remote_host"])
        #self.video_connector = VideoConnector(self.video_cmd_datachannel, config=video, name="Main Video Feed")
        if mode == "local" and in_line_server:
            self.video_datachannel = LocalTcpGateway(local_gateway=local_gateway["tcp_gateA"])
        else:
            self.video_datachannel = TcpDataChannel(source=Queue(), sink=Queue(), remote_host=tcp_gateB, send=False)
        self.video_connector = VideoConnector(self.video_datachannel, config=video, name="Main Video Feed")
        self.videodisplay = ui.maintab.videodisplay
        self.videodisplay.set_videosource(self.video_connector)
        self.command = Command(self.video_cmd_datachannel)
        self.telemetry = Telemetry(datachannel=self.video_cmd_datachannel)
        MCLogger.set_logging_element(ui.flightindicator.logdisplay)
        ui.flightindicator.set_backend(self.telemetry)
        self.networkstatus = ui.maintab.networkstatusbar
        self.telemetry.signal_telemetry.connect(self.networkstatus.update)
        self.recorder = Recorder(datachannel=self.video_datachannel)

    def start(self):
        self.video_datachannel.start()
        #self.telemetry.start()
        #self.video_cmd_datachannel.start()
        self.video_connector.start()
        self.command.start()

    def stop(self):
        self.video_connector.destroy()
        self.video_cmd_datachannel.destroy()
        self.command.stop()
        self.telemetry.stop()
        self.video_datachannel.destroy()
    


