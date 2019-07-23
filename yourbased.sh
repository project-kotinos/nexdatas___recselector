#!/usr/bin/env bash
set -e

echo "inside script"
chmod +x .travis/run.sh
chmod +x .travis/install.sh
docker build -t ndts .travis/debian9_py2
docker run  --name  ndts -d -it -v `pwd`:/home/tango  ndts
.travis/install.sh debain9 2
.travis/run.sh basic 2
docker stop ndts
docker rm ndts

