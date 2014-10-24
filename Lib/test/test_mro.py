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

    def test_incomplete_set_bases_on_self(self):
        """
        type_set_bases must be aware that type->tp_mro can be NULL.
        """
        class M(DebugHelperMeta):
            def mro(cls):
                if self.step_until(1):
                    assert cls.__mro__ is None
                    cls.__bases__ += ()

                return type.mro(cls)

        class A(metaclass=M):
            pass

    def test_reent_set_bases_on_base(self):
        """
        Deep reentrancy must not over-decref old_mro.
        """
        class M(DebugHelperMeta):
            def mro(cls):
                if cls.__mro__ is not None and cls.__name__ == 'B':
                    # 4-5 steps are usually enough to make it crash somewhere
                    if self.step_until(10):
                        A.__bases__ += ()

                return type.mro(cls)

        class A(metaclass=M):
            pass
        class B(A):
            pass
        B.__bases__ += ()

    def test_reent_set_bases_on_direct_base(self):
        """
        Similar to test_reent_set_bases_on_base, but may crash differently.
        """
        class M(DebugHelperMeta):
            def mro(cls):
                base = cls.__bases__[0]
                if base is not object:
                    if self.step_until(5):
                        base.__bases__ += ()

                return type.mro(cls)

        class A(metaclass=M):
            pass
        class B(A):
            pass
        class C(B):
            pass


if __name__ == '__main__':
    unittest.main()

