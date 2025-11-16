
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import mysql.connector
import json
import paho.mqtt.client as mqtt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from flask import send_file


ADMIN_USER = "admin"
ADMIN_PASS = "1234"


DB_CFG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "controle"
}


HIVEMQ_HOST = "c3f995e2e3fc4989bbdad3830780078e.s1.eu.hivemq.cloud"
HIVEMQ_PORT = 8883
HIVEMQ_USER = "Esp32"
HIVEMQ_PASS = "Esp32pass"

MQTT_TOPIC_SCAN = "access/scan"

mqtt_client = mqtt.Client(client_id="backend_server")
mqtt_client.username_pw_set(HIVEMQ_USER, HIVEMQ_PASS)
mqtt_client.tls_set()
mqtt_client.tls_insecure_set(True)
mqtt_client.connect(HIVEMQ_HOST, HIVEMQ_PORT)
mqtt_client.loop_start()


app = Flask(__name__)
app.secret_key = "chave-muito-secreta"

def db_connect():
    return mysql.connector.connect(**DB_CFG)


@app.route("/api/scan", methods=["POST"])
def api_scan():
    data = request.get_json() or request.form
    code = data.get("code")

    if not code:
        return jsonify({"error": "code required"}), 400

    conn = db_connect()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE code=%s", (code,))
    row = cur.fetchone()

    if not row:
        payload = json.dumps({"code": code, "name": "", "ok": False, "acao": ""})
        mqtt_client.publish(MQTT_TOPIC_SCAN, payload.encode(), qos=1)
        cur.close()
        conn.close()
        return jsonify({"published": True, "payload": payload})

    name = row["name"]
    current_status = row["status"]

    if current_status == 0:
        new_status = 1
        acao = "ENTROU"
    else:
        new_status = 0
        acao = "SAIU"

    cur.execute("UPDATE users SET status=%s WHERE code=%s", (new_status, code))
    cur.execute("INSERT INTO log_acessos (code, name, acao) VALUES (%s, %s, %s)", (code, name, acao))
    conn.commit()

    cur.close()
    conn.close()

    payload = json.dumps({"code": code, "name": name, "ok": True, "acao": acao})
    mqtt_client.publish(MQTT_TOPIC_SCAN, payload.encode(), qos=1)

    return jsonify({"published": True, "payload": payload})


@app.route("/api/add", methods=["POST"])
def api_add():
    data = request.get_json() or request.form
    code = data.get("code")
    name = data.get("name")

    if not code or not name:
        return jsonify({"error": "code and name required"}), 400

    conn = db_connect()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (code, name) VALUES (%s, %s)", (code, name))
        conn.commit()
    except mysql.connector.IntegrityError:
        cur.close()
        conn.close()
        return jsonify({"error": "code exists"}), 400

    cur.close()
    conn.close()
    return jsonify({"added": True})



@app.route("/")
def home():
    return redirect("/login")



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")

        
        if u == ADMIN_USER and p == ADMIN_PASS:
            session["admin"] = True
            return redirect("/admin")

        
        conn = db_connect()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE name=%s AND code=%s", (u, p))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session["voluntario"] = user["name"]
            return redirect("/voluntario")

        return render_template("login.html", error="Credenciais inválidas")

    return render_template("login.html")




@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")

    conn = db_connect()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT code, name, funcao, status FROM users ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("painel_admin.html", usuarios=rows)
@app.route("/voluntario")
def pagina_voluntario():
    if not session.get("voluntario"):
        return redirect("/login")

    conn = db_connect()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT name FROM users ORDER BY name")
    lista = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("voluntario.html", nomes=lista)






@app.route("/admin/novo", methods=["GET", "POST"])
def novo_usuario():
    if not session.get("admin"):
        return redirect("/login")

    if request.method == "POST":
        code = request.form.get("code")
        name = request.form.get("name")
        funcao = request.form.get("funcao")
        numero = request.form.get("numero")
        endereco = request.form.get("endereco")

        conn = db_connect()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT * FROM users WHERE code=%s", (code,))
        existente = cur.fetchone()

        if existente:
            cur.close()
            conn.close()
            return render_template("novo_usuario.html", error="⚠ Este código já está cadastrado!")

        cur2 = conn.cursor()
        cur2.execute("""
            INSERT INTO users (code, name, funcao, numero, endereco, status)
            VALUES (%s, %s, %s, %s, %s, 0)
        """, (code, name, funcao, numero, endereco))
        conn.commit()
        cur2.close()
        conn.close()
        return redirect("/admin")

    return render_template("novo_usuario.html")



@app.route("/admin/ver/<code>")
def ver_voluntario(code):
    if not session.get("admin"):
        return redirect("/login")

    conn = db_connect()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT code, name, funcao, endereco, numero, created_at, status 
        FROM users 
        WHERE code=%s
    """, (code,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    return render_template("detalhes_voluntario.html", user=user)



@app.route("/admin/editar/<code>", methods=["GET", "POST"])
def editar_usuario(code):
    if not session.get("admin"):
        return redirect("/login")

    conn = db_connect()
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        new_name = request.form.get("name")
        new_funcao = request.form.get("funcao")
        new_numero = request.form.get("numero")
        new_endereco = request.form.get("endereco")

        cur.execute("""
            UPDATE users SET name=%s, funcao=%s, numero=%s, endereco=%s
            WHERE code=%s
        """, (new_name, new_funcao, new_numero, new_endereco, code))
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/admin")

    cur.execute("SELECT * FROM users WHERE code=%s", (code,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return render_template("editar_usuario.html", user=user)



@app.route("/admin/remover/<code>")
def remover_usuario(code):
    if not session.get("admin"):
        return redirect("/login")

    conn = db_connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE code=%s", (code,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/admin")




@app.route("/relatorio")
def relatorio():
    if not session.get("admin"):
        return redirect("/login")

    dia = request.args.get("dia")

    conn = db_connect()
    cur = conn.cursor(dictionary=True)

    if dia:
        cur.execute("SELECT * FROM log_acessos WHERE DATE(horario)=%s ORDER BY horario DESC", (dia,))
    else:
        cur.execute("SELECT * FROM log_acessos ORDER BY horario DESC")

    logs = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("relatorio.html", registros=logs, dia=dia)




@app.route("/relatorio/pdf")
def relatorio_pdf():
    if not session.get("admin"):
        return redirect("/login")

    dia = request.args.get("dia")

    conn = db_connect()
    cur = conn.cursor(dictionary=True)

    if dia and dia.strip() != "":
        cur.execute("SELECT * FROM log_acessos WHERE DATE(horario)=%s ORDER BY horario DESC", (dia,))
        titulo_relatorio = f"Relatório de {dia}"
    else:
        cur.execute("SELECT * FROM log_acessos ORDER BY horario DESC")
        titulo_relatorio = "Relatório Completo"

    logs = cur.fetchall()
    cur.close()
    conn.close()

    file_path = "relatorio_acessos.pdf"
    c = canvas.Canvas(file_path, pagesize=A4)

   
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, titulo_relatorio)

    c.setFont("Helvetica", 10)
    c.drawString(50, 785, f"Total de registros: {len(logs)}")

    data = [["Nome", "Código", "Ação", "Horário"]]
    for l in logs:
        data.append([l["name"], l["code"], l["acao"], str(l["horario"])])

    table = Table(data, colWidths=[150, 100, 100, 150])

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ]))

    
    table.wrapOn(c, 50, 760)
    table.drawOn(c, 50, 700 - (len(logs) * 18))

    c.showPage()
    c.save()

    return send_file(file_path, as_attachment=True)



@app.route("/download/relatorio.pdf")
def download_relatorio_pdf():
    return send_file("relatorio_acessos.pdf", as_attachment=True)



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    print("✅ Backend rodando em http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
