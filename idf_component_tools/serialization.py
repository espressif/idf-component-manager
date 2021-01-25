'''Class decorators to help with serialization'''

from numbers import Number

from six import string_types

try:
    from collections.abc import Mapping, Iterable
except ImportError:
    from collections import Mapping, Iterable

BASIC_TYPES = (Number, type(None)) + string_types


def serialize(value):
    '''Serialize value'''
    if isinstance(value, BASIC_TYPES):
        return value

    if isinstance(value, Mapping):
        return {k: serialize(v) for (k, v) in value.items()}

    if isinstance(value, Iterable):
        return [serialize(v) for v in value]

    return value.serialize()


def serializable(_cls=None, like='dict'):
    """Returns the same class with `serialize` method to handle nested structures.
    Requires `_serializaton_properties` to be defined in the class"""
    def wrapper(cls):
        # Check if class is already serializable by custom implementation
        if hasattr(cls, 'serialize'):
            return cls

        if like == 'dict':

            def _serialize(self):
                # Use all properties if list is not selected
                properties = set(getattr(self, '_serializaton_properties', self.__dict__.keys()))
                return {prop: serialize(getattr(self, prop)) for prop in properties}

        elif like == 'str':

            def _serialize(self):
                return str(self)
        else:
            raise TypeError("'%s' is not known type for serialization" % like)

        setattr(cls, 'serialize', _serialize)
        return cls

    # handle both @serializable and @serializable() calls
    if _cls is None:
        return wrapper

    return wrapper(_cls)
