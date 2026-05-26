# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import esp_pylib.errors

from idf_component_tools.errors import FatalError, NothingToDoError


class TestFatalError:
    def test_is_subclass_of_pylib_fatal_error(self):
        assert issubclass(FatalError, esp_pylib.errors.FatalError)

    def test_is_subclass_of_runtime_error(self):
        assert issubclass(FatalError, RuntimeError)

    def test_default_exit_code(self):
        assert FatalError.exit_code == 2

    def test_exit_code_kwarg_overrides(self):
        err = FatalError('msg', exit_code=7)
        assert err.exit_code == 7

    def test_default_exit_code_not_mutated_by_instance(self):
        FatalError('msg', exit_code=7)
        assert FatalError.exit_code == 2

    def test_args_flow_into_message(self):
        err = FatalError('boom')
        assert str(err) == 'boom'

    def test_instance_is_catchable_as_runtime_error(self):
        raised = False
        try:
            raise FatalError('oops')
        except RuntimeError:
            raised = True
        assert raised


class TestNothingToDoError:
    def test_exit_code_is_144(self):
        assert NothingToDoError.exit_code == 144

    def test_is_subclass_of_fatal_error(self):
        assert issubclass(NothingToDoError, FatalError)
