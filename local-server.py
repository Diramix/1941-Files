from flask import Flask, send_from_directory
import os

app = Flask(__name__)

PORT = 1941
DIRECTORY = "assets"

@app.route("/<filename>")
def serve_file(filename):
    # Путь к файлу в директории assets
    return send_from_directory(DIRECTORY, filename)

if __name__ == "__main__":
    # Не меняем текущую директорию
    print(f"Serving at http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT)
