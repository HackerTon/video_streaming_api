FROM nginx:latest

WORKDIR /app

# install node
RUN apt -y update
RUN apt-get install -y curl
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash -
RUN apt-get install -y nodejs

COPY . .
RUN npm install
RUN npm run build

RUN cp -r templates/*  /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf 