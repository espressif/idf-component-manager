from idf_component_tools.manifest import Manifest


def dist_name(manifest):  # type: (Manifest) -> str
    if manifest.version is None:
        raise ValueError('Version is required in this manifest')

    return '{}_{}'.format(manifest.name, manifest.version)


def archive_filename(manifest):  # type: (Manifest) -> str
    return '{}.tgz'.format(dist_name(manifest))
