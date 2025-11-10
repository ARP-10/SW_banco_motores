# gui_moderno.py
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QPushButton, QSlider, QTextEdit, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QDial
)

from PyQt6.QtCore import Qt, QTimer
from labjack_interface import LabJackInterface
import pyqtgraph as pg
import time, sys, datetime
import pandas as pd

import requests  # asegúrate de tenerlo instalado: pip install requests

API_BASE_URL = "http://127.0.0.1:8000/api"  # cambia por tu IP o dominio real
MACHINE_ID = 2


class PracticePage(QWidget):
    def __init__(self, lj_interface: LabJackInterface):
        super().__init__()
        self.lj = lj_interface
        self.t0 = time.time()
        self.data_x = []
        self.data = {key: [] for key in ["Inlet Temp", "Ambient Temp", "RPM", "Air Flow", "Torque", "Pressure"]}

        # === Layout principal ===
        main_layout = QHBoxLayout()

        # =====================================================
        # 🔹 PANEL IZQUIERDO: Medidas + Control + Gráfica
        # =====================================================
        left_layout = QVBoxLayout()

        # --- Fila superior: Medidas y Control ---
        top_row = QHBoxLayout()

        # === Medidas en tiempo real ===
        self.group_meas = QGroupBox("📊 Real-Time Measurements")
        self.group_meas.setObjectName("group_lecturas")
        v_meas = QVBoxLayout()
        self.lbls = {}
        for name in ["Inlet Temp", "Ambient Temp", "RPM", "Air Flow", "Torque", "Pressure"]:
            lbl = QLabel(f"{name}: —")
            lbl.setStyleSheet("font-weight: 600; font-size: 13pt; color: #FFFFFF;")
            v_meas.addWidget(lbl)
            self.lbls[name] = lbl
        self.group_meas.setLayout(v_meas)
        top_row.addWidget(self.group_meas, stretch=2)

        # === Panel de control de datos ===
        self.group_tests = QGroupBox("🧪 Data Control")
        self.group_tests.setObjectName("group_tests")
        v_btns = QVBoxLayout()
        self.btn_save = QPushButton("💾 Save Current Data")
        self.btn_save.clicked.connect(self.save_current_data)
        self.btn_export = QPushButton("📤 Export to Excel")
        self.btn_export.clicked.connect(self.export_results)
        v_btns.addWidget(self.btn_save)
        v_btns.addWidget(self.btn_export)
        self.group_tests.setLayout(v_btns)
        top_row.addWidget(self.group_tests, stretch=2)

        left_layout.addLayout(top_row)
        left_layout.addSpacing(10)

        # === Gráfica debajo ===
        self.group_graph = QGroupBox("📈 Real-Time Graph")
        self.group_graph.setObjectName("group_grafica")
        v_graph = QHBoxLayout()

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#FFFFFF")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel("left", "Magnitude", color="#000")
        self.plot_widget.setLabel("bottom", "Time (s)", color="#000")

        self.curves = {
            "Inlet Temp": self.plot_widget.plot(pen=pg.mkPen("#3498DB", width=2)),
            "Ambient Temp": self.plot_widget.plot(pen=pg.mkPen("#9B59B6", width=2)),
            "RPM": self.plot_widget.plot(pen=pg.mkPen("#F39C12", width=2)),
            "Air Flow": self.plot_widget.plot(pen=pg.mkPen("#27AE60", width=2)),
            "Torque": self.plot_widget.plot(pen=pg.mkPen("#E74C3C", width=2)),
            "Pressure": self.plot_widget.plot(pen=pg.mkPen("#2C3E50", width=2)),
        }

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
        legend_widget = QWidget()
        legend_widget.setLayout(legend_layout)

        v_graph.addWidget(self.plot_widget, stretch=4)
        v_graph.addWidget(legend_widget, stretch=1)
        self.group_graph.setLayout(v_graph)
        left_layout.addWidget(self.group_graph, stretch=3)

        # =====================================================
        # 🔹 PANEL DERECHO: Tabla de datos (idéntica a la principal)
        # =====================================================
        right_layout = QVBoxLayout()
        self.group_table = QGroupBox("📋 Saved Measurements")
        self.group_table.setObjectName("group_tabla")

        v_table = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "#", "Date", "Time", "Inlet (°C)", "Ambient (°C)",
            "RPM", "Air Flow", "Torque (N·m)", "Pressure (Pa)"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 5)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 70)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 70)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setWordWrap(False)

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
        v_table.addWidget(self.table)
        self.group_table.setLayout(v_table)
        right_layout.addWidget(self.group_table)

        # === Combinar layout principal ===
        main_layout.addLayout(left_layout, stretch=6)
        main_layout.addLayout(right_layout, stretch=4)

        self.setLayout(main_layout)

        # --- Timer propio de la página ---
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_readings)
        self.timer.start(500)

    # ====== LÓGICA DE LA PÁGINA ======
    def update_readings(self):
        try:
            data = self.lj.read_sensors()
        except Exception:
            return
        if not data:
            return

        mapping = {
            "Inlet Temp": "Tentrada",
            "Ambient Temp": "Tambiente",
            "RPM": "RPM",
            "Air Flow": "Caudal",
            "Torque": "Par",
            "Pressure": "Presion"
        }

        t = time.time() - self.t0
        self.data_x.append(t)

        for label, key in mapping.items():
            value = data[key]
            self.lbls[label].setText(f"{label}: {value:.3f}")
            self.data[label].append(value)

        for label, curve in self.curves.items():
            if self.checks[label].isChecked():
                curve.setData(self.data_x, self.data[label])
            else:
                curve.clear()

    def update_curve_visibility(self):
        for name, curve in self.curves.items():
            if self.checks[name].isChecked():
                curve.setData(self.data_x, self.data[name])
            else:
                curve.clear()

    def save_current_data(self):
        now = datetime.datetime.now()
        date, hour = now.strftime("%d/%m/%Y"), now.strftime("%H:%M:%S")
        values = [lbl.text().split(": ")[1] for lbl in self.lbls.values()]

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.table.setItem(row, 1, QTableWidgetItem(date))
        self.table.setItem(row, 2, QTableWidgetItem(hour))
        for j, val in enumerate(values):
            item = QTableWidgetItem(val)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, j + 3, item)

    def export_results(self):
        rows = []
        for i in range(self.table.rowCount()):
            row = {}
            for j, header in enumerate([
                "#", "Date", "Time", "Inlet (°C)", "Ambient (°C)",
                "RPM", "Air Flow", "Torque (N·m)", "Pressure (Pa)"
            ]):
                item = self.table.item(i, j)
                row[header] = item.text() if item else ""
            rows.append(row)
        if not rows:
            QMessageBox.warning(self, "No data", "There is no data to export.")
            return

        df = pd.DataFrame(rows)
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel File", "practice_data.xlsx", "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".xlsx"):
            file_path += ".xlsx"
        df.to_excel(file_path, index=False, engine="openpyxl")
        QMessageBox.information(self, "Export Successful", f"File saved at:\n{file_path}")





class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Engine Test Bench TD 01.2")
        self.resize(1700, 800)

        self.lj = LabJackInterface()

        # --- Configuración API ---
        self.run_id = None
        self.local_results = []

        self.motor_on = False
        self.t0 = time.time()

        # --- UI setup ---
        self.init_ui()

        self.start_run_on_server()

        # --- Timer for real-time readings ---
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_readings)
        self.timer.start(500)

        self.data_x = []
        self.data = {key: [] for key in ["Inlet Temp", "Ambient Temp", "RPM", "Air Flow", "Torque", "Pressure"]}


    def start_run_on_server(self):
        """Crea un registro de ejecución (run) en el servidor."""
        try:
            response = requests.post(f"{API_BASE_URL}/runs/start", json={
                "machine_id": MACHINE_ID,
                "app_version": "1.0.0"
            })
            if response.status_code == 201:
                self.run_id = response.json().get("run_id")
                self.log(f"✅ Run iniciado en el servidor: {self.run_id}")
            else:
                self.log(f"⚠️ Error al crear run: {response.text}")
        except Exception as e:
            self.log(f"❌ Error de conexión a la API: {e}")


    # =====================================================
    # UI SETUP
    # =====================================================
    def init_ui(self):
        # === BARRA SUPERIOR PERMANENTE ===
        self.top_bar = QWidget()
        self.top_bar.setFixedHeight(45)
        self.top_bar.setStyleSheet("""
            QWidget {
                background-color: #0077b6;
                border-bottom: 2px solid #005f99;
            }
            QPushButton {
                background-color: transparent;
                color: white;
                font: 600 11pt "Segoe UI";
                padding: 6px 20px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0096c7;
            }
            QPushButton:pressed {
                background-color: #00b4d8;
            }
        """)

        # --- Botones Home y Practice ---
        self.btn_home = QPushButton("🏠 Home")
        self.btn_practice = QPushButton("🧩 Practice")
        self.btn_home.clicked.connect(self.back_to_home_view)
        self.btn_practice.clicked.connect(self.open_practice_view)

        bar_layout = QHBoxLayout()
        bar_layout.setContentsMargins(10, 0, 0, 0)
        bar_layout.setSpacing(0)  # 🔹 Pegados
        bar_layout.addWidget(self.btn_home)
        bar_layout.addWidget(self.btn_practice)
        bar_layout.addStretch()  # 🔹 Empuja todo a la izquierda
        self.top_bar.setLayout(bar_layout)

        # === CONTENEDOR CAMBIANTE (área de contenido) ===
        self.content_container = QWidget()
        self.home_view = self.create_home_view()   # Creamos la vista Home como función aparte
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.addWidget(self.home_view)
        self.content_container.setLayout(self.content_layout)

        # === Layout global (barra + contenido) ===
        global_layout = QVBoxLayout()
        global_layout.setContentsMargins(0, 0, 0, 0)
        global_layout.setSpacing(0)
        global_layout.addWidget(self.top_bar)
        global_layout.addWidget(self.content_container)

        container = QWidget()
        container.setLayout(global_layout)
        self.setCentralWidget(container)

        # --- Timer general ---
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_readings)
        self.timer.start(500)


    def create_home_view(self):
        """Crea la vista principal (Home) y la devuelve como QWidget."""
        main_layout = QVBoxLayout()

        # === FILA SUPERIOR ===
        top_row = QHBoxLayout()

        # --- Grupo de medidas ---
        self.group_meas = QGroupBox("📊 Real-Time Measurements")
        self.group_meas.setObjectName("group_lecturas")
        v_meas = QVBoxLayout()
        self.lbls = {}
        for name in ["Inlet Temp", "Ambient Temp", "RPM", "Air Flow", "Torque", "Pressure"]:
            lbl = QLabel(f"{name}: —")
            lbl.setStyleSheet("font-weight: 600; font-size: 13pt; color: #FFFFFF;")
            v_meas.addWidget(lbl)
            self.lbls[name] = lbl
        self.group_meas.setLayout(v_meas)
        top_row.addWidget(self.group_meas, 2)

        # --- Control del equipo ---
        self.group_control = QGroupBox("⚙️ Equipment Control")
        v_ctrl = QVBoxLayout()
        self.btn_motor = QPushButton("🔴 Motor OFF")
        self.btn_motor.clicked.connect(self.toggle_motor)
        self.btn_auto = QPushButton("🤖 Start Automatic Test")
        self.btn_auto.clicked.connect(self.start_auto_test)
        self.btn_stop_auto = QPushButton("⏹ Stop Test")
        self.btn_stop_auto.clicked.connect(self.stop_auto_test)
        self.btn_stop_auto.setEnabled(False)
        v_ctrl.addWidget(self.btn_motor)
        v_ctrl.addWidget(self.btn_auto)
        v_ctrl.addWidget(self.btn_stop_auto)
        self.group_control.setLayout(v_ctrl)
        top_row.addWidget(self.group_control, 2)

        # --- Tacómetro (Dial visual para RPM) ---
        self.group_rpm = QGroupBox("🧭 RPM Gauge")
        v_rpm = QVBoxLayout()
        self.rpm_dial = QDial()
        self.rpm_dial.setRange(0, 3600)
        self.rpm_dial.setNotchesVisible(True)
        self.rpm_dial.setWrapping(False)
        self.rpm_dial.setEnabled(False)
        self.rpm_dial.setFixedSize(200, 200)
        self.lbl_rpm_value = QLabel("0 RPM")
        self.lbl_rpm_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_rpm_value.setStyleSheet("font-weight: 700; font-size: 13pt; color: #000;")
        v_rpm.addWidget(self.rpm_dial, alignment=Qt.AlignmentFlag.AlignCenter)
        v_rpm.addWidget(self.lbl_rpm_value)
        self.group_rpm.setLayout(v_rpm)
        top_row.addWidget(self.group_rpm, 3)

        # --- Barra vertical de freno ---
        self.group_brake = QGroupBox("🧱 Brake Control")
        self.group_brake.setObjectName("group_brake")
        v_brake = QVBoxLayout()

        # --- Slider vertical con estilo visual mejorado ---
        self.slider_brake = QSlider(Qt.Orientation.Vertical)
        self.slider_brake.setRange(0, 50)
        self.slider_brake.setValue(0)
        self.slider_brake.valueChanged.connect(self.update_brake)
        self.slider_brake.setFixedHeight(180)
        self.slider_brake.setStyleSheet("""
            QSlider::groove:vertical {
                background: #A5D8FF;
                border-radius: 4px;
                width: 8px;
                margin: 10px 0;
            }
            QSlider::handle:vertical {
                background: #0077b6;
                border: 2px solid #005f87;
                height: 18px;
                width: 18px;
                margin: -4px -5px;
                border-radius: 9px;
            }
            QSlider::handle:vertical:hover {
                background: #0096d1;
            }
        """)

        # --- Etiqueta con fondo blanco y texto centrado ---
        self.lbl_brake = QLabel("Brake: 0.0 V")
        self.lbl_brake.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_brake.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 10px;
            padding: 6px 10px;
            color: #0077b6;
            font: 600 11pt "Segoe UI";
        """)

        v_brake.addStretch()
        v_brake.addWidget(self.slider_brake, alignment=Qt.AlignmentFlag.AlignHCenter)
        v_brake.addSpacing(10)
        v_brake.addWidget(self.lbl_brake, alignment=Qt.AlignmentFlag.AlignHCenter)
        v_brake.addStretch()

        self.group_brake.setLayout(v_brake)
        top_row.addWidget(self.group_brake, 1)


        # === FILA INFERIOR ===
        bottom_row = QHBoxLayout()

        # --- Gráfica ---
        self.group_graph = QGroupBox("📈 Real-Time Graph")
        self.group_graph.setObjectName("group_grafica")

        v_graph = QHBoxLayout()

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#FFFFFF")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel("left", "Magnitude", color="#000")
        self.plot_widget.setLabel("bottom", "Time (s)", color="#000")

        self.curves = {
            "Inlet Temp": self.plot_widget.plot(pen=pg.mkPen("#3498DB", width=2)),
            "Ambient Temp": self.plot_widget.plot(pen=pg.mkPen("#9B59B6", width=2)),
            "RPM": self.plot_widget.plot(pen=pg.mkPen("#F39C12", width=2)),
            "Air Flow": self.plot_widget.plot(pen=pg.mkPen("#27AE60", width=2)),
            "Torque": self.plot_widget.plot(pen=pg.mkPen("#E74C3C", width=2)),
            "Pressure": self.plot_widget.plot(pen=pg.mkPen("#2C3E50", width=2)),
        }

        # --- Leyenda lateral con checkboxes ---
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

        legend_widget = QWidget()
        legend_widget.setLayout(legend_layout)

        v_graph.addWidget(self.plot_widget, stretch=4)
        v_graph.addWidget(legend_widget, stretch=1)
        self.group_graph.setLayout(v_graph)
        bottom_row.addWidget(self.group_graph, 7)


        # --- Logs ---
        self.group_logs = QGroupBox("🧾 Logs")
        self.group_logs.setObjectName("group_logs")  
        v_logs = QVBoxLayout()

        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("background: transparent; font: 10pt 'Consolas'; color: #FFFFFF;")

        v_logs.addWidget(self.txt_logs)
        self.group_logs.setLayout(v_logs)
        bottom_row.addWidget(self.group_logs, 3)


        # === COMBINAR TODO ===
        main_layout.addLayout(top_row, 5)
        main_layout.addLayout(bottom_row, 5)

        widget = QWidget()
        widget.setLayout(main_layout)
        return widget



    def open_practice_view(self):
        if hasattr(self, "timer"):
            self.timer.stop()

        self.practice_page = PracticePage(self.lj)
        self.practice_page.setStyleSheet(self.styleSheet())

        # Reemplazar el contenido de la zona central (no toda la ventana)
        for i in reversed(range(self.content_layout.count())):
            w = self.content_layout.takeAt(i).widget()
            if w:
                w.setParent(None)
        self.content_layout.addWidget(self.practice_page)


    def back_to_home_view(self):
        if hasattr(self, "practice_page") and hasattr(self.practice_page, "timer"):
            self.practice_page.timer.stop()
            self.practice_page.deleteLater()
            del self.practice_page

        for i in reversed(range(self.content_layout.count())):
            w = self.content_layout.takeAt(i).widget()
            if w:
                w.setParent(None)
        self.content_layout.addWidget(self.home_view)
        if hasattr(self, "timer"):
            self.timer.start(500)



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
        self.lbl_brake.setText(f"Brake: {voltage:.1f} V")

        # Color dinámico según nivel
        if value < 15:
            color = "#4CAF50"  # Verde
        elif value < 35:
            color = "#FFC107"  # Amarillo
        else:
            color = "#F44336"  # Rojo

        self.dial_brake.setStyleSheet(f"""
            QDial {{
                background: qradialgradient(
                    cx: 0.5, cy: 0.5, fx: 0.5, fy: 0.5,
                    radius: 0.9,
                    stop: 0 #1E1E1E,
                    stop: 0.7 #2C2C2C,
                    stop: 1 {color}
                );
                border: 2px solid {color};
                border-radius: 80px;
            }}
        """)

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
        

        # Actualizar curvas activas
        for label, curve in self.curves.items():
            if self.checks[label].isChecked():
                curve.setData(self.data_x, self.data[label])
            else:
                curve.clear()

        self.rpm_dial.setValue(int(data["RPM"]))
        self.lbl_rpm_value.setText(f"{data['RPM']:.0f} RPM")

        # --- Guardar localmente para envío posterior ---
        if self.run_id:
            self.local_results.append({
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "metrics": {
                    "Inlet_Temp": data["Tentrada"],
                    "Ambient_Temp": data["Tambiente"],
                    "RPM": data["RPM"],
                    "Air_Flow": data["Caudal"],
                    "Torque": data["Par"],
                    "Pressure": data["Presion"]
                }
            })


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

                # --- Simulación temporal si no hay LabJack conectado ---
                try:
                    data = self.lj.read_sensors()
                except Exception:
                    data = None

                samples.append(data)
                time.sleep(0.2)


            if not samples:
                continue

            # Calcular promedios
            avg = {k: sum(d[k] for d in samples) / len(samples) for k in samples[0]}
            avg["Brake (%)"] = point
            self.results.append(avg)
            self.log(f"📊 Point {point}% → RPM={avg['RPM']:.1f}, Torque={avg['Par']:.2f}")

            now = datetime.datetime.now()
            date = now.strftime("%d/%m/%Y")
            hour = now.strftime("%H:%M:%S")

            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            # Número de registro
            self.table.setItem(row_position, 0, QTableWidgetItem(str(row_position + 1)))
            self.table.setItem(row_position, 1, QTableWidgetItem(date))
            self.table.setItem(row_position, 2, QTableWidgetItem(hour))

            # 🔹 Insertar las variables promedio (mismo orden que en la tabla)
            values = [
                f"{avg['Tentrada']:.3f}",
                f"{avg['Tambiente']:.3f}",
                f"{avg['RPM']:.1f}",
                f"{avg['Caudal']:.3f}",
                f"{avg['Par']:.3f}",
                f"{avg['Presion']:.3f}",
            ]

            for j, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_position, j + 3, item)

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
        """Cerrar conexión con LabJack y enviar datos a la API."""
        self.lj.close()

        # --- Enviar datos a la API ---
        if self.run_id and self.local_results:
            try:
                payload = {"run_id": self.run_id, "results": self.local_results}
                self.log(f"📡 Enviando {len(self.local_results)} resultados al servidor...")
                response = requests.post(f"{API_BASE_URL}/results/bulk", json=payload, timeout=10)
                if response.status_code == 201:
                    self.log("✅ Resultados enviados correctamente.")
                else:
                    self.log(f"⚠️ Error al enviar resultados: {response.status_code} {response.text}")
            except Exception as e:
                self.log(f"❌ Falló el envío a la API: {e}")

            # Cerrar el run en la API
            try:
                requests.post(f"{API_BASE_URL}/runs/{self.run_id}/end")
                self.log("🧾 Run cerrado correctamente en el servidor.")
            except Exception as e:
                self.log(f"⚠️ No se pudo cerrar el run: {e}")

        event.accept()


    # =====================================================
    # EXPORT DATA
    # =====================================================
    def export_results(self):
        try:
            rows = []

            # Si la tabla está vacía → crear una fila con número, fecha y hora actuales
            if self.table.rowCount() == 0:
                now = datetime.datetime.now()
                rows.append({
                    "#": 1,
                    "Date": now.strftime("%d/%m/%Y"),
                    "Time": now.strftime("%H:%M:%S"),
                    "Inlet (°C)": "",
                    "Ambient (°C)": "",
                    "RPM": "",
                    "Air Flow": "",
                    "Torque (N·m)": "",
                    "Pressure (Pa)": ""
                })
            else:
                # Exportar todas las filas de la tabla (aunque tengan celdas vacías)
                for i in range(self.table.rowCount()):
                    row = {}
                    for j, header in enumerate([
                        "#", "Date", "Time", "Inlet (°C)", "Ambient (°C)",
                        "RPM", "Air Flow", "Torque (N·m)", "Pressure (Pa)"
                    ]):
                        item = self.table.item(i, j)
                        row[header] = item.text() if item else ""
                    rows.append(row)

            # Crear DataFrame
            df_manual = pd.DataFrame(rows)

            # Nombre sugerido con timestamp
            suggested_name = f"practice_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            # Abrir diálogo para elegir dónde guardar
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Excel File",
                suggested_name,
                "Excel Files (*.xlsx);;All Files (*)"
            )

            # 🔹 Si el usuario canceló → salir sin mostrar mensajes
            if not file_path:
                return

            # Asegurar extensión .xlsx
            if not file_path.lower().endswith(".xlsx"):
                file_path += ".xlsx"

            # Guardar archivo
            df_manual.to_excel(file_path, index=False, engine="openpyxl")

            QMessageBox.information(self, "Export Successful", f"Results saved to:\n{file_path}")

        except Exception as e:
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
