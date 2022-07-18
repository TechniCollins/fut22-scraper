FROM python:3.9.5-slim-buster

ENV HOME /root
ENV APP_HOME /application/
ENV C_FORCE_ROOT=true
ENV PYTHONUNBUFFERED 1

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential

RUN mkdir -p $APP_HOME
WORKDIR $APP_HOME

# upgrade pip
RUN pip3 install --upgrade pip

# Install pip packages
ADD ./requirements.txt .
RUN pip install -r requirements.txt
RUN rm requirements.txt

# Install Chrome browser and its dependencies

RUN apt-get install -y \
    libcurl3-gnutls \
    libcurl3-nss \
    libcurl4 \
    libgbm1

RUN apt-get install -y \
    gconf-service \
    libasound2 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libfontconfig1 \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0  \
    libnspr4 \
    libpango-1.0-0 \
    libxss1 \
    fonts-liberation \
    libappindicator1 \
    libnss3 \
    lsb-release \
    xdg-utils \
    xvfb

RUN apt-get -y install wget

RUN wget -q --show-progress https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN dpkg -i google-chrome-stable_current_amd64.deb; apt-get -fy install

# Copy code into Image
ADD ./futscraper/ $APP_HOME

# collect static files
# RUN $APP_HOME/manage.py collectstatic

# Create a user - Running chrome as root is a nightmare
RUN useradd -ms /bin/bash futadmin
RUN chown futadmin $APP_HOME
RUN chown futadmin $HOME
USER futadmin

# More configs for google chrome
RUN Xvfb -ac :99 -screen 0 1280x1024x16 -nolisten unix &
RUN export DISPLAY=:99
