# gui_moderno.py
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QPushButton, QSlider, QTextEdit, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)

from PyQt6.QtCore import Qt, QTimer
from labjack_interface import LabJackInterface
import pyqtgraph as pg
import time, sys, datetime
import pandas as pd


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Engine Test Bench TD 01.2")
        self.resize(1700, 800)

        self.lj = LabJackInterface()
        self.motor_on = False
        self.t0 = time.time()

        # --- UI setup ---
        self.init_ui()

        # --- Timer for real-time readings ---
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_readings)
        self.timer.start(500)

    # =====================================================
    # UI SETUP
    # =====================================================
    def init_ui(self):
        main_layout = QHBoxLayout()

        # === Left panel (measurements, control, graph) ===
        left_layout = QVBoxLayout()

        # --- Top: measurements + control ---
        top_layout = QHBoxLayout()

        # ----- Measurements -----
        self.group_meas = QGroupBox("📊 Real-Time Measurements")
        self.group_meas.setObjectName("group_lecturas")

        grid = QVBoxLayout()
        self.lbls = {}
        for name in ["Inlet Temp", "Ambient Temp", "RPM", "Air Flow", "Torque", "Pressure"]:
            lbl = QLabel(f"{name}: —")
            lbl.setStyleSheet("font-weight: 600; font-size: 13pt; color: #FFFFFF;")
            grid.addWidget(lbl)
            self.lbls[name] = lbl
        self.group_meas.setLayout(grid)

        # ----- CONTROL DEL EQUIPO -----
        self.group_control = QGroupBox("⚙️ Equipment Control")
        self.group_control.setObjectName("group_control")
        v_ctrl = QVBoxLayout()

        self.btn_motor = QPushButton("🔴 Motor OFF")
        self.btn_motor.setFixedHeight(40)
        self.btn_motor.clicked.connect(self.toggle_motor)

        self.slider_brake = QSlider(Qt.Orientation.Horizontal)
        self.slider_brake.setRange(0, 50)
        self.slider_brake.setValue(0)
        self.slider_brake.valueChanged.connect(self.update_brake)
        self.lbl_brake = QLabel("Brake setpoint (DAC1): 0.0 V")

        v_ctrl.addWidget(self.btn_motor)
        v_ctrl.addWidget(self.lbl_brake)
        v_ctrl.addWidget(self.slider_brake)
        self.group_control.setLayout(v_ctrl)

        # ----- PRUEBAS AUTOMÁTICAS -----
        self.group_tests = QGroupBox("🧪 Automatic Tests")
        self.group_tests.setObjectName("group_tests")
        v_tests = QVBoxLayout()

        self.btn_auto = QPushButton("🤖 Start Automatic Test")
        self.btn_auto.clicked.connect(self.start_auto_test)

        self.btn_stop_auto = QPushButton("⏹ Stop Test")
        self.btn_stop_auto.clicked.connect(self.stop_auto_test)
        self.btn_stop_auto.setEnabled(False)

        self.btn_export = QPushButton("💾 Export Results")
        self.btn_export.clicked.connect(self.export_results)
        self.btn_export.setEnabled(False)

        self.btn_save = QPushButton("💾 Save Current Data")
        self.btn_save.clicked.connect(self.save_current_data)

        v_tests.addWidget(self.btn_auto)
        v_tests.addWidget(self.btn_stop_auto)
        v_tests.addWidget(self.btn_save)
        v_tests.addWidget(self.btn_export)

        self.group_tests.setLayout(v_tests)


        # --- Fila superior: medidas + control + pruebas ---
        top_layout.addWidget(self.group_meas, stretch=2)
        top_layout.addWidget(self.group_control, stretch=2)
        top_layout.addWidget(self.group_tests, stretch=2)
        left_layout.addLayout(top_layout)
        left_layout.addSpacing(10)



        # === Graph ===
        self.group_graph = QGroupBox("📈 Real-Time Graph")
        v_graph = QHBoxLayout()  # ← horizontal para añadir leyenda a la derecha

        # --- Plot ---
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#FFFFFF")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel("left", "Magnitude", color="#000")
        self.plot_widget.setLabel("bottom", "Time (s)", color="#000")

        # --- Curves (6 signals) ---
        self.curves = {
            "Inlet Temp": self.plot_widget.plot(pen=pg.mkPen("#3498DB", width=2)),
            "Ambient Temp": self.plot_widget.plot(pen=pg.mkPen("#9B59B6", width=2)),
            "RPM": self.plot_widget.plot(pen=pg.mkPen("#F39C12", width=2)),
            "Air Flow": self.plot_widget.plot(pen=pg.mkPen("#27AE60", width=2)),
            "Torque": self.plot_widget.plot(pen=pg.mkPen("#E74C3C", width=2)),
            "Pressure": self.plot_widget.plot(pen=pg.mkPen("#2C3E50", width=2)),
        }

        # --- Legend panel with checkboxes ---
        legend_layout = QVBoxLayout()
        legend_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        legend_layout.setSpacing(6)

        self.checks = {}
        for name, color in zip(
            self.curves.keys(),
            ["#3498DB", "#9B59B6", "#F39C12", "#27AE60", "#E74C3C", "#2C3E50"]
        ):
            cb = pg.QtWidgets.QCheckBox(name)
            cb.setChecked(True)
            cb.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 10pt;")
            cb.stateChanged.connect(self.update_curve_visibility)
            self.checks[name] = cb
            legend_layout.addWidget(cb)

        # --- Combine plot + legend ---
        v_graph.addWidget(self.plot_widget, stretch=4)
        legend_widget = QWidget()
        legend_widget.setLayout(legend_layout)
        v_graph.addWidget(legend_widget, stretch=1)
        self.group_graph.setLayout(v_graph)
        left_layout.addWidget(self.group_graph)

        # === Data storage ===
        self.data_x = []
        self.data = {key: [] for key in self.curves.keys()}

        # === Right panel: Saved Data + Logs ===
        right_layout = QVBoxLayout()

        # =====================================================
        # 🧮 TABLA DE DATOS GUARDADOS (como en it032_gui.py)
        # =====================================================
        self.group_table = QGroupBox("📋 Saved Measurements")
        self.group_table.setObjectName("group_tabla")

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "#", "Date", "Time", "Inlet Temp (°C)", "Ambient Temp (°C)",
            "RPM", "Air Flow", "Torque (N·m)", "Pressure (Pa)"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 30)

        # Stretch el resto
        for i in range(1, self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        # --- Estilo visual coherente con DIKOIN UI ---
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: none;
                alternate-background-color: #F3F7FB;
                selection-background-color: #E0F0FF;
                font-size: 10pt;
                box-shadow: 0px 6px 16px rgba(0, 0, 0, 0.08);
            }
            QHeaderView::section {
                background: #0077b6;
                color: #FFFFFF;
                font: 600 10.5pt "Segoe UI";
                padding: 8px 6px;
                border: none;
            }
        """)

        v_table = QVBoxLayout()
        v_table.addWidget(self.table)
        self.group_table.setLayout(v_table)
        right_layout.addWidget(self.group_table)

        # =====================================================
        # 🧾 SYSTEM LOGS
        # =====================================================
        self.group_logs = QGroupBox("System Logs")
        self.group_logs.setObjectName("group_logs")
        v_logs = QVBoxLayout()
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        v_logs.addWidget(self.txt_logs)
        self.group_logs.setLayout(v_logs)
        right_layout.addWidget(self.group_logs)

        # === Combine layouts ===
        main_layout.addLayout(left_layout, stretch=6)
        main_layout.addLayout(right_layout, stretch=4)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)



        self.data_x, self.data_rpm, self.data_torque = [], [], []

    # =====================================================
    # CONTROL FUNCTIONS
    # =====================================================
    def toggle_motor(self):
        self.motor_on = not self.motor_on
        if self.motor_on:
            self.lj.send_command("motor_on")
            self.btn_motor.setText("🟢 Motor ON")
            self.log("✅ Motor turned ON (FIO0 = 1)")
        else:
            self.lj.send_command("motor_off")
            self.btn_motor.setText("🔴 Motor OFF")
            self.log("🛑 Motor turned OFF (FIO0 = 0)")

    def update_brake(self, value):
        voltage = value / 10.0
        self.lj.send_command("set_brake", voltage)
        self.lbl_brake.setText(f"Brake setpoint (DAC1): {voltage:.1f} V")
        self.log(f"⚙️ DAC1 updated → {voltage:.1f} V")

    # =====================================================
    # DATA READING
    # =====================================================
    def update_readings(self):
        data = self.lj.read_sensors()
        if not data:
            return

        # Actualizar etiquetas
        mapping = {
            "Inlet Temp": "Tentrada",
            "Ambient Temp": "Tambiente",
            "RPM": "RPM",
            "Air Flow": "Caudal",
            "Torque": "Par",
            "Pressure": "Presion"
        }

        for label, key in mapping.items():
            value = data[key]
            self.lbls[label].setText(f"{label}: {value:.3f}")

        # Añadir datos nuevos
        t = time.time() - self.t0
        self.data_x.append(t)
        for label, key in mapping.items():
            self.data[label].append(data[key])
        
        # Actualizar tabla con las lecturas actuales
        i = 0
        for label in ["Inlet Temp", "Ambient Temp", "RPM", "Air Flow", "Torque", "Pressure"]:
            self.table.setItem(0, i, QTableWidgetItem(self.lbls[label].text().split(": ")[1]))
            i += 1


        # Actualizar curvas activas
        for label, curve in self.curves.items():
            if self.checks[label].isChecked():
                curve.setData(self.data_x, self.data[label])
            else:
                curve.clear()

    def update_curve_visibility(self):
        """Show/hide curves when checkboxes are toggled"""
        for name, curve in self.curves.items():
            if self.checks[name].isChecked():
                curve.setData(self.data_x, self.data[name])
            else:
                curve.clear()


    # =====================================================
    # AUTOMATIC TEST
    # =====================================================
    def start_auto_test(self):
        if not self.motor_on:
            QMessageBox.warning(self, "Motor Off", "Please turn ON the motor before starting the automatic test.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm",
            "Start the automatic test?\nThe system will apply loads automatically.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # --- Preparación ---
        self.timer.stop()
        self.abort_auto = False
        self.results = []  # limpiar resultados previos
        self.btn_stop_auto.setEnabled(True)
        self.btn_export.setEnabled(False)
        self.log("🚀 Starting automatic test...")

        brake_points = [0, 10, 20, 30, 40, 50]
        settle_time = 5
        samples_per_point = 10

        for point in brake_points:
            if self.abort_auto:
                self.log("⚠️ Automatic test aborted by user.")
                break

            voltage = point / 10.0
            self.lj.send_command("set_brake", voltage)
            self.lbl_brake.setText(f"Brake setpoint (DAC1): {voltage:.1f} V")
            self.log(f"⚙️ Applying load: {voltage:.1f} V ({point}%)")
            QApplication.processEvents()

            # Esperar estabilización con GUI viva
            for _ in range(int(settle_time * 10)):
                if self.abort_auto:
                    break
                QApplication.processEvents()
                time.sleep(0.1)

            if self.abort_auto:
                break

            # Tomar muestras
            samples = []
            for _ in range(samples_per_point):
                if self.abort_auto:
                    break
                data = self.lj.read_sensors()
                if data:
                    samples.append(data)
                time.sleep(0.2)

            if not samples:
                continue

            # Calcular promedios
            avg = {k: sum(d[k] for d in samples) / len(samples) for k in samples[0]}
            avg["Brake (%)"] = point
            self.results.append(avg)
            self.log(f"📊 Point {point}% → RPM={avg['RPM']:.1f}, Torque={avg['Par']:.2f}")

        # --- Fin del test ---
        self.lj.send_command("set_brake", 0)
        self.slider_brake.setValue(0)
        self.timer.start(500)
        self.btn_stop_auto.setEnabled(False)
        self.btn_export.setEnabled(True)

        if not self.abort_auto:
            self.log("✅ Automatic test completed.")
            QMessageBox.information(self, "Finished", "Automatic test completed successfully.")
        else:
            self.log("🟡 Test stopped before completion.")
            QMessageBox.information(self, "Stopped", "Automatic test aborted.")

    def stop_auto_test(self):
        """Permite detener el test automático de forma segura."""
        self.abort_auto = True
        self.log("🟡 Stop requested by user...")


    # =====================================================
    # LOG PANEL
    # =====================================================
    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        text = f"[{timestamp}] {message}"
        print(text)
        self.txt_logs.append(text)

    # =====================================================
    def closeEvent(self, event):
        self.lj.close()
        event.accept()

    # =====================================================
    # EXPORT DATA
    # =====================================================
    def export_results(self):

                # Si hay filas en la tabla manual → exportarlas
        if self.table.rowCount() > 0:
            rows = []
            for i in range(self.table.rowCount()):
                row = {}
                for j, header in enumerate(["Inlet Temp", "Ambient Temp", "RPM", "Air Flow", "Torque", "Pressure"]):
                    item = self.table.item(i, j)
                    row[header] = item.text() if item else ""
                rows.append(row)

            df_manual = pd.DataFrame(rows)
            filename = f"manual_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df_manual.to_excel(filename, index=False, engine="openpyxl")

            self.log(f"💾 Manual table exported to {filename}")

        if not self.results:
            QMessageBox.information(self, "No Data", "No test results to export.")
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.xlsx"

        try:
            # Crear DataFrame y exportar a Excel
            df = pd.DataFrame(self.results)
            df.to_excel(filename, index=False, engine="openpyxl")

            self.log(f"💾 Data exported to {filename}")
            QMessageBox.information(self, "Export Successful", f"Results saved to {filename}")

            

        except Exception as e:
            self.log(f"❌ Export failed: {e}")
            QMessageBox.critical(self, "Export Failed", str(e))

    def save_current_data(self):
        """Guarda una nueva fila con los valores actuales en la tabla de datos."""
        try:
            now = datetime.datetime.now()
            date = now.strftime("%d/%m/%Y")
            hour = now.strftime("%H:%M:%S")

            # Obtener lecturas actuales
            values = [
                self.lbls["Inlet Temp"].text().split(": ")[1],
                self.lbls["Ambient Temp"].text().split(": ")[1],
                self.lbls["RPM"].text().split(": ")[1],
                self.lbls["Air Flow"].text().split(": ")[1],
                self.lbls["Torque"].text().split(": ")[1],
                self.lbls["Pressure"].text().split(": ")[1],
            ]

            # Insertar nueva fila
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            # Número de registro
            self.table.setItem(row_position, 0, QTableWidgetItem(str(row_position + 1)))
            self.table.setItem(row_position, 1, QTableWidgetItem(date))
            self.table.setItem(row_position, 2, QTableWidgetItem(hour))

            # Valores de las medidas
            for j, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_position, j + 3, item)


        except Exception as e:
            self.log(f"❌ Failed to save data: {e}")
            QMessageBox.critical(self, "Save Error", str(e))



# =====================================================
# EXECUTION
# =====================================================
def load_stylesheet(app, path="style.qss"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print(f"[QSS] Stylesheet could not be loaded: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    load_stylesheet(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
