# gui.py

import sys
from PyQt6 import QtWidgets, QtCore
from labjack_interface import LabJackInterface

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor sensores motor")
        self.lj = LabJackInterface()
        self.init_ui()
        # Timer para actualizar cada 500 ms
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_readings)
        self.timer.start(500)

    def init_ui(self):
        layout = QtWidgets.QFormLayout()

        self.lbl_Tentrada = QtWidgets.QLabel("-")
        self.lbl_Tambiente = QtWidgets.QLabel("-")
        self.lbl_RPM = QtWidgets.QLabel("-")
        self.lbl_Caudal = QtWidgets.QLabel("-")
        self.lbl_Par = QtWidgets.QLabel("-")
        self.lbl_Presion = QtWidgets.QLabel("-")

        layout.addRow("Tentrada (°C):", self.lbl_Tentrada)
        layout.addRow("Tambiente (°C):", self.lbl_Tambiente)
        layout.addRow("RPM:", self.lbl_RPM)
        layout.addRow("Caudal:", self.lbl_Caudal)
        layout.addRow("Par (Nm):", self.lbl_Par)
        layout.addRow("Presión:", self.lbl_Presion)

        self.setLayout(layout)

    def update_readings(self):
        vals = self.lj.read_sensors()
        if vals:
            # Formatear los valores
            self.lbl_Tentrada.setText(f"{vals['Tentrada']:.2f}")
            self.lbl_Tambiente.setText(f"{vals['Tambiente']:.2f}")
            self.lbl_RPM.setText(f"{vals['RPM']:.0f}")
            self.lbl_Caudal.setText(f"{vals['Caudal']:.3f}")
            self.lbl_Par.setText(f"{vals['Par']:.3f}")
            self.lbl_Presion.setText(f"{vals['Presion']:.3f}")
        else:
            # Si falla la lectura, quizá mostrar guión o mensaje
            self.lbl_Tentrada.setText("-")
            self.lbl_Tambiente.setText("-")
            self.lbl_RPM.setText("-")
            self.lbl_Caudal.setText("-")
            self.lbl_Par.setText("-")
            self.lbl_Presion.setText("-")

    def closeEvent(self, event):
        self.lj.close()
        event.accept()

def run_app():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_app()
