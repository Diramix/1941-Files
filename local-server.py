from flask import Flask, send_from_directory, render_template, request, jsonify, redirect, url_for, session
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'control/config.json')
USERS_PATH = os.path.join(BASE_DIR, 'control/users.json')
WHITELIST_PATH = os.path.join(BASE_DIR, 'control/ip-whitelist.txt')
BANLIST_PATH = os.path.join(BASE_DIR, 'control/ip-banlist.txt')

app = Flask(__name__)
app.secret_key = os.urandom(24)

def load_config():
    with open(CONFIG_PATH, 'r') as config_file:
        return json.load(config_file)

def load_users():
    if os.path.exists(USERS_PATH):
        with open(USERS_PATH, 'r') as f:
            return json.load(f)
    return {}

def load_whitelisted_ips():
    if os.path.exists(WHITELIST_PATH):
        with open(WHITELIST_PATH, 'r') as f:
            return {line.strip() for line in f.readlines()}
    return set()

def load_banned_ips():
    if os.path.exists(BANLIST_PATH):
        with open(BANLIST_PATH, 'r') as f:
            return {line.strip() for line in f.readlines()}
    return set()

config = load_config()
NOSECURE = config.get("nosecure", False)
PORT = config.get("port", 1941)
directory_raw = config.get("directory", "assets")
DIRECTORY = os.path.expandvars(directory_raw)

if not os.path.exists(DIRECTORY):
    os.makedirs(DIRECTORY)
    print(f"Directory '{DIRECTORY}' created.")

def is_banned_ip(user_ip):
    if NOSECURE:
        return False
    banned_ips = load_banned_ips()
    return user_ip in banned_ips

def login_required(f):
    def wrapped(*args, **kwargs):
        if NOSECURE:
            return f(*args, **kwargs)

        user_ip = request.remote_addr
        if is_banned_ip(user_ip):
            return redirect(url_for('banned'))

        whitelisted_ips = load_whitelisted_ips()
        if user_ip in whitelisted_ips:
            return f(*args, **kwargs)

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
    return render_template("files.html", files=files)

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
    if NOSECURE:
        return redirect(url_for('list_files'))

    if 'username' in session:
        return redirect(url_for('list_files'))

    user_ip = request.remote_addr
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
    if NOSECURE:
        return redirect(url_for('list_files'))

    user_ip = request.remote_addr
    users = load_users()
    if is_banned_ip(user_ip):
        return render_template("ban.html")
    if 'username' in session:
        username = session['username']
        user_data = users.get(username)
        if isinstance(user_data, dict) and user_data.get("ban") is True:
            return render_template("ban.html")
    return redirect(url_for('login'))

if __name__ == "__main__":
    print(f"Serving at http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT)
