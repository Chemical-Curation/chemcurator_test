FROM tbrown02_cr_chemreg-ui

# prevent time zone config. asking questions
ARG DEBIAN_FRONTEND=noninteractive

ARG USER_ID=77777
ARG GROUP_ID=500
ARG USERNAME=tbrown02
ARG GROUPNAME=analysis
ARG PASSWORD=Cypress

# Cypress requires xvfb
RUN apk add git mc tig xterm lynx xvfb \
            iproute2 openssh-server screen xauth
RUN addgroup -g $GROUP_ID $GROUPNAME \
 && adduser -D -u $USER_ID -G $GROUPNAME $USERNAME \
 && echo $USERNAME:$PASSWORD | chpasswd \
 && mkdir /run/sshd \
 && ssh-keygen -A \
 && sed -i 's/X11Forwarding no/X11Forwarding yes/' /etc/ssh/sshd_config \
 && sed -i 's/GatewayPorts no/GatewayPorts yes/' /etc/ssh/sshd_config \
 && sed -i 's/AllowTcpForwarding no/AllowTcpForwarding yes/' /etc/ssh/sshd_config \
 && sed -i 's/#X11UseLocalhost yes/X11UseLocalhost no/' /etc/ssh/sshd_config

COPY run.sh /
# run in daemon mode
CMD ["sh", "/run.sh"]
