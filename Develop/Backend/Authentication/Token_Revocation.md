---
title: JWT 토큰 무효화
tags: [authentication, jwt, redis, Token Revocation, security]
updated: 2026-08-02
---

# JWT 토큰 무효화

JWT의 근본적인 문제는 stateless 특성에 있다. 서버가 토큰 발급 이후의 상태를 알 수 없기 때문에, 토큰이 탈취되거나 사용자가 로그아웃해도 만료 시간이 남아 있는 한 토큰은 계속 유효하다. 이 문제를 해결하는 방법은 크게 세 가지다: 블랙리스트, jti 추적, 버전(세대) 기반 무효화.

## Redis 블랙리스트 방식

가장 단순한 접근이다. 로그아웃이나 강제 만료가 필요한 토큰을 Redis에 저장해두고, 요청마다 블랙리스트 여부를 확인한다.

```python
import redis
from datetime import datetime, timezone

r = redis.Redis(host='localhost', port=6379, db=0)

def revoke_token(jti: str, expires_at: datetime):
    ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    if ttl > 0:
        r.setex(f"blacklist:{jti}", ttl, "1")

def is_revoked(jti: str) -> bool:
    return r.exists(f"blacklist:{jti}") == 1
```

미들웨어에서 토큰 검증 시 `is_revoked(payload["jti"])`를 추가로 호출하면 된다.

주의할 점은 Redis가 단일 장애 지점(SPOF)이 된다는 것이다. Redis가 다운되면 블랙리스트 확인이 불가능해진다. 이 경우 fail-open(Redis 장애 시 통과)으로 할지 fail-close(차단)로 할지 결정이 필요하다. 보안이 중요한 서비스라면 fail-close가 맞지만, UX 측면에서는 손실이 크다. Redis Sentinel이나 Cluster 구성으로 가용성을 높이는 게 현실적인 해법이다.

블랙리스트의 크기는 동시 사용자 수와 토큰 만료 시간에 비례해서 커진다. access token 만료 시간을 짧게(15분) 유지하면 블랙리스트 항목 수를 자연스럽게 줄일 수 있다.

## jti 기반 allowlist 추적

블랙리스트의 반대 개념으로, 유효한 토큰 목록만 관리하는 방식이다. 토큰 발급 시 jti를 Redis에 저장하고, 검증 시 해당 jti가 존재하는지 확인한다.

```python
import uuid
from datetime import datetime, timedelta, timezone
import jwt

def issue_token(user_id: int, secret: str) -> str:
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
    }
    token = jwt.encode(payload, secret, algorithm="HS256")

    # Redis에 유효한 jti 저장 (15분 TTL)
    r.setex(f"token:{user_id}:{jti}", 900, "1")
    return token

def verify_token(token: str, secret: str) -> dict:
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    user_id = payload["sub"]
    jti = payload["jti"]

    if not r.exists(f"token:{user_id}:{jti}"):
        raise Exception("Token not found or revoked")

    return payload
```

특정 사용자의 모든 토큰을 무효화할 때는 `token:{user_id}:*` 패턴으로 일괄 삭제한다. 비밀번호 변경이나 계정 정지 시 이 방식이 유용하다.

```python
def revoke_all_tokens(user_id: int):
    pattern = f"token:{user_id}:*"
    keys = r.keys(pattern)
    if keys:
        r.delete(*keys)
```

단점은 모든 요청마다 Redis를 조회해야 한다는 것이다. 트래픽이 많은 서비스에서는 Redis 부하가 상당해진다. 로컬 캐시와 병행하면 부하를 줄일 수 있지만 무효화 지연이 생긴다.

## Token Version 기반 무효화

DB 조회 없이 세션 무효화를 구현하는 방법이다. 사용자 테이블에 `token_version` 컬럼을 두고, 토큰 발급 시 해당 시점의 버전을 넣는다. 검증 시 DB의 현재 버전과 비교해서 다르면 거부한다.

```sql
ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 1;
```

```python
def issue_token(user_id: int, token_version: int, secret: str) -> str:
    payload = {
        "sub": str(user_id),
        "ver": token_version,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def verify_token(token: str, secret: str, db) -> dict:
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    user_id = int(payload["sub"])

    user = db.query(User).filter(User.id == user_id).first()
    if payload["ver"] != user.token_version:
        raise Exception("Token version mismatch")

    return payload

def invalidate_all_sessions(user_id: int, db):
    db.query(User).filter(User.id == user_id).update(
        {"token_version": User.token_version + 1}
    )
    db.commit()
```

비밀번호 변경 시 `invalidate_all_sessions`를 호출하면 기존 토큰이 전부 무효화된다. Redis 의존성이 없고, 사용자 데이터 조회 시 이미 DB를 hit하는 경우라면 추가 비용이 거의 없다.

반면, 모든 요청마다 DB를 조회해야 하는 상황이라면 캐싱 레이어가 필요해진다. 사용자 정보를 Redis에 캐싱하고 token_version을 포함시키면, Redis 조회만으로 검증이 가능하다.

## Refresh Token Rotation과 Token Family

Access token 만료 시 refresh token으로 갱신하는 구조에서, 탈취된 refresh token을 감지하는 패턴이다.

핵심 원리는 단순하다. Refresh token은 1회만 사용 가능하고, 재발급 시 새 refresh token을 발급한다. 이미 사용된 refresh token으로 재발급 요청이 들어오면, 탈취가 발생했다고 판단하고 해당 token family 전체를 무효화한다.

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class RefreshToken:
    token_id: str
    family_id: str        # 최초 발급 시 생성된 family 식별자
    user_id: int
    parent_id: Optional[str]  # 이전 토큰 ID (None이면 최초 발급)
    is_used: bool
    used_at: Optional[datetime]
    expires_at: datetime

def rotate_refresh_token(old_token_id: str, db) -> tuple[str, str]:
    token = db.query(RefreshToken).filter(
        RefreshToken.token_id == old_token_id
    ).first()

    if not token:
        raise Exception("Token not found")

    if token.is_used:
        # 이미 사용된 토큰으로 재요청 = 탈취 의심
        revoke_token_family(token.family_id, db)
        raise Exception("Token reuse detected - possible theft")

    token.is_used = True
    token.used_at = datetime.now(timezone.utc)
    db.add(token)

    new_token_id = str(uuid.uuid4())
    new_refresh = RefreshToken(
        token_id=new_token_id,
        family_id=token.family_id,  # family_id 유지
        user_id=token.user_id,
        parent_id=old_token_id,
        is_used=False,
        used_at=None,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db.add(new_refresh)
    db.commit()

    new_access = issue_access_token(token.user_id, SECRET)
    return new_access, new_token_id

def revoke_token_family(family_id: str, db):
    db.query(RefreshToken).filter(
        RefreshToken.family_id == family_id
    ).update({"is_used": True})
    db.commit()
```

Token family 패턴의 약점은 race condition이다. 클라이언트가 refresh 요청을 동시에 두 번 보내면(네트워크 재시도 등), 두 번째 요청이 이미 사용된 토큰으로 들어와서 탈취로 오탐된다. 이를 방지하려면 refresh 요청에 분산 락을 걸거나, "최근 N초 이내 사용된 토큰은 grace period 허용" 방식을 적용한다.

```python
def rotate_refresh_token(old_token_id: str, db) -> tuple[str, str]:
    token = db.query(RefreshToken).filter(
        RefreshToken.token_id == old_token_id
    ).first()

    if token.is_used:
        grace_period = timedelta(seconds=10)
        if token.used_at and datetime.now(timezone.utc) - token.used_at < grace_period:
            # grace period 내 재요청이면 최근 발급된 토큰 반환
            latest = db.query(RefreshToken).filter(
                RefreshToken.family_id == token.family_id,
                RefreshToken.is_used == False
            ).order_by(RefreshToken.expires_at.desc()).first()
            if latest:
                return issue_access_token(token.user_id, SECRET), latest.token_id

        revoke_token_family(token.family_id, db)
        raise Exception("Token reuse detected")

    # ... 이하 동일
```

## Sliding Window Session

세션 유효 기간을 마지막 활동 시간 기준으로 연장하는 방식이다. "30분 동안 활동이 없으면 세션 만료" 같은 요구사항을 JWT 환경에서 구현할 때 쓴다.

JWT에 고정 만료 시간을 넣으면 sliding window를 직접 구현하기 어렵다. 별도로 Redis에 세션 활성 상태를 관리하는 게 현실적이다.

```python
def update_session_window(user_id: int, device_id: str, window_minutes: int = 30):
    key = f"session:{user_id}:{device_id}"
    r.setex(key, window_minutes * 60, "active")

def is_session_active(user_id: int, device_id: str) -> bool:
    return r.exists(f"session:{user_id}:{device_id}") == 1

# 미들웨어에서 요청마다 호출
def session_middleware(request, user_id: int, device_id: str):
    if not is_session_active(user_id, device_id):
        raise HTTPException(status_code=401, detail="Session expired")

    update_session_window(user_id, device_id)  # TTL 갱신
```

`device_id`를 포함시키는 이유가 있다. 여러 기기에서 동시 로그인을 허용하는 경우, key를 `session:{user_id}`로만 쓰면 한 기기의 활동이 다른 기기의 세션 TTL을 갱신시킨다. 각 기기의 세션을 독립적으로 관리하려면 기기 식별자를 포함해야 한다.

## 로그아웃 처리

클라이언트에서 토큰을 삭제하는 것만으로는 충분하지 않다. 서버 측에서 토큰을 명시적으로 무효화해야 한다.

```python
@router.post("/auth/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    token = extract_token_from_header(request)
    payload = decode_token(token)

    jti = payload.get("jti")
    exp = payload.get("exp")

    # access token 블랙리스트 등록
    if jti and exp:
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        revoke_token(jti, expires_at)

    # refresh token 무효화
    db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id,
        RefreshToken.is_used == False
    ).update({"is_used": True})
    db.commit()

    return {"message": "Logged out"}
```

"전체 기기 로그아웃" 기능은 token version을 올리거나, 해당 사용자의 모든 refresh token을 무효화하는 방식으로 구현한다.

## 비밀번호 변경 시 전체 세션 무효화

비밀번호 변경 후 기존 세션을 유지하는 서비스도 있지만, 보안 관점에서는 전체 무효화가 맞다. 비밀번호 변경 자체가 계정을 탈취당했을 수 있다는 신호일 수 있기 때문이다.

```python
@router.post("/auth/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid current password")

    current_user.hashed_password = hash_password(request.new_password)

    # 방법 1: token version 증가로 기존 토큰 전체 무효화
    current_user.token_version += 1

    # 방법 2: 모든 refresh token 만료 처리
    db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id
    ).update({"is_used": True})

    # sliding window session 사용 시 Redis 세션 키 삭제
    revoke_all_tokens(current_user.id)

    db.add(current_user)
    db.commit()

    # 비밀번호 변경 후 재로그인 없이 사용 가능하도록 새 토큰 발급
    new_token = issue_token(current_user.id, current_user.token_version, SECRET)
    return {"access_token": new_token}
```

## 계정 정지 즉시 적용

JWT stateless 특성상 계정 정지 처리가 까다롭다. 토큰이 유효하다면 서버는 그걸 신뢰하기 때문이다.

즉각 차단이 필요한 경우 세 가지 방법이 있다.

**매 요청마다 DB 조회**

```python
def get_current_user(token: str, db: Session) -> User:
    payload = decode_token(token)
    user = db.query(User).filter(User.id == int(payload["sub"])).first()

    if not user or user.is_suspended:
        raise HTTPException(status_code=403, detail="Account suspended")

    return user
```

성능 부담이 있지만, 계정 상태를 즉각 반영할 수 있다. Redis 캐싱을 병행하면 DB 부하를 줄일 수 있다.

**정지 계정 Redis 블랙리스트**

```python
def suspend_user(user_id: int, db):
    db.query(User).filter(User.id == user_id).update({"is_suspended": True})
    db.commit()

    # 정지 계정 Redis 등록 (TTL은 refresh token 최대 수명으로 설정)
    r.set(f"suspended:{user_id}", "1", ex=60 * 60 * 24 * 30)

def unsuspend_user(user_id: int, db):
    db.query(User).filter(User.id == user_id).update({"is_suspended": False})
    db.commit()
    r.delete(f"suspended:{user_id}")

def is_user_suspended(user_id: int) -> bool:
    return r.exists(f"suspended:{user_id}") == 1
```

매 요청마다 DB를 hit하는 것보다 빠르다. Redis 의존성이 있지만, 블랙리스트 방식과 인프라를 공유하면 된다.

**token version 활용**

`suspend_user` 시 `token_version`을 증가시킨다. 토큰 검증 단계에서 version 불일치로 자동 거부된다. 계정 정지 해제 시 새 토큰을 발급해야 하는 번거로움이 있다.

현실적으로는 첫 번째 방법(DB 조회)을 Redis 캐싱과 함께 쓰는 경우가 많다. 사용자 정보를 1분 캐싱하면 계정 정지 후 최대 1분의 지연이 생기지만, DB 부하는 크게 줄어든다. 이 지연이 허용되는지는 서비스 요구사항에 따라 다르다.

## 운영 중 자주 발생하는 문제

**토큰 블랙리스트가 지나치게 커지는 경우**: access token 만료 시간을 줄이는 것이 근본 해결책이다. 15분 이하면 블랙리스트 항목이 자동으로 만료되어 크기가 제한된다.

**Refresh token rotation에서 race condition**: 클라이언트의 retry 로직과 서버의 grace period를 조합한다. 특히 모바일 앱에서 네트워크 불안정으로 인한 재시도가 자주 발생한다.

**다중 서버 환경에서 블랙리스트 동기화**: Redis를 중앙 저장소로 쓰면 자연스럽게 해결된다. 로컬 캐시를 병행하는 경우, pub/sub로 무효화 신호를 전파해야 한다.

**jti가 없는 레거시 토큰**: 토큰 전체 문자열을 키로 사용할 수 있지만, 저장 공간이 크고 조회도 느려진다. 신규 토큰부터 jti를 추가하고, 기존 토큰은 만료될 때까지 기다리는 마이그레이션이 현실적이다.

---
이 문서는 [인증과 토큰 허브](../../_hub/인증과_토큰.md)의 일부입니다.
