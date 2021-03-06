FROM debian

# prevent time zone config. asking questions
ARG DEBIAN_FRONTEND=noninteractive

ARG USER_ID=77777
ARG GROUP_ID=500
ARG USERNAME=tbrown02
ARG GROUPNAME=analysis
ARG PASSWORD=Cypress

# -l in useradd needed to avoid some large sparse log file
# https://github.com/moby/moby/issues/5419
RUN apt-get update || true \
 && apt-get install -y git mc aptitude tig xterm lynx npm \
            iproute2 openssh-server screen nodejs firefox-esr \
            libxcursor1 libnss3 libgdk-pixbuf2.0-0 wget \
            libgtk-3-dev libxss-dev libasound2-dev \
 && groupadd -g $GROUP_ID $GROUPNAME \
 && useradd -l -u $USER_ID -g $GROUPNAME -m $USERNAME \
 && echo $USERNAME:$PASSWORD | chpasswd \
 && mkdir /run/sshd

# START: build steps from chemcurator_vuejs/Dockerfile

# make the 'app' folder the current working directory
WORKDIR /app
RUN chown $USERNAME.$GROUPNAME /app
USER $USERNAME

# install simple http server for serving static content
RUN npm install http-server

# copy both 'package.json' and 'package-lock.json' (if available)
COPY chemcurator_vuejs/package*.json /app/

# install project dependencies
RUN npm install

# copy project files and folders to the current working directory (i.e. 'app' folder)
COPY chemcurator_vuejs/ /app/

# build app for production with minification
# RUN npm run build

# END: build steps from chemcurator_vuejs/Dockerfile

# run in non-daemon mode
USER root

ARG VUE_APP_API_URL
ARG VUE_APP_KETCHER_URL
RUN echo "VUE_APP_API_URL=${VUE_APP_API_URL}" >> /etc/environment \
 && echo "VUE_APP_KETCHER_URL=${VUE_APP_KETCHER_URL}" >> /etc/environment

ENTRYPOINT ["/usr/sbin/sshd", "-D"]
