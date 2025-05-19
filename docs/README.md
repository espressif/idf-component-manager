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
