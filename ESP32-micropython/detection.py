import time, network, os

# === CONFIG ===
SSID = "MAX-AP"
THRESHOLD = -32.78
CSV_PATH = "/sd/ML/wifilog.csv"

def scan_rssi():
    found = sta_if.scan()
    for net in found:
        ssid, _, _, rssi, _, _ = net
        if ssid.decode() == SSID:
            return rssi
    return None

def log(rssi, label):
    with open(CSV_PATH, "a") as f:
        t = time.ticks_ms()
        f.write("{},{},{}\n".format(t, rssi, label))

sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)

oled.fill(0)
oled.text("Real-Time Detection", 0, 0)
oled.show()

while True:
    if btn_left.value() == 0:  # Exit on left button
        break

    rssi = scan_rssi()
    if rssi is not None:
        label = "Person" if rssi <= THRESHOLD else "Blank"
        log(rssi, label)
        oled.fill(0)
        oled.text("RSSI: {}".format(rssi), 0, 20)
        oled.text("Status: " + label, 0, 40)
        oled.show()
        if label == "Person":
            beep()
    else:
        oled.fill(0)
        oled.text("SSID not found", 0, 30)
        oled.show()

    time.sleep(2)
