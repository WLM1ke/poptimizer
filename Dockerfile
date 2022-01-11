FROM nvidia/cuda:11.0.3-cudnn8-runtime-ubuntu20.04
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get -q update \
 && apt-get install -yq --no-install-recommends \
    wget \
    ca-certificates \
    sudo \
    locales \
    fonts-liberation \
    run-one \
    libx11-xcb1 \
    libxtst6 \
    gnupg \
 && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen
RUN wget -qO - https://www.mongodb.org/static/pgp/server-5.0.asc | apt-key add -
RUN echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/5.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-5.0.list
RUN apt-get update && apt-get install -y mongodb-org-tools python3.9 python3-pip &&  apt-get clean && rm -rf /var/lib/apt/lists/*
RUN python3.9 -m pip install -U pip
WORKDIR /opt/app
COPY requirements.txt .
RUN python3.9 -m pip install -U -r requirements.txt
#RUN apt-get update \
#    && apt-get install -y wget gnupg \
#    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
#    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
#    && apt-get update \
#    && apt-get install -y google-chrome-stable fonts-ipafont-gothic fonts-wqy-zenhei fonts-thai-tlwg fonts-kacst fonts-freefont-ttf libxss1 \
#      --no-install-recommends \
#    && rm -rf /var/lib/apt/lists/*
#RUN apt-get update && apt-get install libx11-xcb1 libxtst6
COPY fix-permissions /usr/local/bin/fix-permissions
RUN chmod a+rx /usr/local/bin/fix-permissions
ARG NB_USER="user"
ARG NB_UID="1000"
ARG NB_GID="100"
RUN echo "auth requisite pam_deny.so" >> /etc/pam.d/su && \
    sed -i.bak -e 's/^%admin/#%admin/' /etc/sudoers && \
    sed -i.bak -e 's/^%sudo/#%sudo/' /etc/sudoers && \
    useradd -m -s /bin/bash -N -u $NB_UID $NB_USER && \
    chmod g+w /etc/passwd && \
    fix-permissions $HOME
USER $NB_UID
# RUN mkdir "/home/$NB_USER"
RUN pyppeteer-install
USER root
COPY . /opt/app/
RUN python3.9 setup.py install
USER $NB_USER
ENTRYPOINT ["bash"]
#ENTRYPOINT ["python3.9", "/opt/app/poptimizer/__main__.py", "evolve" ]
