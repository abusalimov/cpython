"""
Tests for metaclass mro() method and friends.
"""

__author__ = "Eldar Abusalimov <eldar.abusalimov@gmail.com>"

import unittest


class DebugHelperMeta(type):
    """
    Sets default __doc__ and simplifies repr() output.
    """
    def __new__(mcls, name, bases, attrs):
        if attrs.get('__doc__') is None:
            attrs['__doc__'] = name  # helps when debugging with gdb
        return type.__new__(mcls, name, bases, attrs)
    def __repr__(cls):
        return repr(cls.__name__)


class MroTest(unittest.TestCase):
    """
    Regressions for some bugs revealed through
    mcsl.mro() customization (typeobject.c: mro_internal()) and
    cls.__bases__ assignment (typeobject.c: type_set_bases()).
    """

    def setUp(self):
        self.step = 0
        self.ready = False

    def step_until(self, limit):
        ret = (self.step < limit)
        if ret:
            self.step += 1
        return ret


if __name__ == '__main__':
    unittest.main()

