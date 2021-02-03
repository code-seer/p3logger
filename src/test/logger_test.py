import json

from src.app.logger import logger

user_code = """input = 'Sideshow,Bob,1972,4,1,male'
tokens = input.split(',')
firstName = tokens[0]
lastName = tokens[1]
birthdate = (int(tokens[2]), int(tokens[3]), int(tokens[4]))
isMale = (tokens[5] == 'male')
fullName = firstName + ' ' + lastName

print('Hi ' + fullName)
"""


def test_baseline():
    data = None
    with open('test/tokenizer_trace.json', 'r') as f:
        data = json.load(f)
    trace_data = logger.run_logger(user_code)
    assert data
    assert data == trace_data

