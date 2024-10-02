from PyQt5.QtWidgets import (QLabel, QHBoxLayout, QVBoxLayout, 
                             QWidget, QSpacerItem)

import psutil
from PyQt5.QtCore import QTimer
from QCustomPlot_PyQt5 import QCustomPlot
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QBrush, QColor
import math

class QNetworkRollGraph(QCustomPlot):
    def __init__(self):
        super().__init__()
        self.downgraph = self.addGraph()
        self.downgraph.setPen(QPen(Qt.red))
        self.downgraph.setBrush(QBrush(QColor(255, 0, 0, 20)))
        self.upgraph = self.addGraph()
        self.upgraph.setPen(QPen(Qt.green))
        self.upgraph.setBrush(QBrush(QColor(0, 255, 0, 20)))
        self.time = [x for x in range(60)]
        self.download_dataset = [0 for i in range(60)]
        self.upload_dataset = [0 for i in range(60)]
        self.xAxis.setLabel("Time")
        self.yAxis.setLabel("Speed (kB/s)")
        background_color = QColor(24, 24, 24)
        self.setBackground(background_color)
        axis_font_color = QColor(255, 255, 255)  # White
        self.xAxis.setLabelColor(axis_font_color)
        self.yAxis.setLabelColor(axis_font_color)
        self.xAxis.setTickLabelColor(axis_font_color)
        self.yAxis.setTickLabelColor(axis_font_color)
    
    def push_data(self, download_data, upload_data):
        self.download_dataset = [download_data] + self.download_dataset[:59]
        self.upload_dataset = [upload_data] + self.upload_dataset[:59]
        self.downgraph.setData(self.time, self.download_dataset)
        self.upgraph.setData(self.time, self.upload_dataset)
        self.replot()
        self.rescaleAxes()

class NetworkStats(QWidget):
    def __init__(self):
        super().__init__()
        first_row = QHBoxLayout()
        self.upspeed = QLabel("--")
        upspeedlabel = QLabel("Upload speed: ")
        self.downspeed = QLabel("--")
        downspeedlabel = QLabel("Download speed: ")
        totallabel = QLabel("Total usage: ")
        self.total_usage = QLabel("0kB")
        first_row.addWidget(upspeedlabel)
        first_row.addWidget(self.upspeed)
        first_row.addItem(QSpacerItem(100, 10))
        first_row.addWidget(downspeedlabel)
        first_row.addWidget(self.downspeed)
        first_row.addWidget(totallabel)
        first_row.addWidget(self.total_usage)
        self.setLayout(first_row)

class NetworkGraphTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.stats = NetworkStats()
        layout.addWidget(self.stats)
        self.graph = QNetworkRollGraph()
        layout.addWidget(self.graph, 1)
        self.setLayout(layout)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_network_stats)
        self.timer.start(1000)
        self.current_sent = psutil.net_io_counters().bytes_sent
        self.current_recv = psutil.net_io_counters().bytes_recv
        self.first_usage = self.current_recv + self.current_sent
        self.index = None
        self.tabber = None
            
    def update_network_stats(self):
        net_stats = psutil.net_io_counters()
        send_speed = round((net_stats.bytes_sent - self.current_sent)/1024,2)
        self.current_sent = net_stats.bytes_sent
        self.stats.upspeed.setText(f"<html><font color='green'>↑{send_speed}</font> kB/s</html>")
        recv_speed = round((net_stats.bytes_recv - self.current_recv)/1024, 2)
        self.current_recv = net_stats.bytes_recv
        self.stats.downspeed.setText(f"<html><font color='red'>↓{recv_speed}</font> kB/s</html>")
        self.stats.total_usage.setText(f"{round((self.current_recv + self.current_sent - self.first_usage)/1024, 2)} kB")
        self.graph.push_data(download_data=recv_speed, upload_data=send_speed)
        if self.tabber is not None:
            self.tabber.setTabText(self.tabber.indexOf(self), f"↓{recv_speed} kB/s  ↑{send_speed} kB/s")
    
    def close(self):
        print("Closing network graph")
        self.timer.stop()
        
    def closeEvent(self, event):
        print("Closing network graph")
        self.timer.stop()
        event.accept()
