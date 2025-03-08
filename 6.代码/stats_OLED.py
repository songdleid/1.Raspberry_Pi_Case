from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont
import time
import logging
import subprocess
import smbus

# Config Register (R/W)
_REG_CONFIG = 0x00
# SHUNT VOLTAGE REGISTER (R)
_REG_SHUNTVOLTAGE = 0x01

# BUS VOLTAGE REGISTER (R)
_REG_BUSVOLTAGE = 0x02

# POWER REGISTER (R)
_REG_POWER = 0x03

# CURRENT REGISTER (R)
_REG_CURRENT = 0x04

# CALIBRATION REGISTER (R/W)
_REG_CALIBRATION = 0x05




# 配置参数
I2C_PORT = 1
I2C_ADDRESS = 0x3C
OLED_WIDTH = 128
OLED_HEIGHT = 64
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SIZE = 10  # 减小字体大小
UPDATE_INTERVAL = 1  # 动态内容更新间隔（秒）

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 初始化OLED
def initialize_oled():
    try:
        serial = i2c(port=I2C_PORT, address=I2C_ADDRESS)
        device = sh1106(serial, width=OLED_WIDTH, height=OLED_HEIGHT)
        logging.info("OLED initialized successfully.")
        return device
    except Exception as e:
        logging.error(f"Failed to initialize OLED: {e}")
        return None

# 显示文本
def display_text(device, text_lines):
    try:
        with Image.new("1", (OLED_WIDTH, OLED_HEIGHT)) as image:
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
            y_offset = 0  # 初始垂直偏移
            for line in text_lines:
                draw.text((0, y_offset), line, font=font, fill="white")
                y_offset += FONT_SIZE  # 每行的垂直间距
            device.display(image)

    except Exception as e:
        logging.error(f"Failed to display text: {e}")

# 获取系统信息
def get_system_info():
    try:
        cmd = "hostname -I | cut -d' ' -f1"
        IP = subprocess.check_output(cmd, shell=True).decode('UTF-8', 'strict').strip()
        cmd = "top -bn1 | grep load | awk '{printf \"%.2f\",$(NF-2)}'"
        CPU = subprocess.check_output(cmd, shell=True).decode('UTF-8', 'strict').strip()
        cmd = "free -m | awk 'NR==2{printf \"%s/%sMB %.2f%%\",$3,$2,$3*100/$2 }'"
        MemUsage = subprocess.check_output(cmd, shell=True).decode('UTF-8', 'strict').strip()
        cmd = "df -h | awk '$NF==\"/\"{printf \"%d/%dGB %s\", $3,$2,$5}'"
        Disk = subprocess.check_output(cmd, shell=True).decode('UTF-8', 'strict').strip()
        Date = time.asctime(time.localtime(time.time()))
        return IP, CPU, MemUsage, Disk, Date
    except Exception as e:
        logging.error(f"Failed to get system info: {e}")
        return "N/A", "N/A", "N/A", "N/A", "N/A"
#IN
    
class BusVoltageRange:
    """Constants for ``bus_voltage_range``"""
    RANGE_16V = 0x00  # set bus voltage range to 16V
    RANGE_32V = 0x01  # set bus voltage range to 32V (default)


class Gain:
    """Constants for ``gain``"""
    DIV_1_40MV = 0x00  # shunt prog. gain set to  1, 40 mV range
    DIV_2_80MV = 0x01  # shunt prog. gain set to /2, 80 mV range
    DIV_4_160MV = 0x02  # shunt prog. gain set to /4, 160 mV range
    DIV_8_320MV = 0x03  # shunt prog. gain set to /8, 320 mV range


class ADCResolution:
    """Constants for ``bus_adc_resolution`` or ``shunt_adc_resolution``"""
    ADCRES_9BIT_1S = 0x00  # 9bit,   1 sample,     84us
    ADCRES_10BIT_1S = 0x01  # 10bit,   1 sample,    148us
    ADCRES_11BIT_1S = 0x02  # 11 bit,  1 sample,    276us
    ADCRES_12BIT_1S = 0x03  # 12 bit,  1 sample,    532us
    ADCRES_12BIT_2S = 0x09  # 12 bit,  2 samples,  1.06ms
    ADCRES_12BIT_4S = 0x0A  # 12 bit,  4 samples,  2.13ms
    ADCRES_12BIT_8S = 0x0B  # 12bit,   8 samples,  4.26ms
    ADCRES_12BIT_16S = 0x0C  # 12bit,  16 samples,  8.51ms
    ADCRES_12BIT_32S = 0x0D  # 12bit,  32 samples, 17.02ms
    ADCRES_12BIT_64S = 0x0E  # 12bit,  64 samples, 34.05ms
    ADCRES_12BIT_128S = 0x0F  # 12bit, 128 samples, 68.10ms


class Mode:
    """Constants for ``mode``"""
    POWERDOW = 0x00  # power down
    SVOLT_TRIGGERED = 0x01  # shunt voltage triggered
    BVOLT_TRIGGERED = 0x02  # bus voltage triggered
    SANDBVOLT_TRIGGERED = 0x03  # shunt and bus voltage triggered
    ADCOFF = 0x04  # ADC off
    SVOLT_CONTINUOUS = 0x05  # shunt voltage continuous
    BVOLT_CONTINUOUS = 0x06  # bus voltage continuous
    SANDBVOLT_CONTINUOUS = 0x07  # shunt and bus voltage continuous


class INA219:
    def __init__(self, i2c_bus=1, addr=0x40):
        self.bus = smbus.SMBus(i2c_bus);
        self.addr = addr

        # Set chip to known config values to start
        self._cal_value = 0
        self._current_lsb = 0
        self._power_lsb = 0
        self.set_calibration_32V_2A()

    def read(self, address):
        data = self.bus.read_i2c_block_data(self.addr, address, 2)
        return ((data[0] * 256) + data[1])

    def write(self, address, data):
        temp = [0, 0]
        temp[1] = data & 0xFF
        temp[0] = (data & 0xFF00) >> 8
        self.bus.write_i2c_block_data(self.addr, address, temp)

    def set_calibration_32V_2A(self):
        """Configures to INA219 to be able to measure up to 32V and 2A of current. Counter
           overflow occurs at 3.2A.
           ..note :: These calculations assume a 0.1 shunt ohm resistor is present
        """
        # By default we use a pretty huge range for the input voltage,
        # which probably isn't the most appropriate choice for system
        # that don't use a lot of power.  But all of the calculations
        # are shown below if you want to change the settings.  You will
        # also need to change any relevant register settings, such as
        # setting the VBUS_MAX to 16V instead of 32V, etc.

        # VBUS_MAX = 32V             (Assumes 32V, can also be set to 16V)
        # VSHUNT_MAX = 0.32          (Assumes Gain 8, 320mV, can also be 0.16, 0.08, 0.04)
        # RSHUNT = 0.1               (Resistor value in ohms)

        # 1. Determine max possible current
        # MaxPossible_I = VSHUNT_MAX / RSHUNT
        # MaxPossible_I = 3.2A

        # 2. Determine max expected current
        # MaxExpected_I = 2.0A

        # 3. Calculate possible range of LSBs (Min = 15-bit, Max = 12-bit)
        # MinimumLSB = MaxExpected_I/32767
        # MinimumLSB = 0.000061              (61uA per bit)
        # MaximumLSB = MaxExpected_I/4096
        # MaximumLSB = 0,000488              (488uA per bit)

        # 4. Choose an LSB between the min and max values
        #    (Preferrably a roundish number close to MinLSB)
        # CurrentLSB = 0.0001 (100uA per bit)
        self._current_lsb = .1  # Current LSB = 100uA per bit

        # 5. Compute the calibration register
        # Cal = trunc (0.04096 / (Current_LSB * RSHUNT))
        # Cal = 4096 (0x1000)

        self._cal_value = 4096

        # 6. Calculate the power LSB
        # PowerLSB = 20 * CurrentLSB
        # PowerLSB = 0.002 (2mW per bit)
        self._power_lsb = .002  # Power LSB = 2mW per bit

        # 7. Compute the maximum current and shunt voltage values before overflow
        #
        # Max_Current = Current_LSB * 32767
        # Max_Current = 3.2767A before overflow
        #
        # If Max_Current > Max_Possible_I then
        #    Max_Current_Before_Overflow = MaxPossible_I
        # Else
        #    Max_Current_Before_Overflow = Max_Current
        # End If
        #
        # Max_ShuntVoltage = Max_Current_Before_Overflow * RSHUNT
        # Max_ShuntVoltage = 0.32V
        #
        # If Max_ShuntVoltage >= VSHUNT_MAX
        #    Max_ShuntVoltage_Before_Overflow = VSHUNT_MAX
        # Else
        #    Max_ShuntVoltage_Before_Overflow = Max_ShuntVoltage
        # End If

        # 8. Compute the Maximum Power
        # MaximumPower = Max_Current_Before_Overflow * VBUS_MAX
        # MaximumPower = 3.2 * 32V
        # MaximumPower = 102.4W

        # Set Calibration register to 'Cal' calculated above
        self.write(_REG_CALIBRATION, self._cal_value)

        # Set Config register to take into account the settings above
        self.bus_voltage_range = BusVoltageRange.RANGE_32V
        self.gain = Gain.DIV_8_320MV
        self.bus_adc_resolution = ADCResolution.ADCRES_12BIT_32S
        self.shunt_adc_resolution = ADCResolution.ADCRES_12BIT_32S
        self.mode = Mode.SANDBVOLT_CONTINUOUS
        self.config = self.bus_voltage_range << 13 | \
                      self.gain << 11 | \
                      self.bus_adc_resolution << 7 | \
                      self.shunt_adc_resolution << 3 | \
                      self.mode
        self.write(_REG_CONFIG, self.config)

    def getShuntVoltage_mV(self):
        self.write(_REG_CALIBRATION, self._cal_value)
        value = self.read(_REG_SHUNTVOLTAGE)
        if value > 32767:
            value -= 65535
        return value * 0.01

    def getBusVoltage_V(self):
        self.write(_REG_CALIBRATION, self._cal_value)
        self.read(_REG_BUSVOLTAGE)
        return (self.read(_REG_BUSVOLTAGE) >> 3) * 0.004

    def getCurrent_mA(self):
        value = self.read(_REG_CURRENT)
        if value > 32767:
            value -= 65535
        return value * self._current_lsb

    def getPower_W(self):
        self.write(_REG_CALIBRATION, self._cal_value)
        value = self.read(_REG_POWER)
        if value > 32767:
            value -= 65535
        return value * self._power_lsb

# 获取CPU温度
def get_cpu_temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read().strip()) / 1000.0
        return f"CPU Temp: {temp:.1f}°C"
    except Exception as e:
        logging.error(f"Failed to get CPU temperature: {e}")
        return "CPU Temp: N/A"


def main():
    device = None
    ina219 = INA219(addr=0x42)  # 初始化INA219

    try:
        counter = 0
        while True:
            # 检测OLED是否连接，如果未连接则尝试重新初始化
            if device is None:
                device = initialize_oled()
                if device is None:
                    logging.warning("OLED not detected. Retrying in 5 seconds...")
                    time.sleep(5)
                    continue

            # 获取系统信息和CPU温度
            IP, CPU, MemUsage, Disk, Date = get_system_info()
            CPU_Temperature = get_cpu_temperature()

            # 获取UPS信息
            bus_voltage = ina219.getBusVoltage_V()
            shunt_voltage = ina219.getShuntVoltage_mV() / 1000
            current = ina219.getCurrent_mA() / 1000
            power = ina219.getPower_W()
            p = (bus_voltage - 6) / 2.4 * 100
            p = max(0, min(100, p))

            load_voltage = f"Load Vol: {bus_voltage:.3f} V"
            current_str = f"Current: {current:.3f} A"
            power_str = f"Power: {power:.3f} W"
            percent_str = f"Percent: {p:.1f}%"

            # 构建显示内容
            text_lines1 = [
                f"IP: {IP}",
                f"CPU: {CPU} {CPU_Temperature}",
                f"Mem: {MemUsage}",
                f"Disk: {Disk}"
            ]
            text_lines2 = [
                load_voltage,
                current_str,
                power_str,
                percent_str
            ]

            # 根据计数器切换显示内容
            if counter % 2 == 0:
                display_text(device, text_lines1)
            else:
                display_text(device, text_lines2)

            time.sleep(4)
            counter += 1

    except KeyboardInterrupt:
        logging.info("Program terminated by user.")
    finally:
        if device:
            device.cleanup()
            logging.info("OLED cleaned up.")

if __name__ == "__main__":
    main()