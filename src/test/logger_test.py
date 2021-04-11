import json
import yaml
from src.app.logger import pylogger

tokenizer_code = """input = 'John,Doe,1984,4,1,male'

tokens = input.split(',')
firstName = tokens[0]
lastName = tokens[1]
birthdate = (int(tokens[2]), int(tokens[3]), int(tokens[4]))
isMale = (tokens[5] == 'male')

print('Hi ' + firstName + ' ' + lastName)
"""

oop_code = """class A:
    x = 1
    y = 'hello'

class B:
    z = 'bye'

class C(A,B):
    def salutation(self):
        return '%d %s %s' % (self.x, self.y, self.z)

inst = C()
print(inst.salutation())
inst.x = 100
print(inst.salutation())"""

oop_code2 = """class C:
    var1 = 'a'
    var2 = 'b'

# class A:
#     def __init__(self, param):
#         this.x = 1
#         this.y = 'hello' 
#     class B:
#         var1 = 1
#         var2 = 2
"""


def assert_response(expected_file_name, user_code):
    data = None
    with open(expected_file_name + ".json", 'r') as f:
        data = json.dumps(json.load(f))
    trace_data = pylogger.run_logger(user_code)
    with open(expected_file_name+"_test.json", "w") as f:
        json.dump(trace_data, f)
    assert data
    assert yaml.safe_load(data) == trace_data  # yaml strips away the unicode


# def test_oop():
#     assert_response('oop_trace.json', oop_code)


def test_baseline():
    assert_response('tokenizer_trace', tokenizer_code)


# def test_baseline_2():
#     assert_response('tokenizer_trace.json', tokenizer_code)




test_baseline()