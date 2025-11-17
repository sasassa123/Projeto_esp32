import time, ujson
from machine import Pin, I2C
import network
from umqtt.robust import MQTTClient
from i2c_lcd import I2cLcd
import urequests


WIFI_SSID = "Visitantes"
WIFI_PASS = ""


MQTT_HOST = "c3f995e2e3fc4989bbdad3830780078e.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "Esp32"
MQTT_PASS = "Esp32pass"
CLIENT_ID = "esp32_display_1"
TOPIC = b"access/scan"


BACKEND_URL = "http://10.150.12.:5000/api/scan"  


i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
lcd = I2cLcd(i2c, 0x27, 2, 16)

def lcd_msg(l1="", l2=""):
    lcd.clear()
    lcd.move_to(0,0); lcd.putstr((l1 or "")[:16])
    lcd.move_to(0,1); lcd.putstr((l2 or "")[:16])


LED_GREEN = Pin(13, Pin.OUT)
LED_RED   = Pin(12, Pin.OUT)
BUZZER    = Pin(4, Pin.OUT)

def clear_outputs():
    LED_GREEN.off()
    LED_RED.off()
    BUZZER.off()

def signal_ok(name, entered: bool):
    LED_RED.off()
    LED_GREEN.on()
    BUZZER.on(); time.sleep_ms(120); BUZZER.off()
    lcd_msg(name, "Entrou" if entered else "Saiu")
    time.sleep(1.4)
    clear_outputs()
    lcd_msg("Aguardando...", "")

def signal_fail(code):
    LED_GREEN.off()
    LED_RED.on()
    for _ in range(2):
        BUZZER.on(); time.sleep_ms(80); BUZZER.off(); time.sleep_ms(80)
    lcd_msg("Nao Autorizado", (code or "")[-16:])
    time.sleep(1.4)
    clear_outputs()
    lcd_msg("Aguardando...", "")


wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(WIFI_SSID, WIFI_PASS)
lcd_msg("Conectando WiFi", "")
while not wifi.isconnected():
    time.sleep(0.2)
lcd_msg("WiFi OK", wifi.ifconfig()[0])
time.sleep(1)


def mqtt_callback(topic, msg):
    print(" RECEBIDO:", msg)
    try:
        data = ujson.loads(msg)

        if not data.get("ok"):
            signal_fail(data.get("code", ""))
            return

        nome = data.get("name", "")
        acao = data.get("acao", "")

        if acao == "ENTROU":
            signal_ok(nome, True)
        elif acao == "SAIU":
            signal_ok(nome, False)
        else:
            lcd_msg("Erro", "Acao invalida")

    except Exception as e:
        print("Erro MQTT:", e)


client = MQTTClient(CLIENT_ID, MQTT_HOST, port=MQTT_PORT,
                    user=MQTT_USER, password=MQTT_PASS,
                    ssl=True, ssl_params={"server_hostname": MQTT_HOST})

client.set_callback(mqtt_callback)
client.connect()
client.subscribe(TOPIC)
lcd_msg("MQTT OK", "")
time.sleep(1)
lcd_msg("Aguardando...", "")


rows = [Pin(p, Pin.IN, Pin.PULL_UP) for p in (25, 26, 27, 33)]
cols = [Pin(p, Pin.OUT) for p in (32, 14, 15)]

keys = [
    ["1","2","3"],
    ["4","5","6"],
    ["7","8","9"],
    ["*","0","#"]
]

typed = ""

def read_key():
    for c_idx, c in enumerate(cols):
        c.off()
        time.sleep_us(200)
        for r_idx, r in enumerate(rows):
            if r.value() == 0:
                c.on()
                return keys[r_idx][c_idx]
        c.on()
    return None


while True:
    client.check_msg()

    k = read_key()
    if k:
        if k.isdigit():
            typed += k
            lcd_msg("Código:", typed[-16:])
            BUZZER.on(); time.sleep_ms(25); BUZZER.off()

        elif k == "*":
            if typed:
                lcd_msg("Verificando...", "")
                try:
                    urequests.post(BACKEND_URL, json={"code": typed})
                except:
                    lcd_msg("Falha no envio", "")
                    time.sleep(1)
                typed = ""
                lcd_msg("Aguardando...", "")

        elif k == "#":
            typed = ""
            lcd_msg("Limpo", "")
            time.sleep(0.4)
            lcd_msg("Aguardando...", "")

    time.sleep_ms(90)

