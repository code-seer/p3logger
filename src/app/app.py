from flask import Flask, jsonify

from src.app.logger import logger

app = Flask(__name__)

@app.route('/')
def user_code_logger():
    user_code = """input = 'Sideshow,Bob,1972,4,1,male'

tokens = input.split(',')
randomVals = [1, 2, 3, 4, 5]
firstName = tokens[0]
lastName = tokens[1]
birthdate = (int(tokens[2]), int(tokens[3]), int(tokens[4]))
isMale = (tokens[5] == 'male')
fullName = firstName + ' ' + lastName
randomNums = {'a': 1, 'b': 2}

print('Hi ' + fullName)
    """
    return jsonify(logger.run_logger(user_code))

#     return 'Hello, World!'
#
# user_code_logger()