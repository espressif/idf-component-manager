from .context import components


def test_parse_args():
    args = components.parse_args(['install', 'a', 'b'])
    assert args.command == 'install'
    assert args.components == ['a', 'b']
