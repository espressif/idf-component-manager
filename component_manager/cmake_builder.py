import os
from textwrap import dedent


class CMakeBuilder(object):
    """Make CMake file with output"""

    def __init__(self, filepath):
        self.output_filepath = filepath

        # Create directory for out file
        directory = os.path.dirname(filepath)
        if not os.path.exists(directory):
            os.makedirs(directory)

    def _prepare_component_list(self):
        pass

    def _comment(self):
        comment = """
            # get_component_requirements: Generated function to read the dependencies of a given component.
            #
            # Parameters:
            # - component: Name of component
            # - var_requires: output variable name. Set to recursively expanded COMPONENT_REQUIRES
            #   for this component.
            # - var_private_requires: output variable name. Set to recursively expanded COMPONENT_PRIV_REQUIRES
            #   for this component.
            #
            # Throws a fatal error if 'component' is not found (indicates a build system problem).
            #
            """
        return dedent(comment)

    def build(self):
        with open(self.output_filepath, "w") as f:
            # f.write(f"set(BUILD_COMPONENTS {build_components})")
            # f.write(f"set(BUILD_COMPONENT_PATHS {build_component_paths})")
            # TODO: add support for test components
            # f.write(f"set(BUILD_TEST_COMPONENTS {build_test_components})")
            # f.write(f"set(BUILD_TEST_COMPONENT_PATHS {build_test_component_paths})")
            f.write(self._comment())
