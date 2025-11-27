# SPDX-FileCopyrightText: 2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os

from idf_component_manager.prepare_components.prepare import RunCounter


def test_create_counter_file_with_zero(tmp_path):
    counter = RunCounter(tmp_path)
    assert counter.value == 0
    # Verify the file was created
    assert counter._file_path.exists()


def test_file_path_includes_ppid(tmp_path):
    counter = RunCounter(tmp_path)
    expected_filename = f'component_manager_run_counter.{os.getppid()}'
    assert counter._file_path.name == expected_filename


def test_value_handles_missing_file(tmp_path):
    counter = RunCounter(tmp_path)
    assert counter.value == 0


def test_increase_increments_counter_by_one(tmp_path):
    counter = RunCounter(tmp_path)
    assert counter.value == 0
    counter.increase()
    assert counter.value == 1


def test_increase_multiple_times(tmp_path):
    counter = RunCounter(tmp_path)
    counter.increase()
    counter.increase()
    counter.increase()
    assert counter.value == 3


def test_increase_does_nothing_if_file_deleted(tmp_path):
    counter = RunCounter(tmp_path)
    counter.cleanup()
    # Should not raise an exception
    counter.increase()
    assert counter.value == 0  # Fallback


def test_cleanup_removes_counter_file(tmp_path):
    counter = RunCounter(tmp_path)
    assert counter._file_path.exists()
    counter.cleanup()
    assert not counter._file_path.exists()


def test_cleanup_value_after_cleanup(tmp_path):
    counter = RunCounter(tmp_path)
    counter.increase()
    assert counter.value == 1
    counter.cleanup()
    assert counter.value == 0


def test_cleanup_called_multiple_times(tmp_path):
    counter = RunCounter(tmp_path)
    counter.cleanup()
    counter.cleanup()  # Should not raise
    assert not counter._file_path.exists()


def test_single_run_typical_cmake_workflow(tmp_path):
    # First CMake run: prepare_dependencies
    assert not RunCounter(tmp_path).value > 0

    # First CMake run: inject_requirements
    assert not RunCounter(tmp_path).value > 0
    RunCounter(tmp_path).increase()

    # Cleanup after successful build
    cnt = RunCounter(tmp_path)
    cnt.cleanup()

    assert not cnt._file_path.exists()


def test_two_run_typical_cmake_workflow(tmp_path):
    # First CMake run: prepare_dependencies
    assert not RunCounter(tmp_path).value > 0

    # First CMake run: inject_requirements
    assert not RunCounter(tmp_path).value > 0
    RunCounter(tmp_path).increase()

    # Second CMake run: prepare_dependencies checks if run before
    assert RunCounter(tmp_path).value > 0  # Was run before

    # Second CMake run: inject_requirements
    assert RunCounter(tmp_path).value > 0
    RunCounter(tmp_path).increase()

    # Cleanup after successful build
    cnt = RunCounter(tmp_path)
    cnt.cleanup()

    assert not cnt._file_path.exists()


def test_three_run_typical_cmake_workflow(tmp_path):
    # First CMake run: prepare_dependencies
    assert not RunCounter(tmp_path).value > 0

    # First CMake run: inject_requirements
    assert not RunCounter(tmp_path).value > 0
    RunCounter(tmp_path).increase()

    # Second CMake run: prepare_dependencies checks if run before
    assert RunCounter(tmp_path).value > 0  # Was run before

    # Second CMake run: inject_requirements
    assert RunCounter(tmp_path).value > 0

    RunCounter(tmp_path).increase()

    # Third CMake run: prepare_dependencies checks if run before
    assert RunCounter(tmp_path).value > 0  # Was run before

    # Third CMake run: inject_requirements
    assert RunCounter(tmp_path).value > 0
    RunCounter(tmp_path).increase()

    # Cleanup after successful build
    cnt = RunCounter(tmp_path)
    cnt.cleanup()

    assert not cnt._file_path.exists()
