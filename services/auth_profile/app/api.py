import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from aiokafka import AIOKafkaProducer

from . import deps, models, schemas

router = APIRouter()


@router.post("/auth/register", status_code=201)
def register(data: schemas.RegisterRequest, db: Session = Depends(deps.get_db)) -> dict:
    if db.query(models.User).filter_by(email=data.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = models.User(email=data.email, password_hash=deps.hash_password(data.password))
    db.add(user)
    db.flush()
    db.add(models.Profile(user_id=user.id))
    db.add(models.Consents(user_id=user.id))
    db.commit()
    return {"id": user.id}


@router.post("/auth/login", response_model=schemas.TokenResponse)
def login(data: schemas.LoginRequest, db: Session = Depends(deps.get_db)) -> schemas.TokenResponse:
    user = db.query(models.User).filter_by(email=data.email).first()
    if not user or not deps.verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access, refresh = deps.create_tokens(user)
    return schemas.TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/auth/refresh", response_model=schemas.TokenResponse)
def refresh(data: schemas.RefreshRequest, db: Session = Depends(deps.get_db)) -> schemas.TokenResponse:
    payload = deps.decode_token(data.refresh_token, "refresh")
    user = db.get(models.User, payload["sub"])
    if user is None or user.token_version != payload.get("token_version"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    access, refresh_token = deps.create_tokens(user)
    return schemas.TokenResponse(access_token=access, refresh_token=refresh_token)


@router.post("/auth/logout_all")
def logout_all(user: models.User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)) -> dict:
    user.token_version += 1
    db.commit()
    return {"status": "ok"}


@router.get("/profile", response_model=schemas.ProfileResponse)
def get_profile(user: models.User = Depends(deps.get_current_user)) -> schemas.ProfileResponse:
    return schemas.ProfileResponse(
        email=user.email,
        first_name=user.profile.first_name if user.profile else None,
        last_name=user.profile.last_name if user.profile else None,
    )


async def _send_profile_updated(user: models.User) -> None:
    settings = deps.get_settings()
    if not settings.kafka_brokers:
        return
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_brokers.split(","))
    await producer.start()
    try:
        payload = json.dumps({"user_id": user.id}).encode()
        await producer.send_and_wait("user.profile.updated", payload, key=str(user.id).encode())
    finally:
        await producer.stop()


@router.patch("/profile", response_model=schemas.ProfileResponse)
async def update_profile(
    data: schemas.ProfileUpdate,
    user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> schemas.ProfileResponse:
    profile = user.profile or models.Profile(user_id=user.id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    db.add(profile)
    db.commit()
    await _send_profile_updated(user)
    return schemas.ProfileResponse(
        email=user.email,
        first_name=profile.first_name,
        last_name=profile.last_name,
    )


@router.put("/profile/consents", response_model=schemas.ConsentsResponse)
def update_consents(
    data: schemas.ConsentsUpdate,
    user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> schemas.ConsentsResponse:
    consents = user.consents or models.Consents(user_id=user.id)
    for key, value in data.model_dump().items():
        setattr(consents, key, value)
    db.add(consents)
    db.commit()
    return schemas.ConsentsResponse.model_validate(consents)
