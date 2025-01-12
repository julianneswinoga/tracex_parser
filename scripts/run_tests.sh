#!/bin/bash
set -e

if [ "$1" = 'clean' ]; then
  python3 -m venv --clear .venv
fi

. ./.venv/bin/activate

if [ "$1" = 'clean' ]; then
  pip3 install -U pip
  pip3 install -U poetry
  poetry update
fi

# Remove clean from args
for arg in "$@"; do
  shift
  [ "$arg" = "clean" ] && continue
  set -- "$@" "$arg"
done

poetry build
poetry install
pytest --cov-report term-missing:skip-covered --cov=tracex_parser tests/ "$@"
