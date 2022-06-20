ARG PYTHON_IMAGE_TAG=3.10-bullseye

FROM python:${PYTHON_IMAGE_TAG} as idf_tools

ARG API_TOKEN=
ARG IDF_BRANCH=master
ARG IDF_PROJ_ID=
ARG IDF_FILE_API_URL=

RUN wget --no-verbose -O idf_tools.py --header="PRIVATE-TOKEN: ${API_TOKEN}" "${IDF_FILE_API_URL}/tools%2Fidf_tools%2Epy/raw?ref=${IDF_BRANCH}" \
  && wget --no-verbose -O tools.json --header="PRIVATE-TOKEN: ${API_TOKEN}" "${IDF_FILE_API_URL}/tools%2Ftools%2Ejson/raw?ref=${IDF_BRANCH}" \
  # release/v4.3 or earlier branches does not have this file
  && (wget --no-verbose -O python_version_checker.py --header="PRIVATE-TOKEN: ${API_TOKEN}" "${IDF_FILE_API_URL}/tools%2Fpython_version_checker%2Epy/raw?ref=${IDF_BRANCH}" || true)

RUN python ./idf_tools.py --non-interactive --tools-json ./tools.json download --platform linux-amd64 all \
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
