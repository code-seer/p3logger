# LearNet Software

import sys
import bdb
import traceback

from .encoder import Encoder

PYTHON_VERSION = sys.version_info[0]

if PYTHON_VERSION < 3:
    import cStringIO as io
else:
    import io

from . import encoder

MAX_EXECUTED_LINES = 1000
IGNORE_VARS = set(('__stdout__', '__builtins__', '__name__', '__exception__'))


def set_max_executed_lines(m):
    global MAX_EXECUTED_LINES
    MAX_EXECUTED_LINES = m


def get_user_stdout(frame):
    return frame.f_globals.get('__stdout__').getvalue()


def get_user_globals(frame):
    d = filter_var_dict(frame.f_globals)
    # also filter out __return__ for globals only, but NOT for locals
    if '__return__' in d:
        del d['__return__']
    return d


def get_user_locals(frame):
    return filter_var_dict(frame.f_locals)


def filter_var_dict(d):
    ret = {}
    for (k, v) in d.items():
        if k not in IGNORE_VARS:
            ret[k] = v
    return ret


def encode_heap(encoded_globals):
    """Encode global variables as heap objects by adding the REF key to
    compound objects and keeping primitives the same"""
    heap = {}
    modified_globals = {}
    for k, v in encoded_globals.items():
        if type(v) == list:
            heap_val = None
            heap_key = None
            if v[0] == 'CLASS' or v[0] == 'INSTANCE':
                heap_key = str(v[2])
                heap_val = [v[0], v[1]]
                heap_val.extend(v[3:])
                modified_globals[k] = ["REF", int(heap_key)]
            else:
                heap_key = str(v[1])
                heap_val = [v[0]]
                heap_val.extend(v[2:])
            modified_globals[k] = ["REF", int(heap_key)]
            heap[heap_key] = heap_val
        else:
            modified_globals[k] = v
    # print heap
    # print modified_globals
    return modified_globals, heap


def frame_debugger(frame, event_type):
    if frame:
        print "----------------------------------Frame-------------------------------------------------"
        print "Line Number: ", frame.f_lineno
        print "name: ", frame.f_code.co_name
        print "Event Type: ", event_type
        print "Caller: ", frame.f_back.f_lineno, frame.f_back.f_code.co_name
        # print "co_name: ", frame.f_code.co_name
        # print "co_argcount: ", frame.f_code.co_argcount
        # print "co_cellvars: ", frame.f_code.co_cellvars
        # print "co_consts: ", frame.f_code.co_consts
        # print "co_names: ", frame.f_code.co_names
        # print "co_nlocals: ", frame.f_code.co_nlocals
        # print "co_stacksize: ", frame.f_code.co_stacksize
        # print "co_varnames: ", frame.f_code.co_varnames
        global_vars = get_user_globals(frame)
        print "Global:"
        print global_vars
        for k,v in global_vars.items():
            ret = []
            if str(type(v)) == "<type \'instance\'>":
                ret.append('INSTANCE')
                ret.append(v.__class__.__name__)
            elif str(type(v)) == "<type \'classobj\'>":
                ret.append('CLASS')
                ret.append(v.__name__)
                superclass_names = [base.__name__ for base in v.__bases__]
                ret.append(superclass_names)
            print "Summary: ", ret

        # print "\ncaller:"
        # print frame.f_back.items()
        print "\nLocal:"
        print get_user_locals(frame)
        # print frame.f_trace.__name__
        print "\n"
        # print "Local __name__:"
        # print frame.f_locals.get("__name__")
        # print("\n")
        # print "__builtins__ keys:"
        # print frame.f_globals.get("__builtins__").keys()

class PyLogger(bdb.Bdb):

    def __init__(self, finalizer_func, ignore_id=False):
        bdb.Bdb.__init__(self)
        self.mainpyfile = ''
        self._wait_for_mainpyfile = 0

        # a function that takes the output trace as a parameter and
        # processes it
        self.finalizer_func = finalizer_func

        # each entry contains a dict with the information for a single
        # executed line
        self.trace = []

        # don't print out a custom ID for each object
        # (for regression testing)
        self.ignore_id = ignore_id

        self.lineno = None
        self.stack = []
        self.curindex = 0
        self.curframe = None
        self.encoder = Encoder()

    def reset(self):
        bdb.Bdb.reset(self)
        self.forget()

    def forget(self):
        self.lineno = None
        self.stack = []
        self.curindex = 0
        self.curframe = None

    def setup(self, f, t):
        self.forget()
        self.stack, self.curindex = self.get_stack(f, t)
        self.curframe = self.stack[self.curindex][0]

    # Override Bdb methods

    def user_call(self, frame, argument_list):
        """This method is called when there is the remote possibility
        that we ever need to stop in this function."""
        if self._wait_for_mainpyfile:
            return
        if self.stop_here(frame):
            self.process_stack_frame(frame, None, 'call')

    def user_line(self, frame):
        """This function is called when we stop or break at this line."""
        if self._wait_for_mainpyfile:
            if (self.canonic(frame.f_code.co_filename) != "<string>" or
                    frame.f_lineno <= 0):
                return
            self._wait_for_mainpyfile = 0
        self.process_stack_frame(frame, None, 'step_line')

    def user_return(self, frame, return_value):
        """This function is called when a return trap is set here."""
        frame.f_locals['__return__'] = return_value
        self.process_stack_frame(frame, None, 'return')

    def user_exception(self, frame, exc_info):
        exc_type, exc_value, exc_traceback = exc_info
        """This function is called if an exception occurs,
        but only if we are to stop at or just below this level."""
        frame.f_locals['__exception__'] = exc_type, exc_value
        if type(exc_type) == type(''):
            exc_type_name = exc_type
        else:
            exc_type_name = exc_type.__name__
        self.process_stack_frame(frame, exc_traceback, 'exception')

    # General interaction function

    def process_stack_frame(self, frame, traceback, event_type):
        self.setup(frame, traceback)
        tos = self.stack[self.curindex]
        lineno = tos[1]

        # each element is a pair of (function name, ENCODED locals dict)
        encoded_stack_locals = []

        # climb up until you find '<module>', which is (hopefully) the global scope
        i = self.curindex
        while True:
            cur_frame = self.stack[i][0]
            cur_name = cur_frame.f_code.co_name
            if cur_name == '<module>':
                break

            # special case for lambdas - grab their line numbers too
            if cur_name == '<lambda>':
                cur_name = 'lambda on line ' + str(cur_frame.f_code.co_firstlineno)
            elif cur_name == '':
                cur_name = 'unnamed function'

            # encode in a JSON-friendly format now, in order to prevent ill
            # effects of aliasing later down the line ...
            encoded_locals = {}
            
            for (k, v) in get_user_locals(cur_frame).items():
                # don't display some built-in locals ...
                if k != '__module__':
                    encoded_locals[k] = self.encoder.encode(v, self.ignore_id)

            encoded_stack_locals.append((cur_name, encoded_locals))
            i -= 1

        # encode in a JSON-friendly format now, in order to prevent ill
        # effects of aliasing later down the line ...
        encoded_globals = {}
        for (k, v) in get_user_globals(tos[0]).items():
            encoded_globals[k] = self.encoder.encode(v, self.ignore_id)
        encoded_globals, heap = encode_heap(encoded_globals)
        # frame_debugger(tos[0], event_type)
        trace_entry = dict(line=lineno,
                           event=event_type,
                           func_name=tos[0].f_code.co_name,
                           globals=encoded_globals,
                           ordered_globals=sorted(encoded_globals.keys()),
                           heap=heap,
                           stack_locals=encoded_stack_locals,
                           stdout=get_user_stdout(tos[0]))

        # print trace_entry
        # if there's an exception, then record its info:
        if event_type == 'exception':
            # always check in f_locals
            exc = frame.f_locals['__exception__']
            trace_entry['exception_msg'] = exc[0].__name__ + ': ' + str(exc[1])

        self.trace.append(trace_entry)

        if len(self.trace) >= MAX_EXECUTED_LINES:
            self.trace.append(dict(event='instruction_limit_reached', exception_msg='(stopped after ' + str(
                MAX_EXECUTED_LINES) + ' steps to prevent possible infinite loop)'))
            self.force_terminate()

        self.forget()

    def run_script(self, script_str):
        # When bdb sets tracing, a number of call and line events happens
        # BEFORE debugger even reaches user's code (and the exact sequence of
        # events depends on python version). So we take special measures to
        # avoid stopping before we reach the main script (see user_line and
        # user_call for details).
        self._wait_for_mainpyfile = 1

        # ok, let's try to sorta 'sandbox' the user script by not
        # allowing certain potentially dangerous operations:
        user_builtins = {}
        for (k, v) in __builtins__.items():
            if k in ('reload', 'input', 'apply', 'open', 'compile',
                     '__import__', 'file', 'eval', 'execfile',
                     'exit', 'quit', 'raw_input',
                     'dir', 'globals', 'locals', 'vars',
                     'compile'):
                continue
            user_builtins[k] = v

        # redirect stdout of the user program to a memory buffer
        user_stdout = io.StringIO()
        sys.stdout = user_stdout
        user_globals = {"__name__": "__main__",
                        "__builtins__": user_builtins,
                        "__stdout__": user_stdout}

        try:
            self.run(script_str, user_globals, user_globals)
        except SystemExit:
            return
        except:
            traceback.print_exc()  # uncomment this to see the REAL exception msg

            trace_entry = dict(event='uncaught_exception')

            exc = sys.exc_info()[1]
            if hasattr(exc, 'lineno'):
                trace_entry['line'] = exc.lineno
            if hasattr(exc, 'offset'):
                trace_entry['offset'] = exc.offset

            if hasattr(exc, 'msg'):
                trace_entry['exception_msg'] = "Error: " + exc.msg
            else:
                trace_entry['exception_msg'] = "Unknown error"

            self.trace.append(trace_entry)
            self.finalize()
            return

    def force_terminate(self):
        self.finalize()

    def finalize(self):
        sys.stdout = sys.__stdout__
        assert len(self.trace) <= (MAX_EXECUTED_LINES + 1)

        # filter all entries after 'return' from '<module>', since they
        # seem extraneous:
        res = []
        for e in self.trace:
            res.append(e)
            if e['event'] == 'return' and e['func_name'] == '<module>':
                break

        # another hack: if the SECOND to last entry is an 'exception'
        # and the last entry is return from <module>, then axe the last
        # entry, for aesthetic reasons :)
        if len(res) >= 2 and \
                res[-2]['event'] == 'exception' and \
                res[-1]['event'] == 'return' and res[-1]['func_name'] == '<module>':
            res.pop()

        self.trace = res
        return self.finalizer_func(self.trace)


def finalizer_callback(output):
    return {"trace": output}


def run_logger(user_code_input, ignore_id=False):
    pyl = PyLogger(finalizer_callback, ignore_id)
    pyl.run_script(user_code_input)
    return pyl.finalize()
