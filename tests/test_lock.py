import filecmp
import os
from collections import OrderedDict

import pytest

from component_manager.lock import LockParser


class TestLockParser(object):
    def test_load_valid_lock(self):
        lock_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "manifests", "components.lock"
        )
        parser = LockParser(lock_path)

        lock = parser.load()

        assert lock["component_manager_version"] == "1.0.3"
        assert (
            lock["components"]["test_cmp"]["source"]["url"]
            == "https://repo.example.com/aws-iot/1.2.7.tgz"
        )

    def test_load_invalid_lock(self, capsys):
        lock_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "manifests",
            "invalid_components.lock",
        )
        parser = LockParser(lock_path)

        with pytest.raises(SystemExit) as e:
            parser.load()

        captured = capsys.readouterr()
        assert e.type == SystemExit
        assert e.value.code == 1
        assert captured.out.startswith("Error")

    # @pytest.fixture(scope="session")
    def test_lock_dump(self, tmp_path):
        lock_path = os.path.join(str(tmp_path), "components.lock")
        parser = LockParser(lock_path)
        valid_lock_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "manifests", "components.lock"
        )
        solution = parser.load()
        solution["component_manager_version"] = "1.0.3"
        solution["idf_version"] = "3.0.2"
        solution[
            "manifest_hash"
        ] = "f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b"

        components = OrderedDict(
            [
                (
                    "test_cmp",
                    OrderedDict(
                        [
                            ("version", "1.2.7"),
                            (
                                "hash",
                                "f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b",
                            ),
                            ("source_type", "url"),
                            (
                                "source",
                                OrderedDict(
                                    [
                                        (
                                            "url",
                                            "https://repo.example.com/aws-iot/1.2.7.tgz",
                                        )
                                    ]
                                ),
                            ),
                        ]
                    ),
                )
            ]
        )

        solution["components"] = components

        parser.dump(solution)

        assert filecmp.cmp(lock_path, valid_lock_path, shallow=False)
