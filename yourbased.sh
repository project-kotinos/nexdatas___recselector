#!/usr/bin/env bash
set -ex
brew install docker
chmod +x .travis/run.sh
chmod +x .travis/install.sh
docker rm --force ndts || true
docker build -t ndts .travis/debian9_py2
pwd
docker run  --name  ndts -d -it -v `pwd`:/home/tango  ndts
.travis/install.sh debain9 2
.travis/run.sh basic 2
docker stop ndts
docker rm ndts

