#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/frontend"
[ -f .env ] || cp .env.example .env
npm install
npm run dev
