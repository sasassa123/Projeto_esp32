from pynput import keyboard
import requests


API_URL = "http://10.150.12.201:5000/api/scan"

buffer = ""

def enviar_codigo(codigo):
    codigo = codigo.strip()
    if not codigo:
        return

    print(f"\n📡 Código enviado: {codigo}")

    try:
        r = requests.post(API_URL, json={"code": codigo}, timeout=2)
        data = r.json()

        if data.get("ok"):
            acao = data.get("acao")
            nome = data.get("name")
            if acao == "ENTROU":
                print(f" {nome} ENTROU")
            else:
                print(f" {nome} SAIU")
        else:
            print(" Código não autorizado")

    except Exception as e:
        print(" Erro ao conectar com o backend:", e)


def on_press(key):
    global buffer
    try:
        if hasattr(key, "char") and key.char and key.char.isdigit():
            buffer += key.char

        elif key == keyboard.Key.enter:
            enviar_codigo(buffer)
            buffer = ""

    except:
        pass


listener = keyboard.Listener(on_press=on_press)
listener.start()

print(" Scanner ativo. Passe o crachá em QUALQUER tela.")
print("Pressione ENTER para enviar o código lido.")

listener.join()

