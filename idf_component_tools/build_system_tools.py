'''Tools for interaction with IDF build system'''
import os

from idf_component_tools.errors import ProcessingError


def build_name(name):
    name_parts = name.split('/')
    return '__'.join(name_parts)


def get_env_idf_target():  # type: () -> str
    """
    `IDF_TARGET` should be set automatically while compiling with cmake
    """
    env_idf_target = os.getenv('IDF_TARGET')
    if not env_idf_target:
        raise ProcessingError('IDF_TARGET is not set, should be set by CMake, please check your configuration')
    return env_idf_target
