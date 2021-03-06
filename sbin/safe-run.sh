#!/bin/sh

trap '' HUP

if [ -z "$1" ]; then
  echo "No params given"
  exit 10
fi
if ( kill -0 "$(cat "$1")" ) > /dev/null 2>&1; then
  (>&2 echo "Process already active")
  exit 11
fi
echo $$ > "$1"
shift
while true; do
  "$@" > /dev/null
done
