MANIFEST_FILENAME = 'idf_component.yml'
SLUG_BODY_REGEX = r'[a-z\d]+(?:(?:[_-](?![_-]+))|(?:[a-z\d]))*?[a-z\d]+'
SLUG_REGEX = r'^{}$'.format(SLUG_BODY_REGEX)
FULL_SLUG_REGEX = r'^((?:{slug}/{slug})|(?:{slug}))$'.format(slug=SLUG_BODY_REGEX)
WEB_DEPENDENCY_REGEX = r'^((?:{slug}/{slug})|(?:{slug}))(.*)$'.format(slug=SLUG_BODY_REGEX)