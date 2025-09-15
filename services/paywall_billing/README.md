# Paywall Billing Service

Stub service providing simple paywall and in-app purchase validation.

## Endpoints

- `GET /paywall/check?action=` – returns `{show: bool}` based on daily free quota.
- `POST /iap/validate` – accepts `{platform, receipt}` and activates subscription.
- `GET /iap/status` – returns current subscription `{status, expire_at}`.
