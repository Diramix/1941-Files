import json
import os
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from platformdirs import user_data_dir

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "control" / "config.json"
USERS_PATH = BASE_DIR / "control" / "users.json"
WHITELIST_PATH = BASE_DIR / "control" / "ip-whitelist.txt"
BANLIST_PATH = BASE_DIR / "control" / "ip-banlist.txt"
FILES_FOLDER_NAME = "1941 Files"

app = Flask(__name__)
app.secret_key = os.urandom(24)


def load_json(path: Path) -> dict:
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_lines(path: Path) -> set:
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    return set()


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def resolve_directory(raw: str) -> Path:
    if raw.strip() == "{home}":
        return Path(user_data_dir(FILES_FOLDER_NAME, appauthor=False))
    return Path(os.path.expandvars(raw)).resolve()


config = load_config()
NOSECURE: bool = config.get("nosecure", False)
PORT: int = config.get("port", 1941)
DIRECTORY = resolve_directory(config.get("directory", "{home}"))
DIRECTORY.mkdir(parents=True, exist_ok=True)


def is_banned_ip(user_ip: str) -> bool:
    return not NOSECURE and user_ip in load_lines(BANLIST_PATH)


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if NOSECURE:
            return f(*args, **kwargs)

        user_ip = request.remote_addr

        if is_banned_ip(user_ip):
            return redirect(url_for("banned"))

        if user_ip in load_lines(WHITELIST_PATH):
            return f(*args, **kwargs)

        if "username" not in session:
            return redirect(url_for("login"))

        user_data = load_json(USERS_PATH).get(session["username"])
        if isinstance(user_data, dict) and user_data.get("ban") is True:
            return redirect(url_for("banned"))

        return f(*args, **kwargs)

    return wrapped


@app.route("/")
@login_required
def list_files():
    files = [f.name for f in DIRECTORY.iterdir() if f.is_file()]
    return render_template("files.html", files=files)


@app.route("/<filename>")
@login_required
def serve_file(filename):
    return send_from_directory(str(DIRECTORY), filename)


@app.route("/upload", methods=["POST"])
@login_required
def upload_file():
    file = request.files.get("file")
    if not file:
        return jsonify({"success": False, "message": "File not found"})
    if not file.filename:
        return jsonify({"success": False, "message": "No file to upload"})

    filepath = DIRECTORY / file.filename
    if filepath.exists():
        return jsonify(
            {"success": False, "message": "A file with this name already exists"}
        )

    file.save(str(filepath))
    return jsonify({"success": True})


@app.route("/login", methods=["GET", "POST"])
def login():
    if NOSECURE or "username" in session:
        return redirect(url_for("list_files"))

    user_ip = request.remote_addr
    if is_banned_ip(user_ip):
        return redirect(url_for("banned"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_json(USERS_PATH)
        user_data = users.get(username)

        if isinstance(user_data, dict):
            if user_data.get("ban") is True:
                session["username"] = username
                return redirect(url_for("banned"))
            if user_data.get("password") == password:
                session["username"] = username
                return redirect(url_for("list_files"))
        elif user_data == password:
            session["username"] = username
            return redirect(url_for("list_files"))

        return "Invalid credentials, please try again.", 403

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


@app.route("/banned")
def banned():
    if NOSECURE:
        return redirect(url_for("list_files"))

    user_ip = request.remote_addr
    if is_banned_ip(user_ip):
        return render_template("ban.html")

    if "username" in session:
        user_data = load_json(USERS_PATH).get(session["username"])
        if isinstance(user_data, dict) and user_data.get("ban") is True:
            return render_template("ban.html")

    return redirect(url_for("login"))


if __name__ == "__main__":
    print(f"Serving files from: {DIRECTORY}")
    print(f"Serving at http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT)
