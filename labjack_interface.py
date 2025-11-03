# labjack_interface.py

import u3
import time

class LabJackInterface:
    def __init__(self):
        try:
            self.device = u3.U3()  # abre el primer U3 que encuentra
            print("✅ LabJack U3 conectado.")
        except Exception as e:
            print("❌ Error al conectar LabJack U3:", e)
            self.device = None

    def read_sensors(self):
        """
        Lee los canales donde están conectados los sensores.
        Ajusta los números de canal AIN según tu instalación.
        Por ejemplo:
          - temperatura entrada => AIN0
          - temperatura ambiente => AIN1
          - RPM => AIN2
          - caudal => AIN3
          - par (celula de carga) => AIN4
          - presión => AIN5
        Devuelve un dict con los valores en bruto (voltajes u otro).
        """
        if self.device is None:
            return None

        try:
            vals = {}
            vals["Tentrada"]   = self.device.getAIN(0)
            vals["Tambiente"]  = self.device.getAIN(1)
            vals["RPM"]        = self.device.getAIN(2)
            vals["Caudal"]     = self.device.getAIN(3)
            vals["Par"]        = self.device.getAIN(4)
            vals["Presion"]    = self.device.getAIN(5)
            return vals
        except Exception as e:
            print("⚠️ Error de lectura LabJack:", e)
            return None

    def close(self):
        if self.device:
            self.device.close()
            print("🔌 LabJack cerrado.")
