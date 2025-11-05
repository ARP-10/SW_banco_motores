# labjack_interface.py
import u3
import time


class LabJackInterface:
    def __init__(self):
        try:
            # Conexión al dispositivo
            self.device = u3.U3()
            print("✅ LabJack U3 conectado.")

            # Configurar todas las entradas FIO0–FIO7 como analógicas
            self.device.configIO(FIOAnalog=255, EIOAnalog=15)
            print("🔧 FIO0–FIO7 configurados como analógicos (entradas de medida).")

            # Mensaje de confirmación
            print(
                "📡 Sistema listo para adquisición de datos (modo analógico completo)."
            )

            # Lectura inicial para diagnóstico
            for ch in range(8):
                try:
                    v = self.device.getAIN(ch)
                    print(f"AIN{ch}: {v:.3f} V")
                except Exception as e:
                    print(f"AIN{ch}: error → {e}")

        except Exception as e:
            print("❌ Error al conectar LabJack U3:", e)
            self.device = None

    # =====================================================
    # LECTURA DE SENSORES
    # =====================================================
    def read_sensors(self):
        """Lee los sensores del banco de motores (entradas analógicas)."""
        if self.device is None:
            return None

        try:
            vals = {}
            vals["Tentrada"] = self.device.getAIN(0)  # AIN0
            vals["Tambiente"] = self.device.getAIN(1)  # AIN1
            vals["RPM"] = self.device.getAIN(5)  # AIN5
            vals["Caudal"] = self.device.getAIN(4)  # AIN4
            vals["Par"] = self.device.getAIN(7)  # AIN7
            vals["Presion"] = self.device.getAIN(6, 32)  # AIN6 (rango 0–3.6 V)

            return vals

        except Exception as e:
            print("⚠️ Error de lectura LabJack:", e)
            return None

    # =====================================================
    # COMANDO DE FRENO
    # =====================================================
    def send_command(self, cmd, value=None):
        """Envía comandos al hardware (por ahora solo el freno)."""
        if self.device is None:
            print("⚠️ No hay LabJack conectado.")
            return

        try:
            if cmd == "set_brake":
                if value is None:
                    value = 0.0
                # DAC1 = registro 5002
                self.device.writeRegister(5002, value)
                print(f"⚙️ Freno ajustado a {value:.2f} V (DAC1)")

            else:
                print(f"❓ Comando desconocido o no implementado: {cmd}")

        except Exception as e:
            print(f"❌ Error ejecutando comando {cmd}: {e}")

    # =====================================================
    # CIERRE DEL DISPOSITIVO
    # =====================================================
    def close(self):
        if self.device:
            self.device.close()
            print("🔌 LabJack cerrado correctamente.")
