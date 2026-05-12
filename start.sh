#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "Starting Catchphrase at http://localhost:7823"
python3 -m uvicorn main:app --port 7823 --reload
