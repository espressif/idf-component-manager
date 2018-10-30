"""Classes to work with manifest file"""
import os
from shutil import copyfile


class ManifestParser(object):
    """Parser for manifest file"""

    def __init__(self, path):
        # Path of manifest file
        self.path = path

    def check_filename(self):
        """Check manifest's filename"""
        filename = os.path.basename(self.path)

        if filename != "manifest.yml":
            print(
                "Warning: it's recommended to store your component's list in \"manifest.yml\" at project's root"
            )

    def init_manifest(self):
        """Lazily create manifest file if it doesn't exist"""
        example_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "manifest_example.yml"
        )

        if not os.path.exists(self.path):
            copyfile(example_path, self.path)
