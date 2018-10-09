import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="component_manager",
    version="0.0.1",
    author="Sergei Silnov",
    author_email="sergei.silnov@espressif.com",
    description="Component Manager for ESP IDF",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.espressif.cn:6688/sergei.silnov/component-manager",
    packages=setuptools.find_packages(),
    install_requires=['requests', 'future']
)
