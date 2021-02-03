'''Tools for interaction with IDF build system'''


def build_name(name):
    name_parts = name.split('/')
    return '__'.join(name_parts)
