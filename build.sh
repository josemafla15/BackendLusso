#!/bin/bash
set -e

pip install -r requirements.txt
playwright install --with-deps chromium"# forzar rebuild limpio 2" 
