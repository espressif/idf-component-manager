ARG PYTHON_IMAGE_TAG=3.10-bullseye

FROM python:${PYTHON_IMAGE_TAG} as idf_tools

ARG API_TOKEN=
ARG IDF_BRANCH=master
ARG IDF_PROJ_ID=
ARG IDF_GIT_URL=

RUN set -e \
    && git init \
    && git remote add origin https://gitlab-ci-token:${API_TOKEN}@${IDF_GIT_URL} \
    && git fetch --depth 1 origin ${IDF_BRANCH} \
    && git checkout FETCH_HEAD

RUN python ./tools/idf_tools.py --non-interactive --tools-json ./tools/tools.json download --platform linux-amd64 all \
  && ls -lA /root/.espressif/dist/

FROM python:${PYTHON_IMAGE_TAG}

RUN apt-get update \
    && apt-get install -y -q libusb-1.0 cmake git ninja-build \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root/.espressif/dist
COPY --from=idf_tools /root/.espressif/dist/* ./

# idf install.sh would prioritize the python3, make the /usr/bin/python3 symbolic link always point to /usr/bin/python
RUN rm -f /usr/bin/python3 && ln -s /usr/bin/python /usr/bin/python3
