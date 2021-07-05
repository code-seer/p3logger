import os

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_mail import Mail, Message
import base64
import datetime

from logger import pylogger

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": [
    "http://localhost",
    "http://localhost:3000",
    "http://codeseer.net",
    "https://codeseer.net",
]}})

mail_settings = {
    "MAIL_SERVER": 'smtp.gmail.com',
    "MAIL_PORT": 465,
    "MAIL_USE_TLS": False,
    "MAIL_USE_SSL": True,
    "MAIL_USERNAME": os.environ.get('EMAIL_USER'),
    "MAIL_PASSWORD": os.environ.get('EMAIL_PASSWORD')
}

app.config.update(mail_settings)
mail = Mail(app)


def send_email(name=None, email=None, feedback=None):
    with app.app_context():
        msg = Message(subject="CodeSeer Feedback from " + name,
                      sender=("Codeseer.net", email),
                      reply_to=(name, email),
                      recipients=[os.environ['EMAIL_USER']],
                      body=feedback)
        mail.send(msg)
        print "Feedback Submitted by " + email


@app.route('/visualizer', methods=["POST"])
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


@app.route('/feedback', methods=["POST"])
def user_feedback():
    try:
        body = request.json
        name = body.get("name")
        email = body.get("email")
        feedback = body.get('feedback')
        send_email(name=name, email=email, feedback=feedback)
        return jsonify({"status": "OK"}), 200
    except AttributeError:
        return jsonify({
            "error": "Unable to accept feedback. Sorry!"
        })
    except Exception as e:
        return jsonify(e.message), 500


@app.route('/status', methods=["GET"])
def status():
    now = datetime.datetime.now()
    response = {
        "status": "UP",
        "time": now.strftime('%Y-%m-%dT%H:%M:%S') + ('.%03d' % (now.microsecond / 10000))
    }
    return jsonify(response), 200


if __name__ == "__main__":
    app.run(host='0.0.0.0')
