# Trip Runtime Service

Handles trip sessions, pings and approaching POI notifications.

## Running

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Endpoints

* `POST /trip/start` – start a session
* `POST /trip/ping` – send points and get upcoming POI
* `POST /trip/finish` – finish a session
