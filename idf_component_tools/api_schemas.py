from schema import Optional, Or, Schema
from six import string_types

ERROR_SCHEMA = Schema(
    {
        'error': Or(*string_types),
        'messages': Or([Or(*string_types)], {Or(*string_types): object}),
        Optional(str): object,
    })
