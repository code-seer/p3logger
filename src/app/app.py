from flask import Flask, jsonify, request
from flask_cors import CORS
import base64

from logger import pylogger

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:5000",
    "http://localhost:3000",
    "http://learnet.io",
    "https://learnet.io",
]}})


@app.route('/api/visualizer', methods=["POST"])
def user_code_logger():
    try:
        body = request.json
        language = body.get("language")
        user_code = base64.b64decode(body.get("user_code"))
        return jsonify(pylogger.run_logger(user_code))
    except AttributeError:
        return jsonify({
            "error": "Please provide a body with all the required fields"
        })
    except Exception as e:
        return jsonify(e.message), 500


@app.route('/api/feedback', methods=["POST"])
def user_feedback():
    try:
        body = request.json
        name = body.get("name")
        email = body.get("email")
        feedback = body.get('feedback')
        print "user feedback: ", name, email, feedback
        return jsonify({"status": "OK"}), 200
    except AttributeError:
        return jsonify({
            "error": "Unable to accept feedback. Sorry!"
        })
    except Exception as e:
        return jsonify(e.message), 500



if __name__ == "__main__":
    app.run(host='0.0.0.0')
