#!/usr/bin/env bash
set -ex
brew install docker
chmod +x .travis/run.sh
chmod +x .travis/install.sh
docker rm --force ndts || true
docker build -t ndts .travis/${OS}_py${PY}
pwd
ls
docker run  --name  ndts -d -it -v `pwd`:/home/tango  ndts
docker exec --user root ndts /bin/sh -c 'pwd; ls'
.travis/install.sh ${OS} ${PY}
.travis/run.sh ${TEST} ${PY}
docker stop ndts
docker rm ndts

