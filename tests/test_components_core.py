import pytest

from .context import components


def test_build_parser():
    parser = components.build_parser()
    args = parser.parse_args(["install", "a", "b"])
    assert args.command == "install"
    assert args.components == ["a", "b"]


def test_parse_args_for_add():
    with pytest.raises(components.ArgumentError) as einfo:
        components.parse_args(["add"])

    assert "Command 'add' requires list of components" in str(einfo.value)


def test_parse_args_for_install():
    with pytest.raises(components.ArgumentError) as einfo:
        components.parse_args(["install", "package"])

    assert "please run `components.py add package`" in str(einfo.value)
