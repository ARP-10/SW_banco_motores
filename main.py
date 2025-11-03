# main.py
from PyQt6.QtWidgets import QApplication
from gui import MainWindow, load_stylesheet  
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    load_stylesheet(app)  
    win = MainWindow()
    win.show()
    sys.exit(app.exec())