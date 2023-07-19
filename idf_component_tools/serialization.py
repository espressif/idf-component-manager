# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
'''Class decorators to help with serialization'''

from collections import OrderedDict
from numbers import Number

from six import string_types

try:
    from collections.abc import Iterable, Mapping
except ImportError:
    from collections import Iterable, Mapping  # type: ignore

BASIC_TYPES = (Number, type(None)) + string_types


def _by_key(item):
    return item[0]


def serialize(value, serialize_default=True):
    '''Serialize value'''
    if isinstance(value, BASIC_TYPES):
        return value

    if isinstance(value, Mapping):
        return OrderedDict(
            (k, serialize(v, serialize_default)) for (k, v) in sorted(value.items(), key=_by_key)
        )

    if isinstance(value, Iterable):
        return [serialize(v, serialize_default) for v in value]

    try:
        return value.serialize(serialize_default)
    except TypeError:
        return value.serialize()


def serializable(_cls=None, like='dict'):
    """Returns the same class with `serialize` method to handle nested structures.
    Requires `_serialization_properties` to be defined in the class"""

    def wrapper(cls):
        # Check if class is already serializable by custom implementation
        if hasattr(cls, 'serialize'):
            return cls

        if like == 'dict':

            def _serialize(self, serialize_default=True):
                # Use all properties if list is not selected
                properties = getattr(self, '_serialization_properties', [])
                serialization_properties = OrderedDict()
                for prop in properties:
                    if isinstance(prop, dict):
                        property_name = prop['name']
                        if (
                            not serialize_default
                            and not prop.get('serialize_default', True)
                            and getattr(self, property_name) == prop.get('default', None)
                        ):
                            continue

                        serialization_properties[property_name] = serialize(
                            getattr(self, property_name), serialize_default
                        )
                    else:
                        serialization_properties[prop] = serialize(
                            getattr(self, prop), serialize_default
                        )
                return OrderedDict(sorted(serialization_properties.items()))

        elif like == 'str':

            def _serialize(self, serialize_default=True):
                return str(self)

        else:
            raise TypeError("'%s' is not known type for serialization" % like)

        setattr(cls, 'serialize', _serialize)
        return cls

    # handle both @serializable and @serializable() calls
    if _cls is None:
        return wrapper

    return wrapper(_cls)
