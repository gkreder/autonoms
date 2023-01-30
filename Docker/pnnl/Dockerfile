FROM ubuntu:18.04


RUN dpkg --add-architecture i386
# first create user and group for all the X Window stuff
# required to do this first so we have consistent uid/gid between server and client container
RUN addgroup --system xusers

# uid 36480 = crude solution
RUN adduser --home /home/xclient \ 
--disabled-password --uid 36480 \ 
--shell /bin/bash \ 
--gecos "user for running an xclient application" \ 
--ingroup xusers --quiet xclient


# Use the waitonprocess script to wait on wineserver.
USER root
COPY waitonprocess.sh /scripts/
RUN chmod a+rx /scripts/waitonprocess.sh

# we need wget, bzip2, wine from winehq,
# xvfb to fake X11 for winetricks during installation,
# and winbind because wine complains about missing

# Setup a Wine prefix
ENV WINEARCH=win64


RUN apt-get update && \
    apt-get -y install wget gnupg unzip && \
    apt-get update && \
    apt-get -y --install-recommends install \
      bzip2 \
      xvfb \
      cabextract \
      && \
    wget https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks \
      -O /usr/local/bin/winetricks && chmod +x /usr/local/bin/winetricks



#Add 32-bit architecture
RUN dpkg --add-architecture i386
RUN apt-get update

# Install Wine
RUN apt-get install -y software-properties-common gnupg2
RUN wget -nc https://dl.winehq.org/wine-builds/winehq.key
RUN apt-key add winehq.key
RUN apt-add-repository 'deb https://dl.winehq.org/wine-builds/ubuntu/ bionic main'
RUN apt-get install -y --install-recommends winehq-stable winbind
ENV WINEDEBUG=fixme-all


# ENV WINEARCH win64

# WINE does not like running as root
USER xclient
WORKDIR /home/xclient

# wineserver needs to shut down properly!!!
ENV WINEDEBUG -all,err+all

RUN winetricks -q win7 \
	&& /scripts/waitonprocess.sh wineserver

RUN xvfb-run winetricks -q vcrun2008 dotnet48 \
	&& /scripts/waitonprocess.sh wineserver

# Set up working directory and permissions to let user xclient save data
USER root
RUN mkdir /PNNL
ADD https://panomics.pnnl.gov/downloads/installers/PNNL-Preprocessor_4.0_2021.10.27.zip /PNNL
RUN unzip /PNNL/PNNL-Preprocessor_4.0_2021.10.27.zip -d /PNNL
RUN mkdir /data
RUN chmod 777 /data
RUN chown xclient:xusers /data
RUN chown xclient:xusers /
RUN chown -R xclient:xusers /PNNL 
RUN chmod -R 777 /PNNL/PNNL-Preprocessor
WORKDIR /data

USER xclient



