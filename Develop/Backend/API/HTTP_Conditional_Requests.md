---
title: HTTP 조건부 요청 심화
tags: [HTTP, ETag, Conditional-Requests, Optimistic-Locking, Cache, REST]
updated: 2026-07-26
---

# HTTP 조건부 요청 심화

조건부 요청(Conditional Request)은 HTTP 헤더로 서버에 조건을 걸어 요청 처리 여부를 결정하는 메커니즘이다. 단순히 캐시에 쓰이는 기능이라고 생각하는 경우가 많은데, 실제로는 동시 수정 충돌을 막는 낙관적 잠금(Optimistic Locking)의 핵심 도구다.

---

## 조건부 헤더 종류

| 헤더 | 용도 | 대응 상태코드 |
|---|---|---|
| `If-None-Match` | 캐시 신선도 확인 (GET) | 304 Not Modified |
| `If-Match` | 쓰기 전 버전 확인 (PUT/PATCH) | 412 Precondition Failed |
| `If-Modified-Since` | 날짜 기반 캐시 확인 (GET) | 304 Not Modified |
| `If-Unmodified-Since` | 날짜 기반 쓰기 전 확인 (PUT/PATCH) | 412 Precondition Failed |

---

## GET 캐싱과 쓰기 동시성 제어는 다른 문제다

가장 많이 혼동하는 부분이다. 겉보기에 둘 다 ETag를 쓰지만, 목적과 헤더가 다르다.

**GET 캐싱 흐름 — `If-None-Match`**

```
GET /articles/42
If-None-Match: "abc123"
```

서버는 현재 리소스의 ETag가 `"abc123"`이면 본문 없이 `304 Not Modified`를 반환한다. 클라이언트는 로컬 캐시를 그대로 쓴다. 네트워크 트래픽을 줄이는 게 목적이다.

**쓰기 동시성 제어 흐름 — `If-Match`**

```
GET /articles/42
→ 200 OK, ETag: "abc123"

PUT /articles/42
If-Match: "abc123"
Content-Type: application/json

{ "title": "수정된 제목" }
```

서버는 현재 ETag가 `"abc123"`인지 확인한 뒤 일치하면 수정을 진행한다. 다른 클라이언트가 먼저 수정해서 ETag가 `"xyz789"`로 바뀌었다면 `412 Precondition Failed`를 반환한다. 클라이언트는 이 응답을 받고 최신 데이터를 다시 읽어서 충돌을 처리해야 한다.

---

## If-Match를 이용한 낙관적 잠금

DB 레벨 잠금 없이 동시 수정을 막는 방식이다. 실제 트래픽이 많은 API에서 비관적 잠금(SELECT FOR UPDATE)을 쓰면 커넥션을 오래 붙잡는 문제가 생긴다. 조건부 요청으로 낙관적 잠금을 구현하면 이 부담을 피할 수 있다.

```
sequenceDiagram
    participant Alice
    participant Bob
    participant Server

    Alice->>Server: GET /articles/42
    Server-->>Alice: 200 OK, ETag: "v1"

    Bob->>Server: GET /articles/42
    Server-->>Bob: 200 OK, ETag: "v1"

    Alice->>Server: PUT /articles/42, If-Match: "v1"
    Server-->>Alice: 200 OK, ETag: "v2"

    Bob->>Server: PUT /articles/42, If-Match: "v1"
    Server-->>Bob: 412 Precondition Failed
```

Bob은 412를 받은 후 최신 버전(`v2`)을 다시 GET해서 Alice의 변경 내용과 자신의 변경 내용을 합쳐야 한다. 이 병합 로직은 서버가 아닌 클라이언트 책임이다.

서버 구현에서 중요한 점은 ETag 비교를 실제 DB에서 하는 게 아니라 메모리나 캐시에서 할 수 있도록 설계하는 것이다. DB를 매번 조회하면 낙관적 잠금의 이점이 줄어든다.

```python
# Django/DRF 예시
class ArticleView(APIView):
    def put(self, request, pk):
        article = get_object_or_404(Article, pk=pk)
        current_etag = self._compute_etag(article)

        client_etag = request.META.get('HTTP_IF_MATCH', '')
        # 따옴표 제거: "abc123" → abc123
        client_etag = client_etag.strip('"')

        if client_etag and client_etag != current_etag:
            return Response(
                {"detail": "Resource has been modified by another request."},
                status=412
            )

        serializer = ArticleSerializer(article, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response = Response(serializer.data)
        response['ETag'] = f'"{self._compute_etag(serializer.instance)}"'
        return response

    def _compute_etag(self, article):
        import hashlib
        content = f"{article.id}:{article.updated_at.isoformat()}:{article.version}"
        return hashlib.md5(content.encode()).hexdigest()
```

---

## ETag 생성 전략

ETag는 리소스의 특정 버전을 식별하는 값이다. 어떻게 만드느냐에 따라 트레이드오프가 달라진다.

### 해시 기반

리소스 본문 전체를 해시로 만드는 방식이다.

```python
import hashlib
import json

def generate_etag(resource: dict) -> str:
    content = json.dumps(resource, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(content.encode()).hexdigest()[:16]
```

직렬화한 내용이 달라지면 ETag도 달라진다. 실제로 변경된 경우에만 ETag가 바뀐다는 게 장점이다. 단점은 ETag를 만들려면 전체 리소스를 읽어야 한다는 것이다. 리소스가 크면 매번 해시 계산 비용이 든다.

### 버전 기반

DB에 버전 컬럼(`version`, `updated_at`)을 두고 이걸 ETag로 쓰는 방식이다.

```python
def generate_etag(article) -> str:
    # version은 UPDATE마다 1씩 증가하는 컬럼
    return f"{article.id}-{article.version}"

# 또는 updated_at 타임스탬프
def generate_etag_from_timestamp(article) -> str:
    ts = int(article.updated_at.timestamp() * 1000)  # milliseconds
    return f"{article.id}-{ts}"
```

본문을 읽지 않아도 ETag를 만들 수 있다. `SELECT id, version FROM articles WHERE id = ?` 한 번으로 충분하다. 반면 실제 내용이 달라지지 않아도 업데이트가 발생하면 ETag가 바뀐다.

### 실무 선택

DB에 `version` 컬럼을 이미 갖고 있다면 버전 기반이 훨씬 낫다. 해시 기반은 버전 관리를 안 하는 레거시 시스템이나 파일 서버처럼 내용 자체가 진실(source of truth)인 경우에 적합하다.

---

## 동시 수정 충돌 해결 패턴

412를 받은 클라이언트가 취할 수 있는 방법은 세 가지다.

**단순 재시도 거부**

API 응답에서 충돌 사실만 알리고, 사용자가 직접 최신 데이터를 다시 불러와서 편집하게 한다. 구현이 가장 단순하고 데이터 손실 위험이 없다. 동시 편집이 드문 어드민 도구 같은 곳에 적합하다.

```json
HTTP/1.1 412 Precondition Failed
Content-Type: application/problem+json

{
  "type": "/errors/conflict",
  "title": "Precondition Failed",
  "detail": "The resource was modified after you last fetched it. Please reload and try again.",
  "current_etag": "xyz789"
}
```

응답에 `current_etag`를 넣어주면 클라이언트가 불필요한 추가 GET 없이 최신 ETag를 알 수 있다.

**서버 사이드 3-way merge**

클라이언트가 원본(base), 자신의 수정본(mine), 현재 서버 상태(theirs)를 보내면 서버가 병합을 시도한다. 실제로 구현한 팀을 거의 못 봤다. 텍스트 diff/merge 라이브러리를 연동해야 하고, 충돌이 나는 필드 처리 정책을 별도로 정해야 한다.

**필드 단위 PATCH**

PUT 대신 변경된 필드만 PATCH로 보내는 방식이다. 서로 다른 필드를 수정한 경우라면 충돌 없이 둘 다 반영할 수 있다.

```http
PATCH /articles/42
If-Match: "abc123"
Content-Type: application/merge-patch+json

{
  "title": "새 제목"
}
```

같은 필드를 수정한 경우에는 여전히 412가 발생한다. Last Write Wins 정책이 필요한 경우엔 If-Match 없이 그냥 PATCH를 날리는 팀도 있는데, 그러면 동시 수정 제어 자체를 포기하는 것이다.

---

## Last-Modified vs ETag 선택 기준

둘 다 조건부 요청에 쓸 수 있지만 동작 방식이 다르다.

**Last-Modified의 문제**

```http
Last-Modified: Sat, 26 Jul 2026 10:30:00 GMT
```

시간 해상도가 1초다. 1초 안에 두 번 수정이 발생하면 두 번째 수정을 감지하지 못한다. 분산 환경에서 서버 간 시계 동기화가 맞지 않으면 오작동한다. 쓰기 동시성 제어에 쓰기에는 신뢰성이 부족하다.

**ETag가 필요한 경우**

- 1초 이내 다중 수정이 발생할 수 있는 리소스
- 분산 서버 환경
- 쓰기 동시성 제어 (If-Match)
- 동일한 타임스탬프라도 다른 내용을 가질 수 있는 경우

**Last-Modified로 충분한 경우**

- 수정 빈도가 낮고 1초 해상도로 충분한 정적 콘텐츠
- ETag 계산 비용이 부담스러운 대용량 파일 서버
- 기존 시스템에 Last-Modified가 이미 있어서 ETag를 추가하기 어려운 경우

실제로는 ETag와 Last-Modified를 함께 내려보내는 경우가 많다. 클라이언트 호환성 때문이다. 서버는 둘 다 제공하고, 클라이언트가 더 정확한 ETag를 우선 사용하게 된다.

```http
HTTP/1.1 200 OK
ETag: "abc123"
Last-Modified: Sat, 26 Jul 2026 10:30:00 GMT
Cache-Control: max-age=0, must-revalidate
```

---

## 응답 헤더 설계 시 주의사항

ETag 값은 반드시 따옴표로 감싸야 한다. `abc123`이 아니라 `"abc123"`이다. RFC 7232 스펙이다. 파싱을 직접 하는 경우에 이걸 빠뜨리고 나중에 `If-Match` 비교가 계속 실패하는 상황이 생긴다.

Weak ETag(`W/"abc123"`)는 의미적으로 동일한 리소스에 쓴다. 예를 들어 gzip 압축 여부만 다른 경우처럼 표현 방식이 달라도 내용이 같다면 weak ETag를 쓴다. 쓰기 동시성 제어에는 strong ETag만 써야 한다. `If-Match`는 weak ETag를 허용하지 않는다.

```http
# Strong ETag
ETag: "abc123"

# Weak ETag — If-Match에 쓰면 안 됨
ETag: W/"abc123"
```

PATCH 응답에서도 ETag를 새로 내려줘야 한다. 수정이 성공했는데 ETag를 응답에 빠뜨리면 클라이언트가 다음 수정 때 오래된 ETag로 If-Match를 보내서 불필요한 412가 발생한다.
