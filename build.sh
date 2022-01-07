#!/usr/bin/env bash

docker build --no-cache -t telegramer.build . \
    && docker run -v $(pwd)/out:/tmp/out --rm -i telegramer.build sh -s << COMMANDS
python setup.py bdist_egg
chown -R $(id -u):$(id -g) dist
cp -ar dist/ /tmp/out/
COMMANDS
