from flask import Flask, render_template, jsonify
import os

app = Flask(__name__)

LOG_PATH = "E:/AI_Projects/Halcyon_Operations/Execution_Logs/runtime.log"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/logs")
def get_logs():
    with open(LOG_PATH, "r") as file:
        logs = file.readlines()
    return jsonify({"logs": logs})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
