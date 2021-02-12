from flask import Flask, jsonify, request
import base64

from src.app.logger import pylogger

app = Flask(__name__)


@app.route('/visualizer', methods=["POST"])
def user_code_logger():
    try:
        body = request.json
        py_version = body.get("python_version")
        user_code = base64.b64decode(body.get("user_code"))
        return jsonify(pylogger.run_logger(user_code))
    except AttributeError:
        return jsonify({
            "error": "Please provide a body with all the required fields"
        })
    except Exception as e:
        return jsonify(e.message), 500
