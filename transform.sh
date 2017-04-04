#!/bin/bash

#read example name from first argument
if [ -z "$1" ]; then
  echo "** ERROR: no parameter received. Enter the name of the subdirectory on ./examples to convert"
  ls -A1l ./examples | grep ^d | awk '{print $9}'
  exit 1
fi

#change to subdirectory
cd ./examples/"$1"

container-transform -i compose -o marathon docker-compose.yml > marathon.json && \
../../container_transform/marathon_group.py -i marathon.json -n ${PWD##*/}  > group.json && \
dcos marathon group add ./group.json

cd ../..

exit 0
