# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import pytest

from idf_component_tools.serialization import serializable


def test_serialize_default_fields():
    @serializable
    class TestSerializableClass:
        _serialization_properties = [
            'field1',
            {'name': 'field2', 'default': True, 'serialize_default': False},
        ]

        def __init__(self, field1, field2):
            self.field1 = field1
            self.field2 = field2

    serializable_object = TestSerializableClass(field1='test', field2=True)

    assert 'field2' in serializable_object.serialize()
    assert 'field2' not in serializable_object.serialize(serialize_default=False)


def test_serialize_object_field():
    @serializable
    class TestSerializableClass:
        _serialization_properties = [
            'another_class',
        ]

        def __init__(self, another_class):
            self.another_class = another_class

    @serializable
    class TestSerializableAnotherClass:
        _serialization_properties = ['field1', 'field2']

        def __init__(self, field1, field2):
            self.field1 = field1
            self.field2 = field2

    serializable_object = TestSerializableClass(
        another_class=TestSerializableAnotherClass('test', 12)
    )
    serialize = serializable_object.serialize()

    assert 'another_class' in serialize
    assert 'field1' in serialize['another_class']
    assert 'field2' in serialize['another_class']


def test_serialize_object_cyclic_references():
    @serializable
    class TestSerializableClass:
        _serialization_properties = [
            'another_class',
        ]

        def __init__(self, another_class=None):
            self.another_class = another_class

    @serializable
    class TestSerializableAnotherClass:
        _serialization_properties = [
            'another_class',
        ]

        def __init__(self, another_class=None):
            self.another_class = another_class

    serializable_object = TestSerializableClass()
    another_serializable_object = TestSerializableAnotherClass()

    serializable_object.another_class = another_serializable_object
    another_serializable_object.another_class = serializable_object

    with pytest.raises(RuntimeError):  # Recursion Error for python < 3.5
        serializable_object.serialize()


def test_serialize_optional_arguments():
    @serializable
    class TestSerializableClass:
        _serialization_properties = [
            'req_field',
            'none_field',
            'bool_field',
            'str_field',
        ]

        def __init__(self, req_field, opt_field1=None, opt_field2=False, opt_field3=''):
            self.req_field = req_field
            self.none_field = opt_field1
            self.bool_field = opt_field2
            self.str_field = opt_field3

    serializable_object = TestSerializableClass(12, opt_field3='hello')
    serialize = serializable_object.serialize()

    assert serialize['bool_field'] is False
    assert serialize['none_field'] is None
    assert serialize['req_field'] == 12
    assert serialize['str_field'] == 'hello'


def test_serialize_in_inner_class():
    @serializable
    class TestSerializableClass:
        _serialization_properties = [
            'another_class',
        ]

        def __init__(self, another_class):
            self.another_class = another_class

    class TestSerializeFunctionClass:
        def __init__(self, test_field):
            self.test_field = test_field

        def serialize(self):
            return 'Serialize: {}'.format(self.test_field)

    serializable_object = TestSerializableClass(TestSerializeFunctionClass('field'))
    serialize = serializable_object.serialize()

    assert 'another_class' in serialize
    assert serialize['another_class'] == 'Serialize: field'


def test_serialize_in_class():
    @serializable
    class TestSerializeFunctionClass:
        _serialization_properties = [
            'test_field',
        ]

        def __init__(self, test_field):
            self.test_field = test_field

        def serialize(self):
            return 'Check: {}'.format(self.test_field)

    serializable_object = TestSerializeFunctionClass('test')
    serialize = serializable_object.serialize()

    assert serialize == 'Check: test'


def test_serialize_like_str():
    @serializable(like='str')
    class TestSerializeClass:
        _serialization_properties = [
            'field1',
        ]

        def __init__(self, field):
            self.field1 = field

        def __str__(self):
            return 'Serialize: {}'.format(self.field1)

    serializable_object = TestSerializeClass('test')
    serialize = serializable_object.serialize()

    assert serialize == 'Serialize: test'


def test_serialize_like_unknown_type():
    with pytest.raises(TypeError):

        @serializable(like='bool')
        class TestSerializeClass:
            pass


def test_serialize_dictionary():
    @serializable
    class TestSerializableClass:
        _serialization_properties = [
            'dict_field',
        ]

        def __init__(self, dict_field):
            self.dict_field = dict_field

    serializable_object = TestSerializableClass(
        {
            'field1': True,
            'field2': None,
            'field3': 'Hello',
            'field4': 12,
            'field5': 0.56,
        }
    )
    serialize = serializable_object.serialize()

    assert 'dict_field' in serialize
    assert serialize['dict_field']['field1'] is True
    assert serialize['dict_field']['field2'] is None
    assert serialize['dict_field']['field3'] == 'Hello'
    assert serialize['dict_field']['field4'] == 12
    assert serialize['dict_field']['field5'] == 0.56


def test_serialize_list():
    @serializable
    class TestSerializableClass:
        _serialization_properties = [
            'list_field',
        ]

        def __init__(self, list_field):
            self.list_field = list_field

    list_field = [True, None, 'Hello', 12, 0.56]
    serializable_object = TestSerializableClass(list_field)
    serialize = serializable_object.serialize()

    assert 'list_field' in serialize
    assert serialize['list_field'] == list_field
