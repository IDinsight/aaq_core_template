# DESCRIPTION: Dockerfile for  
# BUILD: "make image" or "make image NAME={PROJECT_NAME} PORT={PORT}"

FROM nvcr.io/nvidia/pytorch@sha256:8b172f434079055bdc395ccc47872ccd3bf26a939db205dff40bc6b2571e8a33
LABEL maintainer="IDinsight"

ARG NAME
ARG PORT
ARG TOKEN_MACHINE_USER
ARG HOME_DIR=/usr/src/${NAME}
ENV DEBIAN_FRONTEND=noninteractive 

# Install psycopg2 dependencies
# This is the proper way to do it; psycopg2-binary (Python package
# that doesn't rely on dependencies) is practical for development
# and testing but not suitable for production

RUN apt update && \
    apt install --no-install-recommends -y build-essential software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt install --no-install-recommends -y python3.8 python3-pip python3-setuptools python3-distutils && \
    apt clean && rm -rf /var/lib/apt/lists/*



COPY requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt
RUN pip3 install "faqt[extended] @ git+https://${TOKEN_MACHINE_USER}@github.com/IDinsight/faqt.git@main"
RUN useradd -ms /bin/bash -d ${HOME_DIR} container_user
RUN chown -R container_user: ${HOME_DIR}

RUN mkdir /tmp/prometheus
RUN chown -R container_user: /tmp/prometheus

ENV PYTHONPATH "${PYTHONPATH}:${HOME_DIR}"
ENV PORT ${PORT}

RUN python3 -m nltk.downloader stopwords punkt -d ${HOME_DIR}/nltk_data

COPY . ${HOME_DIR}
WORKDIR ${HOME_DIR}
RUN ["chmod", "+x", "startup.sh"]

EXPOSE ${PORT}

# Note that we don't switch to container_user here
# Rather, it's done when starting gunicorn with su-exec;
# see startup.sh for more details

CMD ["./startup.sh"]
