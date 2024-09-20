# Documentation for the IDF Component Manager and ESP Component Registry

To build documentation locally, run these command from the root of the project

Install dependencies:

```sh
pip install .[docs]
```

Build the docs:

```sh
sphinx-build docs/en docs/html_output
```

Preview in the browser:

```sh
python -m webbrowser -t "file://$(pwd)/docs/html_output/index.html"
```

If you are using WSL, simply start the web server:

```sh
python -m http.server --directory docs/html_output
```
