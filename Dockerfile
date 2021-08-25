FROM ubuntu:20.10

WORKDIR /pythonapp

RUN apt-get -y update
RUN apt-get -y install ffmpeg intel-media-va-driver-non-free

# install python dependencies
RUN apt-get -y install python3 python3-pip
COPY ["*.py", "requirements.txt", "./"]
RUN pip3 install -r requirements.txt

# install node
RUN apt-get install -y curl
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash -
RUN apt-get install -y nodejs

# install node dependencies
COPY package*.json ./
COPY *.js ./
COPY templates/ ./templates
RUN npm install
RUN npm run build

#install nginx
RUN apt-get install -y nginx
COPY nginx.conf /etc/nginx/nginx.conf

# copy templates to nginx folder
RUN cp ./templates/* /var/www/html

# add startup.sh script
ADD startup.sh ./
RUN chmod +x startup.sh


CMD [ "./startup.sh"]