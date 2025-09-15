from datetime import datetime

from pydantic import BaseModel


class PaywallCheckResponse(BaseModel):
    show: bool
    reason: str | None = None
    sku: str | None = None


class IAPValidateRequest(BaseModel):
    platform: str
    receipt: str


class IAPStatusResponse(BaseModel):
    status: str
    expire_at: datetime | None = None
