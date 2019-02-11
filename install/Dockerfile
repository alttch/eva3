FROM ubuntu
# prepare system
RUN apt-get update && apt-get -y upgrade && apt-get -y dist-upgrade
RUN env DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata
RUN ln -sf /usr/share/zoneinfo/Etc/UTC /etc/localtime
RUN apt-get -y install wget curl python3 python3-pip python3-pandas python3-cryptography python3-pysnmp4
RUN apt-get -y clean
# install python modules
COPY check-mods /
RUN /check-mods install
RUN rm -f /check-mods
# final tricks
RUN ln -sf /opt/eva/bin/eva-shell /usr/local/bin/eva-shell
# copy dstart
COPY dstart.sh /
CMD /dstart.sh
