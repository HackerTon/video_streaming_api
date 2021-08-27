FROM ubuntu:20.10

WORKDIR /pythonapp

RUN apt-get -y update
RUN apt-get -y install ffmpeg intel-media-va-driver-non-free

# install python dependencies
RUN apt-get -y install python3 python3-pip
COPY ["*.py", "requirements.txt", "./"]
RUN pip3 install -r requirements.txt

CMD [ "python3", "server.py" ]