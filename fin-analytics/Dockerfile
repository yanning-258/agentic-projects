#base python image, a minimum debian-based image with 3.11 pre-installed
#slim = stripped of extras, no compiler, docs
FROM python:3.11-slim

#install postgres inside the same container
#apt-get update: apt=advanced package tool, command line tool for installing, updating, removing software packages on Debian-based Linux systems
#since base python image is built on debian, apt/apt-get is how I should install OS-level software inside the container
#apt-get is the older, script friendly cli to APT
#apt-get update just refresh APT's local index of what packages are available at what versions, by fetching metadata from the package sources configured ont he system
#always run apt-get update -> then apt-get install
#apt-get install is interactive, the kind that ask user to say yes (y) before installing, this -y is to say yes

RUN apt-get update && apt-get install -y \
    postgresql \
    postgresql-contrib \
    && rm -rf /var/lib/apt/lists/*
#postgresql-contrib, complement to core postgresql, contains extra stuff like extra dattypes...
#then after all this, remove package index

#The docker container has a completely separate filesystem from my local devide
#we are not creating a folder in my hard drive
WORKDIR /app
#so this we are creating a directory in the separate machine, named app
#this would be the root of the project

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
#every time run docker build, docker helps to copy the whole project folder from root onwards into the docker fresh machine

EXPOSE 8000
#this is the port our app listens on inside the container

CMD ["/bin/bash", "docker/entrypoint.sh"]
#this is the default command that runes when the container starts
#CMD only fires at container startup
#here, we start with /bin/bash, then runs the docker/entrypoint.sh
