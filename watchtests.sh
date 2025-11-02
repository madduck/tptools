#!/bin/sh
set -eu

pytest_args=-s
files=
reset=0
for arg in "$@"; do
  case "$arg//$reset" in
  --cov*//0)
    pytest_args="${pytest_args:+$pytest_args }--cov-reset $arg"
    reset=1
    ;;
  -*) pytest_args="${pytest_args:+$pytest_args }$arg" ;;
  *) files="${files:+$files }$arg" ;;
  esac
done

if [ -n "$files" ] && [ $reset -eq 0 ]; then
  pytest_args="${pytest_args:+$pytest_args }--no-cov"
fi

(sleep 0.5 && touch conftest.py) &
exec inotify-hookable -q -t 500 -w . -i '\a\..+\z' -i '__pycache__' -C ".+\.(py|toml)\$=pytest $pytest_args $files"
