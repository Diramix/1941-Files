from flask import Flask, send_from_directory, render_template, request, jsonify
import os
import json

app = Flask(__name__)

# Загрузка конфигурации из файла config.json
def load_config():
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
    return config

# Загрузка конфигурации
config = load_config()

PORT = config.get("port", 1941)  # Порт из config.json, если не указан — по умолчанию 1941
DIRECTORY = config.get("directory", "assets")  # Директория из config.json, если не указана — по умолчанию "assets"

# Проверка и создание директории, если она не существует
if not os.path.exists(DIRECTORY):
    os.makedirs(DIRECTORY)
    print(f"Directory '{DIRECTORY}' created.")

@app.route("/")
def list_files():
    files = os.listdir(DIRECTORY)
    files = [f for f in files if os.path.isfile(os.path.join(DIRECTORY, f))]
    return render_template("index.html", files=files)

@app.route("/<filename>")
def serve_file(filename):
    return send_from_directory(DIRECTORY, filename)

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "File not found"})
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No file to download"})
    
    # Путь к директории для сохранения файла
    filepath = os.path.join(DIRECTORY, file.filename)

    # Проверка на существование файла с таким же именем
    if os.path.exists(filepath):
        return jsonify({"success": False, "message": "A file with this name already exists"})
    
    file.save(filepath)
    return jsonify({"success": True})

if __name__ == "__main__":
    print(f"Serving at http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT)
