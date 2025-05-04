from flask import Flask, send_from_directory, render_template, request, jsonify, redirect, url_for, session
import os
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)

def load_config():
    with open('config.json', 'r') as config_file:
        return json.load(config_file)

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

def load_banned_ips():
    if os.path.exists('ip-banlist.txt'):
        with open('ip-banlist.txt', 'r') as f:
            return {line.strip() for line in f.readlines()}
    return set()

config = load_config()
PORT = config.get("port", 1941)
directory_raw = config.get("directory", "assets")
DIRECTORY = os.path.expandvars(directory_raw)

if not os.path.exists(DIRECTORY):
    os.makedirs(DIRECTORY)
    print(f"Directory '{DIRECTORY}' created.")

# Функция для проверки заблокирован ли IP
def is_banned_ip(user_ip):
    banned_ips = load_banned_ips()
    return user_ip in banned_ips

# Декоратор для проверки авторизации, с добавлением проверки заблокированных IP
def login_required(f):
    def wrapped(*args, **kwargs):
        user_ip = request.remote_addr

        # Если IP заблокирован, перенаправляем на страницу /banned
        if is_banned_ip(user_ip):
            return redirect(url_for('banned'))

        # Если IP в белом списке, пропускаем без авторизации
        whitelisted_ips = load_whitelisted_ips()
        if user_ip in whitelisted_ips:
            return f(*args, **kwargs)

        # Если пользователь не авторизован, перенаправляем на страницу логина
        if 'username' not in session:
            return redirect(url_for('login'))

        users = load_users()
        username = session['username']
        user_data = users.get(username)

        if isinstance(user_data, dict) and user_data.get("ban") is True:
            return redirect(url_for('banned'))

        return f(*args, **kwargs)

    wrapped.__name__ = f.__name__
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
    # Если пользователь уже авторизован, перенаправляем на главную страницу или другую
    if 'username' in session:
        return redirect(url_for('list_files'))  # Можно заменить на любую другую страницу

    user_ip = request.remote_addr

    # Если IP заблокирован, перенаправляем на страницу /banned
    if is_banned_ip(user_ip):
        return redirect(url_for('banned'))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()
        user_data = users.get(username)

        if isinstance(user_data, dict):
            if user_data.get("ban") is True:
                session['username'] = username
                return redirect(url_for('banned'))
            if user_data.get("password") == password:
                session['username'] = username
                return redirect(url_for('list_files'))
        elif user_data == password:
            session['username'] = username
            return redirect(url_for('list_files'))

        return "Invalid credentials, please try again.", 403

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route("/banned")
def banned():
    user_ip = request.remote_addr
    users = load_users()

    # Если IP заблокирован или пользователь заблокирован
    if is_banned_ip(user_ip):
        return render_template("ban.html")
    
    # Также проверяем, если пользователь в бане
    if 'username' in session:
        username = session['username']
        user_data = users.get(username)
        if isinstance(user_data, dict) and user_data.get("ban") is True:
            return render_template("ban.html")

    # Если пользователь не заблокирован, перенаправляем на страницу логина
    return redirect(url_for('login'))

if __name__ == "__main__":
    print(f"Serving at http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT)
