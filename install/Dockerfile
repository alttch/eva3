FROM ubuntu
# prepare system
RUN apt-get update && apt-get -y upgrade && apt-get -y dist-upgrade
RUN env DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata
RUN ln -sf /usr/share/zoneinfo/Etc/UTC /etc/localtime
RUN apt-get -y install --no-install-recommends supervisor
RUN apt-get -y install --no-install-recommends curl
RUN apt-get -y install --no-install-recommends jq
RUN apt-get -y install --no-install-recommends vim-tiny
RUN apt-get -y install --no-install-recommends iproute2
RUN apt-get -y install --no-install-recommends net-tools
RUN apt-get -y install --no-install-recommends libow-dev
RUN apt-get -y install --no-install-recommends libjpeg-dev libjpeg8-dev
RUN apt-get -y install --no-install-recommends python3
RUN apt-get -y install --no-install-recommends python3-dev
RUN apt-get -y install --no-install-recommends python3-virtualenv
RUN apt-get -y install --no-install-recommends python3-distutils
RUN apt-get -y install --no-install-recommends gcc
RUN apt-get -y install --no-install-recommends python3-dev
RUN apt-get -y install --no-install-recommends python3-wheel
RUN apt-get -y install --no-install-recommends python3-pandas
RUN apt-get -y install --no-install-recommends libow-dev
# install --no-install-recommends python modules
COPY build-venv /
COPY mods.list /
COPY venv-docker /etc/venv
RUN /build-venv /
RUN rm -f /build-venv /mods.list
# final tricks
RUN apt-get -y clean
RUN ln -sf /opt/eva/bin/eva /usr/local/bin/eva-shell
RUN ln -sf /opt/eva/bin/eva /usr/local/bin/eva
# copy scripts and configs
COPY eva-supervisor-install /
COPY eva-supervisor-install.conf /etc/supervisor/conf.d/eva-install.conf
COPY eva-dist.tgz /opt/
RUN chmod +x /eva-supervisor-install
EXPOSE 162/udp 8881/udp 8812 8813 8817 8818 8828 8829
CMD [ "/usr/bin/supervisord", "-n" ]
