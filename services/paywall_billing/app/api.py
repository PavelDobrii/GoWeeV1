from datetime import datetime, timedelta

from fastapi import APIRouter

from . import schemas

router = APIRouter()

_FREE_PER_DAY = 1
_usage_day = ""
_usage_count = 0

_subscription: dict[str, datetime | str | None] = {
    "status": "inactive",
    "expire_at": None,
}


def _today() -> str:
    return datetime.utcnow().date().isoformat()


@router.get(
    "/paywall/check",
    response_model=schemas.PaywallCheckResponse,
    response_model_exclude_none=True,
)
def paywall_check(action: str) -> schemas.PaywallCheckResponse:
    global _usage_day, _usage_count
    today = _today()
    if _usage_day != today:
        _usage_day = today
        _usage_count = 0
    show = _usage_count >= _FREE_PER_DAY
    if not show:
        _usage_count += 1
    return schemas.PaywallCheckResponse(show=show)


@router.post(
    "/iap/validate",
    response_model=schemas.IAPStatusResponse,
    response_model_exclude_none=True,
)
def iap_validate(data: schemas.IAPValidateRequest) -> schemas.IAPStatusResponse:
    expire_at = datetime.utcnow() + timedelta(days=30)
    _subscription["status"] = "active"
    _subscription["expire_at"] = expire_at
    return schemas.IAPStatusResponse(status="active", expire_at=expire_at)


@router.get(
    "/iap/status",
    response_model=schemas.IAPStatusResponse,
    response_model_exclude_none=True,
)
def iap_status() -> schemas.IAPStatusResponse:
    status = _subscription["status"]
    expire_at = _subscription["expire_at"]
    if (
        status == "active"
        and isinstance(expire_at, datetime)
        and expire_at < datetime.utcnow()
    ):
        status = "expired"
        _subscription["status"] = status
    return schemas.IAPStatusResponse(
        status=status,
        expire_at=expire_at if isinstance(expire_at, datetime) else None,
    )
