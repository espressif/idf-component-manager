import os

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
            lock["components"]["aws-iot"]["source"]["url"]
            == "https://repo.example.com/aws-iot/1.2.7.tgz"
        )
