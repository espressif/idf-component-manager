# Documentation for the IDF Component Manager and ESP Component Registry

To build documentation locally, run these command from the root of the project

1. Install dependencies:

```sh
pip install .[docs]
```

Install the project in **development mode**:

```sh
$ pip install -e .
```

More details on development mode can be found here:
https://setuptools.pypa.io/en/latest/userguide/development_mode.html

2. Build the docs:

```sh
sphinx-build docs/en docs/html_output
```

3. Preview in the browser:

```sh
python -m webbrowser -t "file://$(pwd)/docs/html_output/index.html"
```

If you are using WSL, simply start the web server:

```sh
python -m http.server --directory docs/html_output
```

## Redirects (keeping old links working)

When you move or rename documentation pages, add redirects so existing links do not break.

This documentation uses Sphinx HTML redirects via the `sphinxext-rediraffe` extension, configured in `docs/en/conf.py` in the `rediraffe_redirects` mapping.

### How to add a redirect

1. Identify the old page and the new page.

   - Use **docnames**: paths relative to `docs/en/` without the `.rst` extension.
   - Example: `guides/faq` corresponds to the old file `docs/en/guides/faq.rst`.

2. Add a mapping entry from the old docname to the new docname.

Example redirect entry:

```python
rediraffe_redirects = {
    'guides/faq': 'troubleshooting/faq',
}
```

3. Build the docs locally and verify Sphinx prints redirect output like:

```
Writing redirects...
(good) guides/faq.html --> troubleshooting/faq.html
```
