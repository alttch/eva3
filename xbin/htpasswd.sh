#!/bin/bash

case $2 in
  create|set_password)
    touch $1
    htpasswd -i $1 $3 || exit 1
    exit $?
    ;;
  destroy)
    htpasswd -D $1 $3
    exit $?
    ;;
esac
