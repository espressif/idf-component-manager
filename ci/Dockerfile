ARG PYTHON_IMAGE_TAG=3.10-bullseye

FROM python:${PYTHON_IMAGE_TAG}

ARG API_TOKEN=
ARG IDF_BRANCH=master
ARG IDF_PROJ_ID=
ARG IDF_GIT_URL=

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
    && git remote add origin https://github.com/espressif/esp-idf.git \
    && git fetch --depth 1 origin ${IDF_BRANCH} \
    && git checkout FETCH_HEAD

RUN python ./tools/idf_tools.py --non-interactive --tools-json ./tools/tools.json download --platform linux-amd64 all \
  && ls -lA /root/.espressif/dist/
