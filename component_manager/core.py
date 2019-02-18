"""Core module of component manager"""
from __future__ import print_function

import os

from .manifest_pipeline import ManifestPipeline


class ComponentManager(object):
    def __init__(self, path):
        # Set path of manifest file for the project
        self.manifest_path = (
            os.path.join(path, "idf_project.yml") if os.path.isdir(path) else path
        )

        # Working directory
        self.path = path if os.path.isdir(path) else os.path.dirname(path)

    def add(self, components):
        print("Adding %s to manifest" % ", ".join(components))
        print("Not implemented yet")

    def install(self):
        ManifestPipeline(self.manifest_path).prepare()
        print("Installing components from manifest")

    def update(self, components=None):
        if components is None:
            components = []
        print("Updating %s" % ", ".join(components))
        print("Not implemented yet")

    def eject(self, components):
        print("Ejecting %s" % ", ".join(components))
        print("Not implemented yet")
