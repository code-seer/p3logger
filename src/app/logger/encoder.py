# LearNet Software

# Given an arbitrary piece of Python data, encode it in such a manner
# that it can be later encoded into JSON.
#   http://json.org/
#
# We use this function to encode run-time traces of data structures
# to send to the front-end.
#
# Format:
#   * None, int, long, float, str, bool - unchanged
#     (json.dumps encodes these fine verbatim)
#   * list     - ['LIST', unique_id, elt1, elt2, elt3, ..., eltN]
#   * tuple    - ['TUPLE', unique_id, elt1, elt2, elt3, ..., eltN]
#   * set      - ['SET', unique_id, elt1, elt2, elt3, ..., eltN]
#   * dict     - ['DICT', unique_id, [key1, value1], [key2, value2], ..., [keyN, valueN]]
#   * instance - ['INSTANCE', class name, unique_id, [attr1, value1], [attr2, value2], ..., [attrN, valueN]]
#   * class    - ['CLASS', class name, unique_id, [list of superclass names], [attr1, value1], [attr2, value2], ..., [attrN, valueN]]
#   * circular reference - ['CIRCULAR_REF', unique_id]
#   * other    - [<type name>, unique_id, string representation of object]
#
# the unique_id is derived from id(), which allows us to explicitly
# capture aliasing of compound values

import re, types
import sys

PYTHON_VERSION = sys.version_info[0]


class Encoder(object):
    """"Encodes Python types to Json-serializable types"""

    def __init__(self):
        # Key: real ID from id()
        # Value: a small integer for greater readability, set by cur_small_id
        self.real_to_small_IDs = {}
        self.cur_small_id = 1
        self.typeRE = re.compile("<type '(.*)'>")
        self.classRE = re.compile("<class '(.*)'>")
        self.instance_type = "<type \'instance\'>"
        self.class_type = "<type \'classobj\'>"

    def encode(self, obj, ignore_ids=False):
        return self._encode_helper(obj, set(), ignore_ids)

    def _encode_helper(self, obj, compound_obj_ids, ignore_id=False):
        # primitive type
        if obj is None or \
                type(obj) in (int, long, float, str, bool):
            return obj
        # compound type
        else:
            my_id = id(obj)
            if my_id not in self.real_to_small_IDs:
                if ignore_id:
                    self.real_to_small_IDs[my_id] = 99999
                else:
                    self.real_to_small_IDs[my_id] = self.cur_small_id
                self.cur_small_id += 1

            if my_id in compound_obj_ids:
                return ['CIRCULAR_REF', self.real_to_small_IDs[my_id]]

            new_compound_obj_ids = compound_obj_ids.union([my_id])

            typ = type(obj)

            my_small_id = self.real_to_small_IDs[my_id]

            if typ == list:
                ret = ['LIST', my_small_id]
                for e in obj: ret.append(self._encode_helper(e, new_compound_obj_ids))
            elif typ == tuple:
                ret = ['TUPLE', my_small_id]
                for e in obj: ret.append(self._encode_helper(e, new_compound_obj_ids))
            elif typ == set:
                ret = ['SET', my_small_id]
                for e in obj: ret.append(self._encode_helper(e, new_compound_obj_ids))
            elif typ == dict:
                ret = ['DICT', my_small_id]
                for (k, v) in obj.iteritems():
                    # don't display some built-in locals ...
                    if k not in ('__module__', '__return__'):
                        ret.append([self._encode_helper(k, new_compound_obj_ids),
                                    self._encode_helper(v, new_compound_obj_ids)])
            elif str(typ) == self.instance_type or str(typ) == self.class_type:
                # ugh, classRE match is a bit of a hack :(
                if str(typ) == self.instance_type:
                    ret = ['INSTANCE', obj.__class__.__name__, my_small_id]
                else:
                    superclass_names = [e.__name__ for e in obj.__bases__]
                    ret = ['CLASS', obj.__name__, my_small_id, superclass_names]

                # traverse inside of its __dict__ to grab attributes
                # (filter out useless-seeming ones):
                user_attrs = sorted([e for e in obj.__dict__.keys()
                                     if e not in ('__doc__', '__module__', '__return__')])

                for attr in user_attrs:
                    ret.append([self._encode_helper(attr, new_compound_obj_ids),
                                self._encode_helper(obj.__dict__[attr], new_compound_obj_ids)])
            else:
                typeStr = str(typ)
                m = self.typeRE.match(typeStr)
                assert m, typ
                ret = [m.group(1), my_small_id, str(obj)]

            return ret
