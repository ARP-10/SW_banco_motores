# gui_moderno.py
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QPushButton, QSlider, QTextEdit, QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from labjack_interface import LabJackInterface
import pyqtgraph as pg
import pandas as pd
import time, sys, datetime


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Banco de Motores TD 01.2")
        self.resize(1700, 800)

        self.lj = LabJackInterface()
        self.motor_on = False
        self.data_records = []
        self.t0 = time.time()

        # --- Crear la interfaz ---
        self.init_ui()

        # --- Timer para lecturas ---
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_readings)
        self.timer.start(500)

    # =====================================================
    # INTERFAZ
    # =====================================================
    def init_ui(self):
        main_layout = QHBoxLayout()  # 🔹 Estructura principal horizontal

        # === Panel izquierdo (lecturas, control, gráfica, botones) ===
        left_layout = QVBoxLayout()

        # --- Sección superior: lecturas + control ---
        top_layout = QHBoxLayout()

        # ----- Lecturas -----
        self.group_lecturas = QGroupBox("📊 Real-time measurements")
        self.group_lecturas.setObjectName("group_lecturas")

        grid = QVBoxLayout()
        self.lbls = {}
        for name in ["Tentrada", "Tambiente", "RPM", "Caudal", "Par", "Presion"]:
            lbl = QLabel(f"{name}: —")
            lbl.setStyleSheet("font-weight: 600; font-size: 13pt; color: #FFFFFF;")
            grid.addWidget(lbl)
            self.lbls[name] = lbl
        self.group_lecturas.setLayout(grid)

        # ----- Controles -----
        self.group_control = QGroupBox("⚙️ Equipment Control")
        v_ctrl = QVBoxLayout()

        self.btn_motor = QPushButton("🔴 Motor OFF")
        self.btn_motor.setFixedHeight(40)
        self.btn_motor.clicked.connect(self.toggle_motor)

        self.slider_brake = QSlider(Qt.Orientation.Horizontal)
        self.slider_brake.setRange(0, 50)
        self.slider_brake.setValue(0)
        self.slider_brake.valueChanged.connect(self.update_brake)
        self.lbl_brake = QLabel("Consigna de freno (DAC1): 0.0 V")

        v_ctrl.addWidget(self.btn_motor)
        v_ctrl.addWidget(self.lbl_brake)
        v_ctrl.addWidget(self.slider_brake)
        self.group_control.setLayout(v_ctrl)

        # --- Añadir ambos al mismo nivel ---
        top_layout.addWidget(self.group_lecturas, stretch=3)
        top_layout.addWidget(self.group_control, stretch=2)
        left_layout.addLayout(top_layout)

        # === Gráfica ===
        self.group_grafica = QGroupBox("📈 Real-Time Graph")
        v_graf = QVBoxLayout()
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#FFFFFF")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel("left", "Magnitud", color="#000")
        self.plot_widget.setLabel("bottom", "Tiempo (s)", color="#000")
        self.curves = {
            "RPM": self.plot_widget.plot(pen=pg.mkPen("#F39C12", width=2), name="RPM"),
            "Par": self.plot_widget.plot(pen=pg.mkPen("#27AE60", width=2), name="Par"),
        }
        v_graf.addWidget(self.plot_widget)
        self.group_grafica.setLayout(v_graf)
        left_layout.addWidget(self.group_grafica)

        # --- Botones de guardado/exportación ---
        h_btns = QHBoxLayout()
        self.btn_guardar = QPushButton("💾 Save data")
        self.btn_export = QPushButton("📤 Export")
        self.btn_guardar.clicked.connect(self.save_data)
        self.btn_export.clicked.connect(self.export_csv)
        h_btns.addStretch()
        h_btns.addWidget(self.btn_guardar)
        h_btns.addWidget(self.btn_export)
        left_layout.addLayout(h_btns)

        # === Panel derecho: tabla de datos ===
        right_layout = QVBoxLayout()
        self.group_tabla = QGroupBox("📋 Datos guardados")
        v_tabla = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["#", "Hora", "Tentrada", "Tambiente", "RPM", "Caudal", "Par", "Presion"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        v_tabla.addWidget(self.table)
        self.group_tabla.setLayout(v_tabla)
        right_layout.addWidget(self.group_tabla)

        # === Composición final ===
        main_layout.addLayout(left_layout, stretch=5)
        main_layout.addLayout(right_layout, stretch=5)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # === Datos ===
        self.data_x, self.data_rpm, self.data_par = [], [], []


    # =====================================================
    # FUNCIONES DE CONTROL
    # =====================================================
    def toggle_motor(self):
        self.motor_on = not self.motor_on
        if self.motor_on:
            self.lj.send_command("motor_on")
            self.btn_motor.setText("🟢 Motor ON")
            self.log("✅ Motor encendido (FIO0 = 1)")
        else:
            self.lj.send_command("motor_off")
            self.btn_motor.setText("🔴 Motor OFF")
            self.log("🛑 Motor apagado (FIO0 = 0)")

    def update_brake(self, value):
        voltage = value / 10.0
        self.lj.send_command("set_brake", voltage)
        self.lbl_brake.setText(f"Consigna de freno (DAC1): {voltage:.1f} V")
        self.log(f"⚙️ DAC1 actualizado → {voltage:.1f} V")

    # =====================================================
    # LECTURA DE DATOS
    # =====================================================
    def update_readings(self):
        data = self.lj.read_sensors()
        if not data:
            return
        for k, v in data.items():
            self.lbls[k].setText(f"{k}: {v:.3f}")
        t = time.time() - self.t0
        self.data_x.append(t)
        self.data_rpm.append(data["RPM"])
        self.data_par.append(data["Par"])
        self.curves["RPM"].setData(self.data_x, self.data_rpm)
        self.curves["Par"].setData(self.data_x, self.data_par)

    # =====================================================
    # GUARDADO Y LOGS
    # =====================================================
    def save_data(self):
        try:
            hora = datetime.datetime.now().strftime("%H:%M:%S")
            valores = [float(v.text().split(": ")[1].replace("—", "0")) for v in self.lbls.values()]
            self.data_records.append([hora] + valores)

            # Añadir fila a la tabla
            i = len(self.data_records)
            self.table.setRowCount(i)
            self.table.setItem(i - 1, 0, QTableWidgetItem(str(i)))
            self.table.setItem(i - 1, 1, QTableWidgetItem(hora))
            for j, val in enumerate(valores):
                self.table.setItem(i - 1, j + 2, QTableWidgetItem(f"{val:.3f}"))

            self.log("💾 Dato guardado en la tabla y memoria.")
        except Exception as e:
            self.log(f"⚠️ Error al guardar: {e}")


    def export_csv(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Sin datos", "No hay datos guardados.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar CSV", "", "CSV Files (*.csv)")
        if not path:
            return

        headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        data = []
        for r in range(self.table.rowCount()):
            fila = []
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                fila.append(item.text() if item else "")
            data.append(fila)

        df = pd.DataFrame(data, columns=headers)
        df.to_csv(path, index=False)
        QMessageBox.information(self, "Exportación", "Datos exportados correctamente.")


    # =====================================================
    def closeEvent(self, event):
        self.lj.close()
        event.accept()


# =====================================================
# EJECUCIÓN
# =====================================================
def load_stylesheet(app, path="style.qss"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print(f"[QSS] No se pudo cargar hoja de estilos: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    load_stylesheet(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
