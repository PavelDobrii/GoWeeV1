#!/usr/bin/env bash
set -uo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required for scripts/smoke.sh" >&2
  exit 1
fi

AUTH=http://localhost:8001
ROUTES=http://localhost:8002
PREFETCH=http://localhost:8006
TRIP=http://localhost:8007

EMAIL="user$RANDOM@example.com"
PASSWORD="pass"

# Register user
curl -s -o /dev/null -X POST "$AUTH/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}"

# Login and extract token plus status code
TMP_LOGIN=$(mktemp)
LOGIN_CODE=$(curl -s -o "$TMP_LOGIN" -w "%{http_code}" -X POST "$AUTH/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
ACCESS=$(jq -r .access_token "$TMP_LOGIN")
rm -f "$TMP_LOGIN"

if [[ -z "$ACCESS" || "$ACCESS" == "null" ]]; then
  echo "failed to obtain access token" >&2
  exit 1
fi

echo "token: ${ACCESS:0:8}..."

# Preview route and capture option id
OPTION=$(curl -s -X POST "$ROUTES/routes/preview" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{"poi_ids":[1,2,3,4],"mode":"car","duration_target_min":60}' | jq -r '.options[0].option_id')

# Confirm route and capture route id
ROUTE=$(curl -s -X POST "$ROUTES/routes/confirm" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d "{\"option_id\":\"$OPTION\"}" | jq -r .route_id)

echo "route: $ROUTE"

sleep 1

# Prefetch and capture status
PREF_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ACCESS" \
  "$PREFETCH/delivery/prefetch?route_id=$ROUTE&next=1")

# Start trip and capture session id
SESSION=$(curl -s -X POST "$TRIP/trip/start" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d "{\"route_id\":$ROUTE}" | jq -r .session_id)

echo "session: $SESSION"

# Ping trip
curl -s -o /dev/null -X POST "$TRIP/trip/ping" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d "{\"session_id\":\"$SESSION\",\"points\":[{\"lat\":55.751244,\"lon\":37.618423}]}"

# Finish trip and capture status
FIN_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$TRIP/trip/finish" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d "{\"session_id\":\"$SESSION\"}")

if [[ "$LOGIN_CODE" != "200" ]]; then
  echo "login failed with status $LOGIN_CODE" >&2
  exit 1
fi

if [[ "$PREF_CODE" != "200" ]]; then
  echo "prefetch failed with status $PREF_CODE" >&2
  exit 1
fi

if [[ "$FIN_CODE" != "200" ]]; then
  echo "finish failed with status $FIN_CODE" >&2
  exit 1
fi

printf "%s\n%s\n%s\n" "$LOGIN_CODE" "$PREF_CODE" "$FIN_CODE"

