import u3
import time

class LabJackInterface:
    def __init__(self):
        try:
            self.device = u3.U3()  # abre el U3 conectado
            print("✅ LabJack U3 conectado.")

            # Configurar los canales FIO0–FIO7 como analógicos (FIO0 será digital para el motor)
            self.device.configIO(FIOAnalog=254)  # 254 = 11111110 → FIO0 digital, resto analógico
            print("🔧 FIO0 digital (motor), FIO1–FIO7 analógicos configurados.")

            # Asegurar que el motor arranque apagado
            self.device.setFIOState(0, 0)
            print("🛑 Motor OFF por seguridad al inicio.")

        except Exception as e:
            print("❌ Error al conectar LabJack U3:", e)
            self.device = None

    # =====================================================
    # READ SENSOR DATA
    # =====================================================
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
            vals["Presion"] = self.device.getAIN(6, 32)  # rango 0–3.6V

            return vals

        except Exception as e:
            print("⚠️ Error de lectura LabJack:", e)
            return None

    # =====================================================
    # COMMANDS: MOTOR & BRAKE
    # =====================================================
    def send_command(self, cmd, value=None):
        """Envía comandos al hardware (motor ON/OFF o control de freno)."""
        if self.device is None:
            print("⚠️ No hay LabJack conectado.")
            return

        try:
            if cmd == "motor_on":
                self.device.setFIOState(0, 1)
                print("🟢 Motor encendido (FIO0=1)")

            elif cmd == "motor_off":
                self.device.setFIOState(0, 0)
                print("🔴 Motor apagado (FIO0=0)")

            elif cmd == "set_brake":
                if value is None:
                    value = 0
                self.device.writeRegister(5000, value)  # DAC1 = address 5000
                print(f"⚙️ Freno ajustado a {value:.2f} V")

            else:
                print(f"❓ Comando desconocido: {cmd}")

        except Exception as e:
            print(f"❌ Error ejecutando comando {cmd}: {e}")

    # =====================================================
    def close(self):
        if self.device:
            self.device.close()
            print("🔌 LabJack cerrado.")
