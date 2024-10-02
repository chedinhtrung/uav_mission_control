from PyQt5.QtGui import QIcon
import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(path))
print(os.path.dirname(path))

import sys
from PyQt5.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
from PyQt5.QtGui import QIcon

power_icon = QIcon(os.path.dirname(path) + "\power.png")

class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Create a button
        btn = QPushButton(self)
        
        # Load the PNG image and set it as the icon for the button
        
        
        btn.setIcon(QIcon(power_icon))
        
        # Set a size for the button (optional)
        btn.setIconSize(btn.sizeHint())
        
        # Set the layout
        vbox = QVBoxLayout()
        vbox.addWidget(btn)
        self.setLayout(vbox)
        
        # Set window properties
        self.setWindowTitle('Button with Image Example')
        self.setGeometry(300, 300, 300, 200)
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())
