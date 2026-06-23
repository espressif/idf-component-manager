# Documentation for the IDF Component Manager and ESP Component Registry

This documentation is built with [ESP-Docs](https://docs.espressif.com/projects/esp-docs/en/latest/index.html),
Espressif's Sphinx-based documentation build system.

## Building the docs locally

Run the following commands from the root of the project.

1. Install the build dependencies (ESP-Docs, the project itself, and the
   project-specific Sphinx extensions):

   ```sh
   pip install '.[docs]'
   ```

   > `cairosvg` (pulled in by ESP-Docs) needs the Cairo system library.
   > See the [ESP-Docs guide](https://docs.espressif.com/projects/esp-docs/en/latest/building-documentation/building-documentation-locally.html)
   > if you hit issues installing it.

2. Build the HTML docs with `build-docs`:

   ```sh
   cd docs
   build-docs -l en
   ```

   The output is placed in `docs/_build/en/generic/html`.

3. Preview in the browser:

   ```sh
   python -m webbrowser -t "file://$(pwd)/_build/en/generic/html/index.html"
   ```

   If you are using WSL, simply start a web server:

   ```sh
   python -m http.server --directory _build/en/generic/html
   ```

For more options (PDF output, building a single page, etc.) run `build-docs --help`
or see the [ESP-Docs user guide](https://docs.espressif.com/projects/esp-docs/en/latest/building-documentation/building-documentation-locally.html).

## Redirects (keeping old links working)

When you move or rename documentation pages, add redirects so existing links do not break.

This documentation uses the ESP-Docs `html_redirects` extension. Redirects are
listed in [`page_redirects.txt`](page_redirects.txt) and read by
[`conf_common.py`](conf_common.py) into the `html_redirect_pages` configuration.

### How to add a redirect

1. Identify the old page and the new page.

   - Use **docnames**: paths relative to `docs/en/` without the `.rst` extension.
   - Example: `guides/faq` corresponds to the old file `docs/en/guides/faq.rst`.

2. Add a line to `page_redirects.txt` mapping the old docname to the new one,
   separated by a space:

   ```text
   guides/faq   troubleshooting/faq
   ```

   The new URL may be a relative docname (as above) or an absolute URL wrapped in
   double quotes, e.g. `"https://example.com/"`.

3. Build the docs locally and verify Sphinx prints redirect output like:

   ```
   HTML file guides/faq.html redirects to URL troubleshooting/faq.html
   ```

See the [ESP-Docs guide on redirecting documents](https://docs.espressif.com/projects/esp-docs/en/latest/writing-documentation/redirecting-documents.html)
for details.
