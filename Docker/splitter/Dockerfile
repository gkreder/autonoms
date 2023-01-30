FROM ubuntu:18.04

# Install wget
RUN apt-get update
RUN apt-get install -y wget

RUN apt-get update && \
    apt-get -y install wget gnupg && \
    apt-get update && \
    apt-get -y --install-recommends install \
      bzip2 \
      xvfb \
      cabextract \
      && \
    wget https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks \
      -O /usr/local/bin/winetricks && chmod +x /usr/local/bin/winetricks



      # # Install OpenMS

      # RUN apt-get update && \
      #         apt-get -y upgrade && \
      #         apt-get install -y  --allow-unauthenticated gdebi python3.7 python3-pip


# RUN python3.7 -m pip install --upgrade pip
#       RUN mkdir /openMS
#       # ADD https://abibuilder.informatik.uni-tuebingen.de/archive/openms/OpenMSInstaller/release/2.7.0/OpenMS-2.7.0-Debian-Linux-x86_64.deb /openMS
#       ADD https://github.com/OpenMS/OpenMS/releases/download/Release2.7.0/OpenMS-2.7.0-Debian-Linux-x86_64.deb /openMS

#       RUN gdebi /openMS/OpenMS-2.7.0-Debian-Linux-x86_64.deb -n


#       RUN python3.7 -m pip install pyopenms==2.7.0

#       ADD sep_retention_time.py /usr/bin/sep_retention_time.py

#       run chmod +x /usr/bin/sep_retention_time.py

#       RUN apt-get update && \
#               apt-get -y upgrade && \
#               apt-get install -y  --allow-unauthenticated unzip

#       RUN mkdir /PNNL
#       ADD https://panomics.pnnl.gov/downloads/installers/PNNL-Preprocessor_4.0_2021.10.27.zip /PNNL
#       RUN unzip /PNNL/PNNL-Preprocessor_4.0_2021.10.27.zip

#

LABEL description="Convert LC/MS or GC/MS RAW vendor files to mzML." \
      maintainer="Rico Derks r.j.e.derks@lumc.nl"
RUN dpkg --add-architecture i386
# first create user and group for all the X Window stuff
# required to do this first so we have consistent uid/gid between server and client container
RUN addgroup --system xusers \
  && adduser \
      --home /home/xclient \
      --disabled-password \
      # this is a crude solution to get it working on my computer
                        --uid 36480 \
      --shell /bin/bash \
      --gecos "user for running an xclient application" \
      --ingroup xusers \
      --quiet \
      xclient




# unfortunately we later need to wait on wineserver.
# Thus a small script for waiting is supplied.
USER root
COPY waitonprocess.sh /scripts/
RUN chmod a+rx /scripts/waitonprocess.sh

# we need wget, bzip2, wine from winehq,
# xvfb to fake X11 for winetricks during installation,
# and winbind because wine complains about missing


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

# Setup a Wine prefix
ENV WINEARCH=win64


RUN apt-get update && \
    apt-get -y install wget gnupg && \
    apt-get update && \
    apt-get -y --install-recommends install \
      bzip2 \
      xvfb \
      cabextract \
      && \
    wget https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks \
      -O /usr/local/bin/winetricks && chmod +x /usr/local/bin/winetricks

ENV WINEARCH win64

# WINE does not like running as root
USER xclient
WORKDIR /home/xclient

# wineserver needs to shut down properly!!!
ENV WINEDEBUG -all,err+all

RUN winetricks -q win7 \
  && /scripts/waitonprocess.sh wineserver

RUN xvfb-run winetricks -q vcrun2008 dotnet48 \
  && /scripts/waitonprocess.sh wineserver


  RUN mkdir /home/xclient/.wine/drive_c/pwiz

  RUN mkdir /home/xclient/.wine/drive_c/splitter

  ADD splitter /home/xclient/.wine/drive_c/splitter

  # ADD pwiz/pwiz /home/xclient/.wine/drive_c/pwiz

  # ENV WINEPATH "C:\pwiz"
  ENV WINEPATH "C:\splitter"

  # Set up working directory and permissions to let user xclient save data
  USER root
  RUN mkdir /data
  RUN chmod 777 /data
  RUN chown xclient:xusers /data
  RUN chown xclient:xusers /
  WORKDIR /data

  USER xclient

# Install nextflow (if you'd like - this insn't necessary inside the docker container?)
# USER root
# RUN apt-get install -y default-jre
# RUN apt-get install -y default-jdk
# WORKDIR /usr/local/bin
# RUN wget -qO- https://get.nextflow.io | bash
# WORKDIR /data
# USER xclient


