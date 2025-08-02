from machine import Pin, I2C, Timer
import network, time, ssd1306, os

# ========== CONFIG ==========
WIFI_SSID = "MAX-AP"
WIFI_PASS = "11223344"
LOG_PATH = "/sd/ML/wifilog.csv"
LEFT_BUTTON = 26
BUZZER_PIN = 25
I2C_SCL = 22
I2C_SDA = 21
OLED_WIDTH = 128
OLED_HEIGHT = 64
COUNTDOWN_SECONDS = 30
RECORD_SECONDS = 600

# ========== INIT ==========
i2c = I2C(scl=Pin(I2C_SCL), sda=Pin(I2C_SDA))
oled = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)
buzzer = Pin(BUZZER_PIN, Pin.OUT)
button = Pin(LEFT_BUTTON, Pin.IN, Pin.PULL_UP)
sta = network.WLAN(network.STA_IF)
sta.active(True)

# ========== FUNCTIONS ==========
def connect_wifi():
    sta.connect(WIFI_SSID, WIFI_PASS)
    timeout = 20
    while not sta.isconnected() and timeout > 0:
        oled.fill(0)
        oled.text("Connecting WiFi", 10, 10)
        oled.text(".", 60 + (20 - timeout) % 3 * 5, 30)
        oled.show()
        time.sleep(1)
        timeout -= 1
    return sta.isconnected()

def beep(ms=100):
    buzzer.on()
    time.sleep_ms(ms)
    buzzer.off()

def countdown(sec):
    for i in range(sec, 0, -1):
        oled.fill(0)
        oled.text("Leave the Room", 10, 10)
        oled.text("Starting in:", 10, 30)
        oled.text(str(i) + " sec", 40, 45)
        oled.show()
        beep(50)
        time.sleep(1)

def log_rssi(duration):
    start = time.ticks_ms()
    with open(LOG_PATH, "w") as f:
        f.write("timestamp_ms,rssi\n")
        while time.ticks_diff(time.ticks_ms(), start) < duration * 1000:
            rssi = sta.status('rssi')
            t = time.ticks_ms()
            f.write(f"{t},{rssi}\n")
            oled.fill(0)
            oled.text("Logging RSSI...", 5, 10)
            oled.text("RSSI: {}".format(rssi), 5, 30)
            oled.text("Time: {}s".format((time.ticks_diff(time.ticks_ms(), start)) // 1000), 5, 50)
            oled.show()
            time.sleep(0.2)

def wait_button_to_stop():
    while button.value():
        oled.fill(0)
        oled.text("Training Done!", 5, 10)
        oled.text("Press LEFT btn", 5, 30)
        oled.show()
        buzzer.on()
        time.sleep(0.3)
        buzzer.off()
        time.sleep(0.3)

# ========== MAIN ==========
oled.fill(0)
oled.text("ESP32 Intrusion", 5, 10)
oled.text("Detector v1", 10, 30)
oled.show()
time.sleep(1)

if connect_wifi():
    oled.fill(0)
    oled.text("WiFi Connected!", 5, 20)
    oled.show()
    time.sleep(1)
    countdown(COUNTDOWN_SECONDS)
    log_rssi(RECORD_SECONDS)
    wait_button_to_stop()
else:
    oled.fill(0)
    oled.text("WiFi Failed!", 10, 20)
    oled.show()
    for _ in range(5):
        beep(100)
        time.sleep(0.2)
