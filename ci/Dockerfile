ARG PYTHON_IMAGE_TAG=3.10-bullseye

FROM python:${PYTHON_IMAGE_TAG}

ARG IDF_BRANCH=master
ARG IDF_GIT_URL=https://github.com/espressif/esp-idf.git

WORKDIR /esp-idf

RUN apt-get update \
    && apt-get install -y -q libusb-1.0 cmake git ninja-build fish zsh \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip

ENV IDF_BRANCH=${IDF_BRANCH}

# Clone the IDF repository
RUN set -e \
    && git init \
    && git remote add origin ${IDF_GIT_URL} \
    && git fetch --depth 1 origin ${IDF_BRANCH} \
    && git checkout FETCH_HEAD \
    && git submodule update --init --depth 1 --recursive

RUN /esp-idf/install.sh
