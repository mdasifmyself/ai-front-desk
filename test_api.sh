#!/bin/zsh
# Usage: ./test_api.sh <path> '<json>'   (calls an n8n webhook with the demo key; prints the reply)
N=$(cat ~/.config/renata-assessment/n8n_url); K=$(cat ~/.config/crm-voice-demo/webhook_secret)
curl -s -m 60 -X POST "$N/webhook/$1" -H "X-Demo-Key: $K" -H 'Content-Type: application/json' -d "$2"; echo
