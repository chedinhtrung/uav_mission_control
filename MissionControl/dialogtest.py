import sys
import math
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QBrush, QColor
from PyQt5.QtWidgets import QApplication, QMainWindow
from QCustomPlot_PyQt5 import QCustomPlot, QCP


app = QApplication(sys.argv)
window = QMainWindow()
window.resize(800, 600)

customPlot = QCustomPlot()
window.setCentralWidget(customPlot)

graph0 = customPlot.addGraph()
graph0.setPen(QPen(Qt.blue))
graph0.setBrush(QBrush(QColor(0, 0, 255, 20)))

graph1 = customPlot.addGraph()
graph1.setPen(QPen(Qt.red))

x, y0, y1 = [], [], []
for i in range (251):
    x.append(i)
    y0.append(math.exp(-i/150.0)*math.cos(i/10.0))  # exponentially decaying cosine
    y1.append(math.exp(-i/150.0))                   # exponential envelope

graph0.setData(x, y0)
graph1.setData(x, y1)

customPlot.rescaleAxes()


window.show()
sys.exit(app.exec_())