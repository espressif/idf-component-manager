"""Core module of component manager"""
from __future__ import print_function

import os

from .manifest import ManifestParser


class ComponentManager(object):
    def __init__(self, path):
        # Set path of manifest file
        self.manifest_path = (
            os.path.join(path, "manifest.yml") if os.path.isdir(path) else path
        )

        # Working directory
        self.path = path if os.path.isdir(path) else os.path.dirname(path)

    def add(self, components):
        print("Adding %s to manifest" % ", ".join(components))

    def install(self):
        print("Installing components from manifest")
        entries = ManifestParser(self.path)

    def update(self, components=[]):
        print("Updating %s" % ", ".join(components))

    def eject(self, components):
        print("Updating %s" % ", ".join(components))
