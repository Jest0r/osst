#!/usr/bin/env bash

# very simple setup script
set -x
venv_name="./venv"

# if virtual env is not there, create it
if [ ! -d $venv_name ]; then
    virtualenv $venv_name
fi
$venv_name/bin/pip install --upgrade pip
$venv_name/bin/pip install -r requirements.txt

