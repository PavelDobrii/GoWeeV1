#!/usr/bin/env bash
set -euo pipefail

AUTH=http://localhost:8001
ROUTES=http://localhost:8002
PREFETCH=http://localhost:8006
TRIP=http://localhost:8007

EMAIL="user$RANDOM@example.com"
PASSWORD="pass"

# Register user and capture status
REG_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$AUTH/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

# Login and extract token
ACCESS=$(curl -s -X POST "$AUTH/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | jq -r .access_token)

echo "token: ${ACCESS:0:8}..."

# Preview route and capture option id
OPTION=$(curl -s -X POST "$ROUTES/routes/preview" -H "Content-Type: application/json" \
  -d '{"poi_ids":[1,2,3,4],"mode":"car","duration_target_min":60}' | jq -r '.options[0].option_id')

# Confirm route and capture route id
ROUTE=$(curl -s -X POST "$ROUTES/routes/confirm" -H "Content-Type: application/json" \
  -d "{\"option_id\":\"$OPTION\"}" | jq -r .route_id)

echo "route: $ROUTE"

sleep 1

# Prefetch and capture status
PREF_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  "$PREFETCH/delivery/prefetch?route_id=$ROUTE&next=1")

# Start trip and capture session id
SESSION=$(curl -s -X POST "$TRIP/trip/start" -H "Content-Type: application/json" \
  -d "{\"route_id\":$ROUTE}" | jq -r .session_id)

echo "session: $SESSION"

# Ping trip
curl -s -o /dev/null -X POST "$TRIP/trip/ping" -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION\",\"points\":[{\"lat\":55.751244,\"lon\":37.618423}]}"

# Finish trip and capture status
FIN_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$TRIP/trip/finish" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION\"}")

printf "%s\n%s\n%s\n" "$REG_CODE" "$PREF_CODE" "$FIN_CODE"

