from machine import Pin, I2C, ADC, SDCard
import ssd1306, os, time, math, esp, machine, gc

# ========== UI CONFIG ==========
TITLE_Y = 3
TITLE_X = 16
SD_X = 5
SD_Y = 4
BAT_X = 77
BAT_Y = 4
PERCENT_X = 94
PERCENT_Y = TITLE_Y
radius_title, radius_body = 2, 2
max_items = 4
BATTERY_AVG_INTERVAL = 3000  # ms
INACTIVITY_TIMEOUT = 35000  # 35 sec

# ========== HARDWARE CONFIG ==========
I2C_SCL, I2C_SDA = 22, 21
BTN_UP, BTN_DOWN, BTN_LEFT, BTN_RIGHT = 32, 33, 26, 27
BUZZER_PIN = 25
BAT_ADC_PIN = 35
SD_CS, SD_MOSI, SD_CLK, SD_MISO = 5, 23, 18, 19

# ========== BATTERY CONFIG ==========
R1, R2 = 56000, 22000
DIVIDER_RATIO = R2 / (R1 + R2)
V_REF = 3.3
CALIBRATION = 1.139
V_MIN, V_MAX = 3.0, 4.2

# ========== INIT ==========
i2c = I2C(0, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
btn_up = Pin(BTN_UP, Pin.IN, Pin.PULL_UP)
btn_down = Pin(BTN_DOWN, Pin.IN, Pin.PULL_UP)
btn_left = Pin(BTN_LEFT, Pin.IN, Pin.PULL_UP)
btn_right = Pin(BTN_RIGHT, Pin.IN, Pin.PULL_UP)
buzzer = Pin(BUZZER_PIN, Pin.OUT)
adc = ADC(Pin(BAT_ADC_PIN))
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_12BIT)
sd_mounted = False

boot_time_ms = time.ticks_ms()

# ========== HELPERS ==========
def beep(duration=50):
    buzzer.on()
    time.sleep_ms(duration)
    buzzer.off()

def read_voltage():
    raw = adc.read()
    v_adc = (raw / 4095.0) * V_REF
    return round((v_adc / DIVIDER_RATIO) * CALIBRATION, 2)

def get_battery_percent(v):
    return int(min(100, max(0, (v - V_MIN) / (V_MAX - V_MIN) * 100)))

def safe_mount_sd():
    global sd_mounted
    if sd_mounted: return
    try:
        sd = SDCard(slot=2, sck=Pin(SD_CLK), mosi=Pin(SD_MOSI), miso=Pin(SD_MISO), cs=Pin(SD_CS))
        os.mount(sd, "/sd")
        if "scripts" not in os.listdir("/sd"):
            os.mkdir("/sd/scripts")
        sd_mounted = True
        beep()
    except Exception as e:
        sd_mounted = False
        beep(100); time.sleep(0.1); beep(100)
        show_msg("SD MOUNT ERROR", str(e))

def draw_capsule(oled, x, y, w, h, r):
    oled.hline(x + r, y, w - 2 * r, 1)
    oled.hline(x + r, y + h - 1, w - 2 * r, 1)
    oled.vline(x, y + r, h - 2 * r, 1)
    oled.vline(x + w - 1, y + r, h - 2 * r, 1)
    for angle in range(0, 91, 10):
        rad = math.radians(angle)
        dx = int(r * math.cos(rad))
        dy = int(r * math.sin(rad))
        oled.pixel(x + r - dx, y + r - dy, 1)
        oled.pixel(x + w - 1 - r + dx, y + r - dy, 1)
        oled.pixel(x + r - dx, y + h - 1 - r + dy, 1)
        oled.pixel(x + w - 1 - r + dx, y + h - 1 - r + dy, 1)

def draw_sd_icon(x, y):
    oled.rect(x, y, 6, 6, 1)
    oled.fill_rect(x + 1, y + 1, 4, 2, 1)
    oled.pixel(x + 2, y + 4, 1)
    oled.pixel(x + 3, y + 5, 1)
    oled.pixel(x, y, 0)
    oled.pixel(x + 1, y, 0)
    oled.pixel(x, y + 1, 0)

def draw_battery_bar(x, y, percent):
    oled.rect(x, y, 12, 6, 1)
    oled.fill_rect(x + 12, y + 2, 2, 2, 1)
    fill = int((percent / 100) * 10)
    oled.fill_rect(x + 1, y + 1, fill, 4, 1)

def wrap_text(text, max_chars=16):
    lines = []
    for word in text.split():
        if len(word) <= max_chars:
            if not lines or len(lines[-1]) + len(word) + 1 > max_chars:
                lines.append(word)
            else:
                lines[-1] += ' ' + word
        else:
            while len(word) > max_chars:
                lines.append(word[:max_chars])
                word = word[max_chars:]
            if word:
                lines.append(word)
    return lines

def show_msg(title, msg):
    lines = []
    for line in msg.split("\n"):
        lines.extend(wrap_text(line))

    offset = 0
    while True:
        oled.fill(0)
        draw_capsule(oled, 0, 0, 128, 14, radius_title)
        oled.text(title, 4, TITLE_Y)
        draw_capsule(oled, 0, 17, 128, 46, radius_body)
        for i in range(min(4, len(lines) - offset)):
            oled.text(lines[offset + i][:16], 4, 19 + i * 10)
        oled.show()
        if not btn_up.value() and offset > 0:
            beep(); offset -= 1; time.sleep(0.15)
        elif not btn_down.value() and offset < len(lines) - 4:
            beep(); offset += 1; time.sleep(0.15)
        elif not btn_left.value():
            beep()
            while not btn_left.value(): pass
            break
        time.sleep(0.05)

def get_scripts():
    out = []
    for path in ["/scripts", "/sd/scripts"]:
        try:
            for f in os.listdir(path):
                if f.endswith(".py"):
                    out.append(path + "/" + f)
        except:
            pass
    return sorted(out)

def run_script(path):
    try:
        with open(path) as f:
            exec(f.read(), {
                "__name__": "__main__",
                "oled": oled,
                "adc": adc,
                "beep": beep,
                "btn_up": btn_up,
                "btn_down": btn_down,
                "btn_left": btn_left,
                "btn_right": btn_right,
                "buzzer": buzzer,
                "draw_capsule": draw_capsule,
                "esp": esp,
                "gc": gc,
                "machine": machine,
                "os": os,
                "safe_mount_sd": safe_mount_sd,
                "show_msg": show_msg,
                "time": time,
                "wrap_text": wrap_text
            })
    except Exception as e:
        show_msg("ERROR", str(e))

# ========== MENU ==========
def show_menu():
    scripts = get_scripts()
    if not scripts:
        show_msg("MaxOS", "No .py scripts found.")
        return

    selected, scroll = 0, 0
    last_batt_check = time.ticks_ms()
    batt_samples = []
    batt_percent = 0
    last_activity = time.ticks_ms()

    while True:
        now = time.ticks_ms()
        if time.ticks_diff(now, last_batt_check) >= BATTERY_AVG_INTERVAL:
            if batt_samples:
                batt_percent = sum(batt_samples) // len(batt_samples)
                batt_samples.clear()
            last_batt_check = now
        batt_samples.append(get_battery_percent(read_voltage()))

        if time.ticks_diff(now, last_activity) > INACTIVITY_TIMEOUT:
            # Run lockscreen with uptime info
            uptime_secs = (time.ticks_ms() - boot_time_ms) // 1000
            exec(open("lockscreen.py").read(), {"__name__": "__main__", "uptime_start": uptime_secs})
            last_activity = time.ticks_ms()

        oled.fill(0)
        draw_capsule(oled, 0, 0, 128, 14, radius_title)
        oled.text("[MaxOS]", TITLE_X, TITLE_Y)
        if sd_mounted:
            draw_sd_icon(SD_X, SD_Y)
        draw_battery_bar(BAT_X, BAT_Y, batt_percent)
        oled.text("{}%".format(batt_percent), PERCENT_X, PERCENT_Y)
        draw_capsule(oled, 0, 17, 128, 46, radius_body)

        for i in range(max_items):
            idx = scroll + i
            if idx >= len(scripts): break
            name = scripts[idx].split("/")[-1].replace(".py", "")
            prefix = "> " if idx == selected else "  "
            name = (name[:11] + "...") if len(name) > 14 else name
            line = prefix + name
            oled.text(line, 4, 19 + i * 10)
        oled.show()

        if not btn_down.value():
            beep(); selected += 1
            if selected >= len(scripts): selected = 0; scroll = 0
            elif selected >= scroll + max_items: scroll += 1
            last_activity = time.ticks_ms()
            time.sleep(0.15)

        elif not btn_up.value():
            beep(); selected -= 1
            if selected < 0: selected = len(scripts) - 1; scroll = max(0, len(scripts) - max_items)
            elif selected < scroll: scroll -= 1
            last_activity = time.ticks_ms()
            time.sleep(0.15)

        elif not btn_left.value():
            beep(); selected = 0; scroll = 0
            while not btn_left.value(): pass
            last_activity = time.ticks_ms()

        elif not btn_right.value():
            beep(); run_script(scripts[selected])
            last_activity = time.ticks_ms()
            time.sleep(0.15)

        time.sleep(0.05)

# ========== STARTUP ==========
safe_mount_sd()
while True:
    show_menu()
