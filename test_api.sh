#!/bin/zsh
# Usage: ./test_api.sh <path> '<json>'   (calls an n8n webhook with the demo key; prints the reply)
N=$(cat ~/.config/asif-demos/webhook_base); K=$(cat ~/.config/asif-demos/frontdesk/webhook_secret)
curl -s -m 60 -X POST "$N/$1" -H "X-Demo-Key: $K" -H 'Content-Type: application/json' -d "$2"; echo
