FROM ubuntu
# prepare system
RUN apt-get update && apt-get -y upgrade && apt-get -y dist-upgrade
RUN env DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata
RUN ln -sf /usr/share/zoneinfo/Etc/UTC /etc/localtime
RUN apt-get -y install wget curl python3 python3-pip python3-pandas python3-cryptography python3-pysnmp4 jq vim-tiny cron iproute2 net-tools psmisc
RUN rm -f /etc/cron.daily/*
RUN apt-get -y install logrotate
# install python modules
COPY check-mods /
RUN /check-mods install
RUN rm -f /check-mods
# final tricks
COPY dlr-eva /etc/logrotate.d/eva-ics
RUN apt-get -y clean
RUN ln -sf /opt/eva/bin/eva-shell /usr/local/bin/eva-shell
# copy dstart
COPY docker-start.sh /start
COPY docker-stop.sh /stop
RUN ln -sf /stop /usr/local/bin/stop
EXPOSE 162/udp 8881/udp 8812 8813 8817 8818 8828 8829
CMD /start
