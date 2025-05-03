from flask import Flask, send_from_directory, render_template, request, jsonify, redirect, url_for, session, request
import os
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Ключ для сессий

def load_config():
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
    return config

def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r') as f:
            return json.load(f)
    return {}

def load_whitelisted_ips():
    if os.path.exists('ip-whitelist.txt'):
        with open('ip-whitelist.txt', 'r') as f:
            return {line.strip() for line in f.readlines()}
    return set()

config = load_config()

PORT = config.get("port", 1941)
directory_raw = config.get("directory", "assets")

DIRECTORY = os.path.expandvars(directory_raw)

if not os.path.exists(DIRECTORY):
    os.makedirs(DIRECTORY)
    print(f"Directory '{DIRECTORY}' created.")

# Декоратор для проверки авторизации
def login_required(f):
    def wrapped(*args, **kwargs):
        user_ip = request.remote_addr  # Получаем IP пользователя
        whitelisted_ips = load_whitelisted_ips()

        if user_ip in whitelisted_ips:
            return f(*args, **kwargs)  # Если IP в списке, пропускаем без авторизации

        if 'username' not in session:
            return redirect(url_for('login'))  # Если пользователь не авторизован, редиректим на страницу логина
        return f(*args, **kwargs)

    wrapped.__name__ = f.__name__  # Присваиваем имя оригинальной функции, чтобы избежать конфликтов
    return wrapped

@app.route("/")
@login_required
def list_files():
    files = os.listdir(DIRECTORY)
    files = [f for f in files if os.path.isfile(os.path.join(DIRECTORY, f))]
    return render_template("index.html", files=files)

@app.route("/<filename>")
@login_required
def serve_file(filename):
    return send_from_directory(DIRECTORY, filename)

@app.route("/upload", methods=["POST"])
@login_required
def upload_file():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "File not found"})

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No file to download"})

    filepath = os.path.join(DIRECTORY, file.filename)

    if os.path.exists(filepath):
        return jsonify({"success": False, "message": "A file with this name already exists"})

    file.save(filepath)
    return jsonify({"success": True})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()
        
        if username in users and users[username] == password:
            session['username'] = username  # Сохраняем имя пользователя в сессии
            return redirect(url_for('list_files'))
        else:
            return "Invalid credentials, please try again.", 403  # Неверные данные для входа

    return render_template("login.html")  # Страница логина

@app.route("/logout")
def logout():
    session.pop('username', None)  # Удаляем пользователя из сессии
    return redirect(url_for('login'))  # Перенаправляем на страницу логина

if __name__ == "__main__":
    print(f"Serving at http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT)
