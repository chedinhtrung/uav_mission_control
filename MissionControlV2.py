import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))
import time
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QPen, QPainter, QSurfaceFormat
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtWidgets import (QLabel, QTextEdit, QProgressBar, \
                             QApplication, QHBoxLayout, QVBoxLayout, 
                             QWidget, QSizePolicy, QGridLayout, QPushButton, 
                             QMenuBar, QDialog, QAction, QSpacerItem, QRadioButton,
                             QDoubleSpinBox, QSpinBox, QComboBox, QLineEdit,
                             QTabWidget, QTabBar, QMenu, QFrame, QStyle, QStyleOption, QStackedLayout)
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QSize
from MissionControl.CoreTcp import MissionControlCore
from config import *
import sys
from MissionControl.Command import Command
from MissionControl.Tools.network.NetworkGrapher import NetworkGraphTab
from MissionControl.Tools.qterminal.widget import QTerminalTab
from MissionControl.FlightDisplay import QPrimaryFlightDisplay
import uuid


class VideoDisplay(QLabel):
    def __init__(self, video_source=None):   
        QLabel.__init__(self)
        self.video_source = video_source
        self.frame = "UAV NOT CONNECTED"
        self.setText(self.frame)
        #self.resize(640, 480)
        self.setStyleSheet("border:2px solid #2A2A2A; background-color:#181818;")
        self.setAlignment(Qt.AlignCenter)
        if self.video_source is not None:
            self.video_source.frame_signal.connect(self.update_frame)

        #self.flightdisplay = QPrimaryFlightDisplay(self) 
        #self.resizeEvent = lambda event: self.resize_overlay(event, self, self.flightdisplay)
    
    def update_frame(self, pixmap):
        self.setPixmap(pixmap)
    
    def set_videosource(self, videosource):
        self.video_source = videosource
        self.video_source.frame_signal.connect(self.update_frame)
        videosource.display = self
    
    def resize_overlay(self, event, bottom_widget, top_widget): 
        top_widget.resize(bottom_widget.size()/2)
        top_x = (bottom_widget.width() - top_widget.width()) // 2
        top_y = (bottom_widget.height() - top_widget.height()) // 2
        top_widget.move(top_x, top_y)          

class MapDisplay(QWebEngineView):
    def __init__(self):
        QWebEngineView.__init__(self)
        local_path = os.path.dirname(os.path.abspath(__file__))
        relative_path = 'MissionControl/googlemaps.html'
        map_path = os.path.join(local_path, relative_path)
        html = None
        # Load GGMaps API key
        with open(map_path, "r") as file:
            html = file.read()
            html = html.replace("{{API_KEY}}", MAPS_API_KEY)
        with open(map_path, "w") as file:
            file.write(html)
        self.load(QUrl.fromLocalFile(map_path))
        self.last_update = time.time()
        self.setStyleSheet("background: transparent;")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.settings().setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.WebGLEnabled, True)

        # Set other performance-related settings
        self.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)

        self.lons = []
        self.lats = []

    def updateDroneLocation(self, data):
        if not data["Online"]:
            return
        time_elapsed = time.time() - self.last_update
        #print(time_elapsed)
        if time_elapsed > 1: 
            self.last_update = time.time()
            if len(self.lons) > 0 and len(self.lats) > 0:
                lon = sum(self.lons)/len(self.lons)
                lat = sum(self.lats)/len(self.lats)

                if not (lon == 0 and lat == 0): #Check for null glitch
                    self.last_update = time.time()
                    script = f"update_location({lon}, {lat});"
                    # Update the marker on the map to reflect the new drone location
                    self.page().runJavaScript(script) 
            self.lons = []
            self.lats = []
        
        else: 
            if not (data["Lon"] < 0.01 and data["Lat"] < 0.01):
                self.lons.append(data["Lon"])
                self.lats.append(data["Lat"])
                #print(self.lons, self.lats)
    
    def set_mapupdater(self, mapupdater):
        self.updater = mapupdater
        mapupdater.signal_telemetry.connect(self.updateDroneLocation)
    
    def remove_api_key(self):
        #kill the API key
        local_path = os.path.dirname(os.path.abspath(__file__))
        relative_path = 'MissionControl/googlemaps.html'
        map_path = os.path.join(local_path, relative_path)
        with open(map_path, "r") as file:
            html = file.read()
            html = html.replace(MAPS_API_KEY, "{{API_KEY}}")
        with open(map_path, "w") as file:
            file.write(html)


class ServerLogDisplay(QTextEdit):
    def __init__(self):
        QTextEdit.__init__(self)
        self.setReadOnly(True)
        self.setStyleSheet("border:2px solid #2A2A2A; background-color:#181818; padding:10px; color: #CCCCBB;")
        self.log("Initializing...")

    def log(self, message):
        self.append(f"{time.strftime('%H:%M:%S', time.localtime())} {message}")


    def update(self, data):
        if not data is None:
            self.text.setText(str(data))
            self.text.adjustSize()

class RoverConfigDialog(QDialog):
    def __init__(self, configurator):
        super().__init__()
        self.configurator = configurator

        self.setWindowTitle("Rover configuration")
        layout = QVBoxLayout()

        row1 = QGridLayout()
        row1.setSpacing(10)
        self.sleep_enabled = QRadioButton()
        row1.addWidget(QLabel("Go to sleep"), 0, 0)
        row1.addWidget(self.sleep_enabled, 0, 1)
        row1.addWidget(QLabel("After"), 0, 2)
        self.sleep_after_duration = QDoubleSpinBox()
        row1.addWidget(self.sleep_after_duration, 0, 3)

        row1.addWidget(QLabel("Main camera: "), 1, 0)
        row1.addWidget(QLabel("Resolution"), 2, 1)
        self.resolutions = QComboBox()
        self.resolutions.addItem("640x480")
        self.resolutions.addItem("1080x720")
        row1.addWidget(self.resolutions, 2, 2)
        row1.addWidget(QLabel("Framerate"), 3, 1)
        self.framerate = QSpinBox()
        row1.addWidget(self.framerate, 3, 2)
        self.picture_qual = QSpinBox()
        row1.addWidget(QLabel("Image quality"), 4, 1)
        row1.addWidget(self.picture_qual, 4, 2)

        row1.addWidget(QLabel("Hosts:"), 5, 0)
        row1.addWidget(QLabel("Video"), 6, 1)
        self.videohost = QLineEdit()
        row1.addWidget(self.videohost, 6,2)
        self.videoport = QLineEdit()
        row1.addWidget(self.videoport, 6,3)
        row1.addWidget(QLabel("Telemetry"), 7, 1)
        self.telemetryhost = QLineEdit()
        row1.addWidget(self.telemetryhost, 7,2)
        self.telemetryport = QLineEdit()
        row1.addWidget(self.telemetryport, 7,3)

        layout.addLayout(row1)

        bottom_row = QHBoxLayout()
        bottom_row.addItem(QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum))
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        ok_button.setFixedWidth(80)
        bottom_row.addWidget(ok_button)
        bottom_row.addItem(QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(bottom_row)

        self.setLayout(layout)   
        self.action = QAction(self)
    
    def accept(self) -> None:
        
        return super().accept()

class ToolsMenu(QMenu):
    def __init__(self, title, parent):
        super().__init__(title, parent)
        self.setTitle(title)
        self.parent = parent
        menu_style = """
            QMenu {
                background-color: #1F1F1F;
                color: #CCCCBB;
            }
            QMenu::item {
                background-color: 1F1F1F;
            }
            QMenu::item:selected {
                background-color: #37373D;
            }
        """
        network_view = QAction("Network monitor", self)
        self.setStyleSheet(menu_style)
        network_view.triggered.connect(self.show_network_monitor) #TODO: add network view
        self.addAction(network_view)
        recorder = QAction("Recorder", self)
        self.addAction(recorder)
        ssh = QAction("SSH", self)
        ssh.triggered.connect(self.show_ssh_commandline)
        self.addAction(ssh)
        missionplaner = QAction("Mission planer", self)
        self.addAction(missionplaner)
    
    def show_network_monitor(self):
        self.parent.tabbar.addTab(NetworkGraphTab(), "Network")

    def show_ssh_commandline(self):
        terminal = QTerminalTab()
        self.parent.tabbar.addTab(terminal, "SSH")   

class MenuBar(QMenuBar):
    configurator = None
    def __init__(self, parent, scale=1):
        QMenuBar.__init__(self)
        self.parent = parent
        self.tools = self.addMenu(ToolsMenu("Tools", self.parent))
        self.config = self.addMenu("Config")
        self.view = self.addMenu("View")
        self.setFixedHeight(int(60*scale))
        self.setStyleSheet("""
            QMenuBar {
                background-color: #181818;
                color: #CCCCBB;
                padding-left: 20px;
                padding-top: 10px;
            }
            QMenuBar::item:selected {
                background-color: #37373D;
                color: #CCCCBB;
            }
            QMenuBar::item:pressed {
                background-color: #37373D;
                color: #CCCCBB;
            }
        """)
        menu_style = """
            QMenu {
                background-color: #1F1F1F;
                color: #CCCCBB;
            }
            QMenu::item {
                background-color: 1F1F1F;
            }
            QMenu::item:selected {
                background-color: #37373D;
            }
        """
        self.config.setStyleSheet(menu_style)
        config = QAction("Rover", self)
        config.triggered.connect(self.show_config)
        # Add the action to the Help menu
        self.config.addAction(config)

    def show_config(self):
        dialog = RoverConfigDialog(self.configurator)
        dialog.exec_()

class TopBar(QWidget):
    def __init__(self, parent, scale=1):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("TopBar")
        self.setStyleSheet("#TopBar { border-bottom: 2px solid #262626; }")
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.addWidget(MenuBar(self.parent, scale), 1)
        minimize = QPushButton()
        minimize.setFixedSize(int(90*scale),int(60*scale))
        minimize.setText("__")
        minimize.setStyleSheet("QPushButton:hover {background-color: #595958;} QPushButton{font-weight:bold}")
        minimize.clicked.connect(self.parent.minimizeWindow)
        layout.addWidget(minimize)
        close_button = QPushButton()
        close_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources/close.png")))
        close_button.setStyleSheet("QPushButton {background-color:darkred; padding:10px} QPushButton:hover {background-color: red;}")
        icon_size = close_button.iconSize()
        icon_size.setWidth(int(20*scale))  
        icon_size.setHeight(int(20*scale))  
        close_button.setIconSize(icon_size)
        close_button.clicked.connect(self.parent.close)
        layout.addWidget(close_button, 1)
        close_button.setFixedSize(int(90*scale),int(60*scale))
        self.setLayout(layout)
    
    def paintEvent(self, pe):
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)

class NetworkStatusBar(QWidget):
    def __init__(self, scale=1):
        QWidget.__init__(self)
        self.scale=scale
        self.image_path = os.path.join(os.path.dirname(__file__), "Resources/signal_0.png")
        layout = QHBoxLayout()
        self.signal_label = QLabel()
        self.signal_label.setFixedHeight(int(25*scale))
        self.signal_label.setFixedWidth(int(35*scale))
        #self.signal_label.setMargin(5)
        self.signal_img = QPixmap(self.image_path).scaled(int(30*scale), int(30*scale), aspectRatioMode=True)
        self.signal_label.setPixmap(self.signal_img)
        self.phonenumber = QLabel("--")
        self.network_mode = QLabel("--")
        self.network_name = QLabel("--")
        layout.addWidget(self.signal_label)
        layout.addWidget(self.network_mode)
        layout.addWidget(self.network_name)
        layout.addWidget(self.phonenumber)
        layout.setSpacing(5)
        layout.setContentsMargins(15, 0, 0, 0) 
        self.setFixedHeight(int(20*scale)) 
        self.setLayout(layout)
        self.last_update = time.time()
        #self.update({'GPS': False, 'Lon': 11.594022750854492, 'Lat': 48.126522064208984, 'Spd': 0, 'Ctl': False, 'Cam': 'Normal', 'Vol': 0.0, 'Rol': 2.8114070892333984, 'Ptc': -2.5679171085357666, 'Yaw': 201.6574249267578, 'Alt': -135.2073516845703, 'Err': [], 'Mea': False, 'Sig': {'sim_status': 'OK', 'mode': 'LTE', 'network_name': 'freenet FUNK', 'phone_number': '"+4917641639250"', 'signal_qual': '50'}, 'Online': True})

    def update(self, data):
        if time.time() - self.last_update < 1:
            return
        self.last_update = time.time()
        
        data = data.get("Sig")
        if data is None: 
            return
        if data.get("phone_number") is not None:
            self.phonenumber.setText(data.get("phone_number").replace("\"", ""))
        self.network_mode.setText(data.get("mode"))
        self.network_name.setText(data.get("network_name"))

        if data.get("signal_qual") is not None:
            quality = int(data.get("signal_qual"))

            if quality < 25:
                self.image_path = os.path.join(os.path.dirname(__file__), "Resources/signal_0.png")
                self.signal_img = QPixmap(self.image_path).scaled(int(30*self.scale), int(30*self.scale), aspectRatioMode=True)
                self.signal_label.setPixmap(self.signal_img)
            
            elif quality >= 25 and quality < 34:
                self.image_path = os.path.join(os.path.dirname(__file__), "Resources/signal_1.png")
                self.signal_img = QPixmap(self.image_path).scaled(int(30*self.scale), int(30*self.scale), aspectRatioMode=True)
                self.signal_label.setPixmap(self.signal_img)
            
            elif quality >= 34 and quality < 43:
                self.image_path = os.path.join(os.path.dirname(__file__), "Resources/signal_2.png")
                self.signal_img = QPixmap(self.image_path).scaled(int(30*self.scale), int(30*self.scale), aspectRatioMode=True)
                self.signal_label.setPixmap(self.signal_img)
            
            elif quality >= 43 and quality < 55:
                self.image_path = os.path.join(os.path.dirname(__file__), "Resources/signal_3.png")
                self.signal_img = QPixmap(self.image_path).scaled(int(30*self.scale), int(30*self.scale), aspectRatioMode=True)
                self.signal_label.setPixmap(self.signal_img)
            
            elif quality >= 55:
                self.image_path = os.path.join(os.path.dirname(__file__), "Resources/signal_4.png")
                self.signal_img = QPixmap(self.image_path).scaled(int(30*self.scale), int(30*self.scale), aspectRatioMode=True)
                self.signal_label.setPixmap(self.signal_img)

class SidebarButton(QPushButton):
    def __init__(self, icon:QIcon, window=None, manager=None, scale=1):
        QPushButton.__init__(self, icon, None)
        self.setFixedSize(int(90*scale), int(90*scale))
        icon_size = QSize(int(45*scale), int(45*scale))
        self.setIconSize(icon_size)
        self.setStyleSheet("QPushButton:hover {background-color: gray;}")
        self.widget = None
        self.slot:QStackedLayout = None
        self.selected = False
        self.manager = manager
        self.clicked.connect(self.setManagerState)
        self.id = uuid.uuid4()
        if self.manager is not None:
            self.manager.buttons.append(self)

    def setTarget(self, slot:QStackedLayout, widget):
        self.slot = slot
        self.widget = widget
        self.clicked.connect(self.toggleWidget)

    def setState(self, selected):
        self.selected = selected
        if self.selected:
            self.setStyleSheet("QPushButton {background-color: gray;}")
            if self.slot is not None and self.widget is not None: 
                self.slot.setCurrentWidget(self.widget)
        else: 
            self.setStyleSheet("QPushButton:hover {background-color: gray;}")
            if self.slot is not None and self.widget is not None: 
                self.slot.setCurrentIndex(0)

    def setManagerState(self):
        if self.manager is None:
            return 
        self.manager.setSelected(self)

    
    def toggleWidget(self):
        self.setState(not self.selected)

class SideBar(QFrame):
    def __init__(self, parent=None, scale=1):
        QFrame.__init__(self)
        self.p = parent
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.setFixedWidth(int(90*scale))
        self.setLayout(layout)
        self.setStyleSheet("background-color: #181818")

        self.buttons = []

        icon_size = QSize(int(45*scale), int(45*scale))
        self.loginbutton = SidebarButton(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources/login.png")), window=None, manager=self, scale=scale)
        self.mapbutton = SidebarButton(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources/map.png")), window=None, manager=self, scale=scale)
        self.mapbutton.setTarget(self.p.flightindicator.topslot, self.p.flightindicator.mapdisplay)
        self.offbutton = SidebarButton(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources/power.png")), window=None, manager=self, scale=scale)
        self.offbutton.setStyleSheet("QPushButton {background-color:darkred; padding:10px} QPushButton:hover {background-color: red;}")
        self.photobutton = SidebarButton(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources/photo.png")), scale=scale)
        self.photobutton.clicked.connect(self.toggle_recording)
        self.logbutton = SidebarButton(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources/log.png")), window=None, manager=self, scale=scale)
        self.logbutton.setTarget(self.p.flightindicator.topslot, self.p.flightindicator.logdisplay)
        self.controllerbutton = SidebarButton(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources/controller.png")), window=None, manager=self, scale=scale)
        self.controllerbutton.setTarget(self.p.flightindicator.topslot, self.p.flightindicator.logdisplay)
        self.launchbutton = SidebarButton(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources/launch.png")), window=None, manager=self, scale=scale)
        self.sosbutton = SidebarButton(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources/sos.png")), window=None, manager=self, scale=scale)

        layout.addWidget(self.loginbutton)
        layout.addWidget(self.mapbutton)
        layout.addWidget(self.photobutton)
        layout.addWidget(self.logbutton)
        layout.addWidget(self.controllerbutton)
        layout.addWidget(self.launchbutton)
        layout.addItem(QSpacerItem(int(20*scale), int(40*scale), QSizePolicy.Expanding, QSizePolicy.Expanding))
        layout.addWidget(self.sosbutton)
        layout.addWidget(self.offbutton)   

    def toggle_recording(self):
        if not self.p.core.recorder.active:
            self.p.core.recorder.start()
            self.photobutton.toggleWidget()
        else: 
            self.p.core.recorder.stop()  
            self.photobutton.toggleWidget()
    
    def setSelected(self, button):
        for btn in self.buttons:
            if btn.id != button.id:
                btn.setState(False)

class FlightIndicatorBar(QFrame):
    def __init__(self, scale=1):
        QFrame.__init__(self)
        layout = QVBoxLayout()
        #layout.setVerticalSpacing(5)
        layout.setContentsMargins(0,0,0,0)
        self.topslot = QStackedLayout()
        self.bottomslot = QStackedLayout()
        self.flightdisplay = QPrimaryFlightDisplay()
        self.mapdisplay = MapDisplay()
        self.logdisplay = ServerLogDisplay()
        self.topslot.addWidget(self.mapdisplay)
        self.topslot.addWidget(self.logdisplay)
        self.bottomslot.addWidget(self.flightdisplay)
        self.topslot.setCurrentWidget(self.mapdisplay)
        self.topslot.setCurrentWidget(self.flightdisplay)
        #self.topslot.setCurrentIndex(0)
        layout.addLayout(self.topslot)
        layout.addLayout(self.bottomslot)
        self.setLayout(layout)
        self.setFixedWidth(int(800*scale))
    
    def set_backend(self, backend):
        backend.signal_telemetry.connect(self.update_data)

    def update_data(self, data):
        try:
            #print(data)
            #print(data['Vol'])
            self.flightdisplay.roll = -data["Rol"]/180*3.14159
            self.flightdisplay.pitch = data["Ptc"]/180*3.14159
            self.flightdisplay.alt = data["Alt"]
            self.flightdisplay.heading = data["Yaw"]
            self.flightdisplay.battery = data["Vol"] * 3.3
            self.flightdisplay.update()
            self.mapdisplay.updateDroneLocation(data)
        except:
            pass


class MainTab(QWidget):
    def __init__(self, parent=None, scale=1):
        super().__init__()
        self.parent = parent
        self.setStyleSheet("background-color: #1F1F1F;")
        layout = QVBoxLayout()
        self.networkstatusbar = NetworkStatusBar(scale)
        layout.addWidget(self.networkstatusbar)
        wrapper = QWidget()
        wrapperlayout = QVBoxLayout()
        self.videodisplay = VideoDisplay()
        wrapperlayout.addWidget(self.videodisplay)
        wrapper.setLayout(wrapperlayout)
        #self.flightdisplay = QPrimaryFlightDisplay(wrapper) 
        layout.addWidget(wrapper)
        self.setLayout(layout)
        #self.resizeEvent = lambda event: self.resize_overlay(event, self, self.flightdisplay)
        
    def resize_overlay(self, event, bottom_widget, top_widget):
        # Calculate the position to center the top widget on the bottom widget
        top_x = (bottom_widget.width() - top_widget.width()) // 2
        top_y = (bottom_widget.height() - top_widget.height()) // 2
        top_widget.move(top_x, top_y)
        #top_widget.resize(bottom_widget.size())  # Ensure the top widget covers the bottom widget
          
class Tabbar(QTabWidget):
    def __init__(self):
        super().__init__()
        self.tabCloseRequested.connect(self.on_tab_close)
    
    def on_tab_close(self, index):
        widget = self.widget(index)
        widget.close()
    
    def addTab(self, widget:QWidget, title:str):
        super().addTab(widget, title)
        self.setCurrentIndex(self.count()-1)
        widget.index = self.count()-1
        widget.tabber = self

class Window(QWidget):
    def __init__(self):
        super().__init__()
        # Create a QHBoxLayout instance
        self.init_UI()
        self.init_logic()
        self.setWindowFlags(self.windowFlags() | 
                            Qt.FramelessWindowHint)
    
    def init_UI(self):
        self.setStyleSheet("background-color: #1F1F1F; margin:0px; padding:0px;")
        self.scale = 0.5 #TODO: dynamically configure scale based on screen size
        window = QVBoxLayout()
        window.setSpacing(0)
        window.setContentsMargins(0, 0, 0, 0)
        self.core:MissionControlCore
        #self.mapdisplay = MapDisplay()
        #self.mapdisplay.setParent(self)
        #self.mapdisplay.setFixedWidth(500)
        #self.mapdisplay.setFixedHeight(400)
        #self.mapdisplay.setVisible(False)
        #self.mapdisplay.move(60,40)

        #self.logdisplay = ServerLogDisplay()
        #self.logdisplay.setParent(self)
        #self.logdisplay.setFixedWidth(500)
        #self.logdisplay.setFixedHeight(400)
        #self.logdisplay.setVisible(False)
        #self.logdisplay.move(60,40)

        topbar = TopBar(self, scale=self.scale)
        window.addWidget(topbar)
        self.flightindicator = FlightIndicatorBar(scale=self.scale)
        row1 = QHBoxLayout()
        self.sidebar = SideBar(parent=self, scale=self.scale)
        row1.addWidget(self.sidebar)

        row1.addWidget(self.flightindicator)
        
        self.tabbar = Tabbar()
        self.tabbar.setTabsClosable(True)
        self.maintab = MainTab(parent=self)
        self.tabbar.addTab(self.maintab, "Mission Control")
      
        self.tabbar.tabBar().setTabButton(0, QTabBar.RightSide, None)
     
        self.tabbar.tabCloseRequested.connect(self.close_tab)
        row1.addWidget(self.tabbar)
        window.addLayout(row1)
        self.setLayout(window)
    
        
    def init_logic(self):  
        self.core = MissionControlCore(ui=self)
        self.core.start()
    
    def closeEvent(self, event):
        self.flightindicator.mapdisplay.remove_api_key()
        self.core.stop()
        for i in range(self.tabbar.count()):
            widget = self.tabbar.widget(i)
            widget.close()
        event.accept()
    
    def minimizeWindow(self):
        self.setWindowState(Qt.WindowMinimized)

    def showEvent(self, event):
        self.setWindowState(Qt.WindowMaximized)
        super().showEvent(event)
    
    def close_tab(self, index):
        self.tabbar.removeTab(index)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    global_scale = 0.5
    app.setStyleSheet("QLabel { color : #CCCCBB; font-size:20px; } QPushButton { color : #CCCCBB; } \
                      QTextEdit{color : #CCCCBB;} QDialog {background-color: #37373D;} \
                      QTabWidget::pane { background-color: #1F1F1F; } QTabBar { font-size: 27px;  background: white;} \
                      QTabBar::tab:selected { color: #CCCCBB; background-color: #1F1F1F; border-top: 3px solid #22A4F1; padding: 5px 10px 5px 20px;} \
                      QTabBar::tab { color: #CCCCBB; background-color: #181818; padding: 5px 10px 5px 20px;} \
                      QLineEdit {color: #CCCCBB; padding: 10px; font-size: 20px}")
    format = QSurfaceFormat()
    format.setRenderableType(QSurfaceFormat.OpenGL)
    QSurfaceFormat.setDefaultFormat(format)
    window = Window()
    window.showMaximized()
    sys.exit(app.exec_())