# labjack_interface.py

import u3
import time


class LabJackInterface:
    def __init__(self):
        try:
            self.device = u3.U3()  # abre el U3 conectado
            print("✅ LabJack U3 conectado.")

            # Configurar los canales FIO0–FIO7 como analógicos
            self.device.configIO(FIOAnalog=255)  # 255 = 0b11111111 → todos analógicos
            print("🔧 Pines FIO0–FIO7 configurados como entradas analógicas.")

        except Exception as e:
            print("❌ Error al conectar LabJack U3:", e)
            self.device = None

    def read_sensors(self):
        if self.device is None:
            return None

        try:
            vals = {}
            vals["Tentrada"] = self.device.getAIN(0)
            vals["Tambiente"] = self.device.getAIN(1)
            vals["RPM"] = self.device.getAIN(5)
            vals["Caudal"] = self.device.getAIN(4)
            vals["Par"] = self.device.getAIN(7)

            # Presión con rango ampliado a 3.6V
            vals["Presion"] = self.device.getAIN(
                6,  # canal positivo (AIN6)
                32,  # canal negativo → activa el rango 0–3.6 V
            )

            return vals

        except Exception as e:
            print("⚠️ Error de lectura LabJack:", e)
            return None

    def close(self):
        if self.device:
            self.device.close()
            print("🔌 LabJack cerrado.")
