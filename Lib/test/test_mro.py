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

    def test_reent_set_bases_tp_base_cycle(self):
        """
        type_set_bases must check for an inheritance cycle not only through
        MRO of the type, which may be not yet updated in case of reentrance,
        but also through tp_base chain, which is assigned before diving into
        inner calls to mro().

        Otherwise, the following snippet can loop forever:
            do {
                // ...
                type = type->tp_base;
            } while (type != NULL);

        Functions that rely on tp_base (like solid_base and PyType_IsSubtype)
        would not be happy in that case, causing a stack overflow.
        """
        class M(DebugHelperMeta):
            def mro(cls):
                if self.ready:
                    if cls.__name__ == 'B1':
                        B2.__bases__ = (B1,)
                    if cls.__name__ == 'B2':
                        B1.__bases__ = (B2,)
                return type.mro(cls)

        class A(metaclass=M):
            pass
        class B1(A):
            pass
        class B2(A):
            pass

        self.ready = True
        with self.assertRaises(TypeError):
            B1.__bases__ += ()

    def test_tp_subclasses_cycle_in_update_slots(self):
        """
        type_set_bases must check for reentrancy upon finishing its job
        by updating tp_subclasses of old/new bases of the type.
        Otherwise, an implicit inheritance cycle through tp_subclasses
        can break functions that recurse on elements of that field
        (like recurse_down_subclasses and mro_hierarchy) eventually
        leading to a stack overflow.
        """
        class M(DebugHelperMeta):
            def mro(cls):
                if self.ready and cls.__name__ == 'C':
                    self.ready = False
                    C.__bases__ = (B2,)
                return type.mro(cls)

        class A(metaclass=M):
            pass
        class B1(A):
            pass
        class B2(A):
            pass
        class C(A):
            pass

        self.ready = True
        C.__bases__ = (B1,)
        B1.__bases__ = (C,)

        self.assertEqual(C.__bases__, (B2,))
        self.assertEqual(B2.__subclasses__(), [C])
        self.assertEqual(B1.__subclasses__(), [])

        self.assertEqual(B1.__bases__, (C,))
        self.assertEqual(C.__subclasses__(), [B1])

    def test_tp_subclasses_cycle_error_return_path(self):
        """
        The same as test_tp_subclasses_cycle_in_update_slots, but tests
        a code path executed on error (goto bail).
        """
        class E(Exception):
            pass
        class M(DebugHelperMeta):
            def mro(cls):
                if self.ready and cls.__name__ == 'C':
                    if C.__bases__ == (B2,):
                        self.ready = False
                    else:
                        C.__bases__ = (B2,)
                        raise E
                return type.mro(cls)

        class A(metaclass=M):
            pass
        class B1(A):
            pass
        class B2(A):
            pass
        class C(A):
            pass

        self.ready = True
        with self.assertRaises(E):
            C.__bases__ = (B1,)
        B1.__bases__ = (C,)

        self.assertEqual(C.__bases__, (B2,))
        self.assertEqual(C.__mro__, tuple(type.mro(C)))

    def test_incomplete_extend(self):
        """
        Extending an unitialized type with type->tp_mro == NULL must
        throw a reasonable TypeError exception, instead of failing
        with PyErr_BadInternalCall.
        """
        class M(DebugHelperMeta):
            def mro(cls):
                if cls.__mro__ is None and cls.__name__ != 'X':
                    with self.assertRaises(TypeError):
                        class X(cls):
                            pass

                return type.mro(cls)

        class A(metaclass=M):
            pass


if __name__ == '__main__':
    unittest.main()

