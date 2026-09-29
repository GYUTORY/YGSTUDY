---
title: JWT 구조와 검증
tags: [jwt, auth, security, backend]
updated: 2026-09-29
---

# JWT 구조와 검증

JWT(JSON Web Token)는 세 개의 Base64URL 인코딩 문자열을 점(`.`)으로 이어 붙인 것이다. `header.payload.signature` 형태다. 구조 자체는 단순하지만, 알고리즘 선택이나 검증 순서를 잘못 구현하면 서명을 완전히 우회하는 취약점이 생긴다.

## 헤더, 페이로드, 서명

헤더는 알고리즘과 토큰 타입을 담는다.

```json
{
  "alg": "RS256",
  "typ": "JWT"
}
```

`alg`는 서명에 사용할 알고리즘이고, `typ`는 거의 항상 `"JWT"`다. `kid`(Key ID)를 추가하면 키 교체 시 어떤 키로 서명했는지 식별할 수 있다.

페이로드는 클레임(claim)의 집합이다. RFC 7519에 등록된 클레임과 커스텀 클레임으로 나뉜다.

```json
{
  "iss": "https://auth.example.com",
  "sub": "user:12345",
  "aud": "api.example.com",
  "exp": 1727612400,
  "iat": 1727608800,
  "jti": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "roles": ["user", "admin"]
}
```

`iss`(발급자), `sub`(주체), `aud`(대상), `exp`(만료), `iat`(발급 시각), `jti`(토큰 ID)가 표준 등록 클레임이다. 페이로드는 서명되지만 암호화되지 않는다. Base64URL 디코딩하면 누구나 내용을 볼 수 있으므로 민감한 정보는 절대 담지 않는다.

서명은 알고리즘에 따라 다르지만, HS256 기준으로는 `HMACSHA256(base64url(header) + "." + base64url(payload), secret)`으로 만들어진다. 헤더와 페이로드의 무결성을 보장하며, 서명 검증이 실패하면 해당 토큰은 위변조된 것이다.

## JWS와 JWE

JWT는 JWS(JSON Web Signature)와 JWE(JSON Web Encryption) 두 가지 형태로 존재한다.

JWS는 서명만 한다. 페이로드가 Base64URL 인코딩되어 있어 내용은 볼 수 있지만 위변조는 불가능하다. 일반적으로 "JWT 토큰"이라고 부르는 것이 JWS다.

JWE는 페이로드를 암호화한다. `header.encrypted_key.iv.ciphertext.tag` 다섯 파트로 구성되며, 복호화하지 않으면 내용을 알 수 없다. JWE가 필요한 경우는 토큰에 개인정보나 민감 데이터를 담아야 할 때다. 실무에서는 민감 데이터를 토큰에 담지 않는 편이 더 단순한 설계고, 대부분은 JWS로 충분하다.

JWS 안에 JWE를 중첩하거나 반대로 중첩하는 Nested JWT도 스펙에 있지만, 구현 복잡도 대비 실익이 거의 없어서 쓰이는 경우는 드물다.

## 알고리즘 선택

`HS256`, `RS256`, `ES256`이 실무에서 가장 많이 쓰는 세 가지다.

**HS256 (HMAC-SHA256)**은 대칭 알고리즘이다. 하나의 비밀키로 서명하고 같은 키로 검증한다. 속도가 빠르고 구현이 단순해서, 토큰 발급과 검증을 같은 서비스가 담당하는 구조에 적합하다.

마이크로서비스 환경에서는 문제가 생긴다. 여러 서비스가 토큰을 검증해야 한다면 모든 서비스가 같은 비밀키를 가져야 하는데, 그 중 하나라도 뚫리면 비밀키가 노출된다.

**RS256 (RSA-SHA256)**은 비대칭 알고리즘이다. 개인키(private key)로 서명하고 공개키(public key)로 검증한다. 검증만 필요한 서비스는 공개키만 갖고 있으면 된다. 공개키가 노출돼도 새 토큰을 위조할 수 없다. 마이크로서비스 환경이나 서드파티에 토큰 검증을 위임할 때 RS256을 쓴다.

RSA는 최소 2048비트를 권장하며, 키 크기가 크고 서명 생성이 HS256보다 느리다.

**ES256 (ECDSA-SHA256)**은 타원 곡선 비대칭 알고리즘이다. RS256과 같은 비대칭 방식이지만 키 크기가 훨씬 작다. 256비트 키가 RSA 3072비트와 동등한 보안 강도를 제공한다. 토큰 크기를 줄이거나 성능이 중요한 환경에서 RS256 대신 쓴다.

선택 기준을 단순화하면: 단일 서비스면 HS256, 여러 서비스가 검증해야 하면 RS256 또는 ES256이다.

## alg:none 공격

2015년에 공개된 취약점으로, 지금도 잘못 구현된 라이브러리에서 간헐적으로 발견된다.

JWT 헤더의 `alg`를 `"none"`으로 바꾸면 서명 검증을 건너뛰는 라이브러리가 있었다. 공격자는 페이로드를 원하는 대로 수정한 뒤 `alg: none`으로 설정하고 서명 부분을 빈 문자열로 둔 토큰을 보낸다.

```
eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhZG1pbiJ9.
```

대부분의 최신 라이브러리는 기본적으로 거부하지만, 허용 알고리즘을 명시적으로 지정하지 않으면 여전히 취약할 수 있다.

```python
import jwt

# 취약한 코드: algorithms를 지정하지 않음
payload = jwt.decode(token, key, options={"verify_signature": False})

# 안전한 코드: 허용 알고리즘을 명시적으로 제한
payload = jwt.decode(token, public_key, algorithms=["RS256"])
```

검증 시에는 반드시 허용할 알고리즘 목록을 코드에 명시해야 한다. 헤더에서 알고리즘을 읽어 동적으로 선택하는 구현은 공격자에게 알고리즘 지정 권한을 주는 것과 같다.

## 키 혼동 취약점

alg:none보다 교묘하며, RS256과 HS256을 동시에 허용하는 환경에서 발생한다.

서버가 HS256도 함께 허용하는 경우, 공격자는 서버의 공개키를 HS256의 비밀키로 사용해 토큰을 만들 수 있다. 공개키는 `/.well-known/jwks.json` 같은 엔드포인트에 공개되거나, 정상 토큰 헤더의 `x5c` 클레임에 포함되기도 한다.

서버는 `alg` 헤더가 `HS256`인 토큰을 받으면 HS256 검증 경로로 들어가 공개키를 비밀키로 사용해 검증한다. 공격자가 서명할 때 쓴 것과 같은 키를 쓰므로 검증이 통과된다.

```python
# 키 혼동 취약점이 있는 구현
def verify_token(token, public_key):
    header = jwt.get_unverified_header(token)
    alg = header["alg"]  # 공격자가 제어 가능
    return jwt.decode(token, public_key, algorithms=[alg])

# 안전한 구현
def verify_token(token, public_key):
    # algorithms를 서버 설정에서 읽어오며, 헤더 값을 따르지 않는다
    return jwt.decode(token, public_key, algorithms=["RS256"])
```

허용 알고리즘을 서버 설정에 고정하고, 한 서비스에서 HS256과 RS256을 동시에 허용하지 않는 것이 방어의 전부다.

## 검증 구현

서명 검증만으로는 부족하다. `aud`, `iss`, `exp` 클레임 검증이 빠지면 다른 서비스에서 발급한 유효한 토큰으로 접근이 가능하다.

```python
import jwt
from jwt import PyJWKClient

JWKS_URI = "https://auth.example.com/.well-known/jwks.json"
ISSUER = "https://auth.example.com"
AUDIENCE = "api.example.com"

jwks_client = PyJWKClient(JWKS_URI)

def verify_jwt(token: str) -> dict:
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],      # 알고리즘 고정, 헤더 값 무시
        audience=AUDIENCE,          # aud 검증
        issuer=ISSUER,              # iss 검증
        options={
            "require": ["exp", "iat", "sub", "jti"],
        },
    )
    return payload
```

`PyJWKClient`는 JWKS URI에서 공개키를 가져오고 캐싱한다. `kid` 클레임으로 어떤 키를 쓸지 자동으로 찾는다.

Node.js에서는 `jose` 라이브러리가 같은 기능을 제공한다.

```typescript
import { createRemoteJWKSet, jwtVerify } from "jose";

const JWKS = createRemoteJWKSet(
  new URL("https://auth.example.com/.well-known/jwks.json")
);

async function verifyJWT(token: string) {
  const { payload } = await jwtVerify(token, JWKS, {
    issuer: "https://auth.example.com",
    audience: "api.example.com",
    algorithms: ["RS256"],
  });
  return payload;
}
```

`clockTolerance` 옵션으로 서버 간 시계 오차 허용 범위를 지정할 수 있다. NTP 동기화를 하더라도 수십 초 차이가 날 수 있으므로 `"30s"` 정도 설정해두는 편이 낫다.

## 클레임 검증에서 자주 빠지는 것

`aud` 검증이 누락되는 경우가 많다. 단일 인증 서버가 여러 서비스에 토큰을 발급할 때, 각 서비스가 자신의 `aud`만 수락하는지 확인하지 않으면 A 서비스용 토큰이 B 서비스에서도 통한다.

`jti` 클레임이 있어도 검증하지 않는 경우가 있다. 페이로드에 `jti`를 넣었지만 실제로 replay 공격 방어는 하지 않는 구현이다. 특히 일회성 토큰(이메일 인증 링크, 비밀번호 재설정 링크)에는 `jti` 소비 여부를 반드시 추적해야 한다.

```python
import time
import redis

r = redis.Redis(host="localhost", port=6379, db=0)

def verify_and_consume_jti(jti: str, exp: int) -> bool:
    ttl = exp - int(time.time())
    if ttl <= 0:
        return False
    # SET NX: 이미 있으면 None 반환 (재사용 감지)
    result = r.set(f"used_jti:{jti}", "1", ex=ttl, nx=True)
    return result is True
```

`SET NX`는 키가 없을 때만 저장하므로, 두 번째 호출부터는 `None`을 반환한다. TTL을 토큰 만료 시간과 동일하게 설정하면 만료된 토큰의 jti는 Redis에서 자동으로 제거된다.
