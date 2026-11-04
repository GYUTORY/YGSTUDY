---
title: CouchDB 데이터 모델과 복제
tags: [database, nosql, architecture]
updated: 2026-11-04
---

# CouchDB

## 정의와 철학

CouchDB는 Apache 재단이 관리하는 문서 지향 NoSQL 데이터베이스다. JSON 문서를 HTTP/REST API로 읽고 쓰는 구조라서, 드라이버 없이 `curl`만으로 모든 기능을 쓸 수 있다. MongoDB가 바이너리 프로토콜(MongoDB Wire Protocol)과 BSON 위에서 동작하는 반면, CouchDB는 처음부터 웹과 같은 방식을 지향해서 모든 요청이 HTTP 메서드(GET/PUT/POST/DELETE)로 매핑된다.

실무에서 CouchDB를 고르는 이유는 대부분 성능이 아니라 복제(replication)와 오프라인 동기화다. 모바일 클라이언트가 간헐적으로 연결되는 환경, 지점별 로컬 DB가 본사와 양방향으로 동기화되어야 하는 환경에서 쓸모가 나온다. 쓰기 처리량이나 쿼리 표현력은 MongoDB에 못 미친다.

이 문서의 응답과 상태코드는 `apache/couchdb:3.3.3` 컨테이너 3대로 클러스터를 만들어 `curl`로 직접 확인한 값이다. 해시는 앞부분만 줄여 적었다.

## MongoDB와의 핵심 차이

"MongoDB는 문서 락, CouchDB는 MVCC"라는 대비는 맞지 않는다. WiredTiger도 MVCC를 쓴다. 실제 차이는 리비전을 누가 들고 있느냐다. MongoDB는 MVCC를 엔진 안에 숨기고 클라이언트는 리비전을 모른다. CouchDB는 리비전(`_rev`)을 클라이언트에 그대로 노출하고, 수정할 때 "내가 본 버전이 이거다"를 `_rev`로 보내게 한다. 서버의 현재 리비전과 다르거나 `_rev`가 없으면 409 Conflict를 돌려주는 낙관적 동시성이다.

```bash
# 문서 생성
curl -X PUT http://admin:password@localhost:5984/orders/ord-1001 \
     -H "Content-Type: application/json" \
     -d '{"customer":"kim","total":45000,"status":"pending"}'
# {"ok":true,"id":"ord-1001","rev":"1-a8f3c4..."}   201

# 수정 시 현재 rev를 함께 보낸다
curl -X PUT http://admin:password@localhost:5984/orders/ord-1001 \
     -H "Content-Type: application/json" \
     -d '{"_rev":"1-a8f3c4...","customer":"kim","total":45000,"status":"paid"}'
```

이미 있는 문서를 `_rev` 없이 PUT 하거나 틀린 `_rev`를 보내면 같은 응답이 나온다.

```bash
curl -X PUT http://admin:password@localhost:5984/src/d1 -d '{"v":2}'
# {"error":"conflict","reason":"Document update conflict."}   409

curl -X PUT http://admin:password@localhost:5984/src/d1 -d '{"_rev":"1-zzz","v":2}'
# {"error":"conflict","reason":"Document update conflict."}   409
```

문서가 없을 때는 `_rev` 없이 PUT 하면 201로 만들어진다. `$set` 같은 블라인드 업데이트는 없고, 읽고 고쳐서 같은 `_rev`로 되돌려 쓰는 사이클이 기본이다. 처음에는 불편하지만 이 제약이 있어서 같은 리비전에서 갈라진 쓰기를 서버가 구분하고, 복제 때도 그 구분이 그대로 쓰인다.

| 항목 | MongoDB | CouchDB |
|---|---|---|
| 동시성 모델 | WiredTiger MVCC, 문서 단위 쓰기 충돌은 서버가 처리 | MVCC, 리비전을 클라이언트에 노출 |
| 같은 문서 동시 수정 | 엔진이 직렬화하고 마지막 쓰기가 값을 덮는다 | 늦은 쪽이 409. 복제로 만난 경우 리프가 둘이 되어 `_conflicts`로 남는다 |
| 트랜잭션 | 다중 문서 트랜잭션 지원 | 없음. `_bulk_docs`는 부분 성공 가능 |
| 모델링 단위 | 컬렉션 | DB 하나에 문서가 섞인다 (`type` 필드 또는 파티션) |
| 복제 단위 | replica set이 인스턴스 전체를 oplog로 따라간다 | DB 하나가 복제 작업 하나. 필터로 일부만 보낼 수도 있다 |
| 프로토콜 | 바이너리 + BSON | HTTP + JSON |

트랜잭션은 위 표 그대로다. CouchDB는 다중 문서 트랜잭션이 없다. `_bulk_docs`로 여러 문서를 한 번에 보낼 수는 있지만 일부 성공, 일부 실패가 가능한 일괄 처리다. 금융 거래처럼 원자성이 필요한 업무는 맞지 않는다.

## 문서 모델과 JSON 저장 구조

CouchDB의 문서는 JSON이다. 스키마가 없고 `_id`와 `_rev` 같은 밑줄 필드만 예약돼 있다. 중첩 구조도 배열도 자유롭다.

```json
{
  "_id": "user-2048",
  "_rev": "3-f2a1b8c9...",
  "type": "user",
  "profile": {
    "name": "박지훈",
    "email": "park@example.com",
    "addresses": [
      {"type": "home", "zip": "06123"},
      {"type": "office", "zip": "04520"}
    ]
  },
  "created_at": "2026-04-17T09:30:00Z"
}
```

### type 필드와 파티션 DB

한 DB에 여러 종류의 문서가 섞여 들어간다. 컬렉션이 없으니 보통 `type` 필드로 구분하고 뷰나 Mango 쿼리에서 거른다. 복제 단위가 DB라서 사용자 관련 데이터를 한 DB에 모아 두면 한 번에 복제되는 장점이 있다.

문제는 `type` 으로 거르는 쿼리가 샤드 전체를 훑는다는 점이다. 3.x에는 파티션 DB가 있다. DB를 `partitioned=true` 로 만들면 문서 `_id` 가 `파티션키:문서키` 형태여야 하고, 같은 파티션키를 가진 문서는 같은 샤드 레인지에 모인다.

```bash
curl -X PUT "http://admin:password@localhost:5984/pt?partitioned=true&q=8&n=3"
# {"ok":true}   201

# 파티션 키가 없는 _id는 거절된다
curl -X PUT http://admin:password@localhost:5984/pt/plain-id -d '{"a":1}'
# {"error":"illegal_docid","reason":"Doc id must be of form partition:id"}   400

# 파티션 단위 조회
curl http://admin:password@localhost:5984/pt/_partition/acme
# {"db_name":"pt","sizes":{"active":276,"external":105},"partition":"acme","doc_count":3,"doc_del_count":0}

curl http://admin:password@localhost:5984/pt/_partition/acme/_all_docs
curl -X POST http://admin:password@localhost:5984/pt/_partition/acme/_find \
     -H "Content-Type: application/json" \
     -d '{"selector":{"type":"order"},"fields":["_id","status"],"limit":2}'
```

`acme:x1`, `acme:x2`, `acme:x3` 의 샤드를 `_shards/<id>` 로 찍어 보면 모두 `00000000-1fffffff` 였고 `globex:x1` 만 `80000000-9fffffff` 였다. 파티션 안의 쿼리는 이 샤드 하나만 읽는다.

| 방식 | 키 | 쿼리 범위 | 맞는 경우 |
|---|---|---|---|
| `type` 필드로 섞기 | 자유 | DB 전체 샤드 | 파티션으로 나눌 기준이 없을 때, 전역 집계가 많을 때 |
| 파티션 DB | `tenant:doc` 형태 필수 | 한 파티션의 샤드 하나 | 테넌트·사용자별 조회가 대부분일 때 |

키 설계 규칙은 하나다. 자주 같이 조회하는 단위를 파티션키로 잡는다. `tenant:doc` 에서 `tenant` 가 사실상 모든 문서에 같은 값이면 한 샤드에 몰리고, 문서마다 다르면 파티션의 이점이 없다. 파티션 DB는 만들 때만 정할 수 있어서, 나중에 켜려면 새 DB를 만들어 복제해야 한다.

### 주문과 주문 항목 모델링

충돌 빈도는 모델링에서 갈린다. 주문 한 건에 항목 20개가 있고, 창고 단말 두 대가 오프라인에서 서로 다른 항목을 `shipped` 로 바꾸는 상황을 양방향 복제로 돌려 봤다.

```mermaid
flowchart LR
    subgraph embedCase["임베드: order-1 한 문서에 items 20개"]
        e0["공통 2-rev"] --> e1["노드 A: items 3번 수정"]
        e0 --> e2["노드 B: items 17번 수정"]
        e1 --> e3["복제 후 리프 2개<br/>winner에는 한쪽 수정만 보인다"]
        e2 --> e3
    end
    subgraph splitCase["분리: order-1:item:03, order-1:item:17"]
        s1["노드 A: item 03 수정"] --> s3["서로 다른 문서<br/>복제 후 두 수정 모두 반영"]
        s2["노드 B: item 17 수정"] --> s3
    end
```

왼쪽은 임베드, 오른쪽은 분리다. 임베드는 항목이 달라도 같은 문서의 같은 리비전에서 갈라지므로 충돌이다. 실행 결과는 이랬다.

```text
임베드: _conflicts = ["2-1f0ca2b0..."], winner에서 shipped 인 항목은 SKU-17 하나뿐
분리:   shipped 문서 = order-1:item:03, order-1:item:17 (양쪽 DB 모두), 충돌 문서 수 0
```

임베드에서 SKU-3 수정이 사라진 건 아니다. 패배한 리프에 남아 있어서 앱이 병합해야 한다. 분리하면 병합 코드가 필요 없는 대신 읽기가 늘어난다. 항목은 ID 접두사 범위로 한 번에 읽는다.

```bash
curl -G http://admin:password@localhost:5984/orders/_all_docs \
     --data-urlencode 'startkey="order-1:"' \
     --data-urlencode 'endkey="order-1:\ufff0"' \
     --data-urlencode 'include_docs=true'
```

항목 20개를 이렇게 읽으면 `rows` 가 20개 나왔다. 같이 수정될 일이 없고 항상 함께 읽히는 값(배송지 주소 같은)은 임베드, 서로 다른 사람이 따로 고치는 값(항목별 상태)은 분리가 기준이다.

### 첨부 파일

`_attachments` 는 문서에 붙는 바이너리다. 300,000바이트 파일을 `PUT /db/doc/파일명?rev=` 로 붙이고 문서를 읽으면 본문 대신 스텁이 나온다.

```bash
curl http://admin:password@localhost:5984/att/a1
# {"_id":"a1","_rev":"2-cf14b322...","t":"photo","_attachments":{"photo.bin":
#  {"content_type":"application/octet-stream","revpos":2,"digest":"md5-74v6I1LZ...",
#   "length":300000,"stub":true}}}                       # 응답 221바이트
```

같은 문서를 `attachments=true` 로 받을 때 크기는 `Accept` 헤더에 따라 달라진다.

| 요청 | 응답 크기 |
|---|---|
| `GET /att/a1` (스텁) | 221바이트 |
| `GET /att/a1/photo.bin` | 300,000바이트 |
| `GET /att/a1?attachments=true` (기본 Accept) | 300,490바이트, multipart/related |
| 같은 요청에 `Accept: application/json` | 400,209바이트, `data` 필드가 base64 400,000자 |

저장 비용은 문서를 고치는 방식에서 갈렸다. 스텁을 그대로 둔 채 본문 필드만 바꿔 3번 갱신했을 때 shard 파일은 315,592에서 327,880바이트로 12KB 늘었다. 같은 파일을 인라인 base64로 3번 다시 실어 PUT 하면 요청 본문이 매번 400,157바이트였고 파일은 327,880에서 1,237,192바이트로 약 909KB 늘었다. 내용이 같아도 첨부가 새로 쓰였고 `revpos` 가 2에서 8로 올라갔다.

복제 경로도 다르다. 첨부가 있는 문서는 복제기가 `_bulk_docs` 로 모아 쓰지 않고 문서마다 `GET /att/a1?revs=true&open_revs=[...]` 로 받아 `PUT /att2/a1?new_edits=false` 로 쓴다(복제 로그에서 확인). 첨부 문서가 많으면 배치 이점이 없어진다. 문서를 고칠 때는 `GET` 으로 받은 스텁 그대로 `PUT` 하고, 인라인 base64는 새 파일을 올릴 때만 쓴다. 이미지처럼 큰 파일은 오브젝트 스토리지에 두고 URL만 문서에 넣는 쪽이 복제 부담이 적다.

## 리비전 트리와 스템

문서 하나는 리비전의 트리다. `_rev` 가 가리키는 건 GET 이 돌려주는 리프(winner)일 뿐이고, 복제로 갈라진 다른 리프는 `_conflicts` 에 남는다. 한 DB에 `_revs_limit` (기본 1000)을 넘는 오래된 리비전은 루트 쪽부터 잘리고, compaction 이 지나가면 리프가 아닌 리비전의 본문은 `missing` 이 된다. 같은 본문이면 `_id` 가 달라도 첫 리비전 해시가 같다는 것, 삭제 후 재생성하면 번호가 이어진다는 것까지 실제 응답과 함께 [CouchDB 리비전 트리](CouchDB_Revision_Tree.md)에 정리했다.

## B-tree 기반 Append-only 스토리지

CouchDB의 스토리지 엔진은 B+tree지만 append-only 방식이다. 쓰기마다 변경된 리프, 인너 노드, 루트가 파일 끝에 순서대로 붙고 마지막에 새 루트를 가리키는 헤더가 붙는다. 기존 페이지는 덮어쓰지 않는다. 크래시가 나도 앞쪽 데이터는 깨지지 않고, 마지막으로 `fsync` 된 헤더까지가 유효한 상태가 된다.

```mermaid
flowchart LR
    subgraph w["쓰기 1회에 파일 끝에 붙는 순서"]
        direction LR
        a1["리프"] --> a2["인너 노드"] --> a3["루트"] --> a4["헤더<br/>새 루트 위치, fsync"]
    end
    subgraph before["compaction 전"]
        direction LR
        b1["쓰기 1<br/>노드와 헤더"] --> b2["쓰기 2<br/>노드와 헤더"] --> b3["...쓰기 51<br/>노드와 헤더 (현재)"]
    end
    subgraph after["compaction 후"]
        direction LR
        c1["현재 리프, 인너, 루트, 헤더만<br/>새 파일로 재작성"]
    end
    w --> before
    before -->|"POST /db/_compact"| after
```

위는 쓰기 한 번의 순서, 가운데는 옛 노드가 남은 파일, 오른쪽은 compaction 이 현재 리비전만 새 파일로 옮긴 결과다. `q=1, n=1` 인 DB에서 문서 하나를 51번 수정하고 `GET /db` 의 `sizes` 를 봤다.

| 시점 | `sizes.file` | `sizes.active` |
|---|---|---|
| 51번 수정 후 | 217,282 | 2,964 |
| compaction 후 | 16,581 | 2,233 |

3KB 안 되는 데이터가 217KB 파일이 됐다. 첨부가 있는 DB는 차이가 더 크다. 위 인라인 갱신 실험의 DB는 1,237,192바이트에서 compaction 후 315,595바이트가 됐다.

```bash
# 특정 DB compaction
curl -X POST http://admin:password@localhost:5984/orders/_compact \
     -H "Content-Type: application/json"
# {"ok":true}   202

# 뷰 인덱스 compaction
curl -X POST http://admin:password@localhost:5984/orders/_compact/design_doc_name \
     -H "Content-Type: application/json"
```

운영 중에도 돌아가지만 I/O를 많이 먹는다. DB가 100GB를 넘으면 compaction 자체가 몇 시간 걸리고, 그동안 원본과 작업본 두 벌이 디스크에 있어서 순간적으로 2배 공간이 필요하다. 5년 전에 운영 중인 50GB DB를 compaction 돌렸다가 디스크가 가득 찬 적이 있다. 그 뒤로는 여유 공간을 DB 크기의 2배 이상 확보한다.

`auto_compaction` 을 켜면 조각화 비율을 보고 알아서 돌지만, 큰 DB는 새벽 시간대에 수동으로 돌리는 편이 예측 가능하다.

## 뷰(Map/Reduce)와 Mango 쿼리

CouchDB의 원래 쿼리 방식은 JavaScript로 작성하는 Map/Reduce 뷰다. Design document 안에 뷰를 정의하면 CouchDB가 그 결과를 인덱스로 영구 저장한다.

```javascript
// _design/orders 문서
{
  "_id": "_design/orders",
  "views": {
    "by_status": {
      "map": "function(doc) { if (doc.type === 'order') { emit(doc.status, doc.total); } }",
      "reduce": "_sum"
    }
  }
}
```

뷰를 처음 조회하면 CouchDB가 전체 DB를 스캔해서 인덱스를 만든다. 1000만 건짜리 DB에 새 뷰를 추가하면 첫 요청이 몇십 분 걸리기도 한다. 운영에 뷰를 넣을 때는 스테이징에서 빌드 시간을 재 두고, 조회가 적은 시간대에 더미 요청으로 인덱스를 먼저 채운다.

2.0부터 들어온 Mango 쿼리는 MongoDB 문법과 비슷해서 진입장벽이 낮다.

```bash
curl -X POST http://admin:password@localhost:5984/orders/_find \
     -H "Content-Type: application/json" \
     -d '{
       "selector": {
         "type": "order",
         "status": "pending",
         "total": {"$gt": 10000}
       },
       "sort": [{"created_at": "desc"}],
       "limit": 50
     }'
```

맞는 인덱스가 없으면 풀스캔이 돌고, 경고는 로그가 아니라 응답 본문의 `warning` 필드에 실린다. 상태코드는 200이라 클라이언트가 이 필드를 보지 않으면 놓친다.

```text
"warning": "No matching index found, create an index to optimize query time."
```

인덱스를 명시적으로 만들 때는 `ddoc` 도 같이 정해 둔다.

```bash
curl -X POST http://admin:password@localhost:5984/orders/_index \
     -H "Content-Type: application/json" \
     -d '{
       "index": {"fields": ["type", "status", "created_at"]},
       "ddoc": "order-status",
       "name": "order-status-idx",
       "type": "json"
     }'
```

`ddoc` 를 빼면 design document 이름이 해시로 만들어진다(`_design/5c7a0b2d...`). 그 상태에서 `use_index: "order-status-idx"` 처럼 인덱스 이름만 주면 문자열을 design document 이름으로 해석해서 못 찾고, 응답에 `_design/order-status-idx was not used because it does not contain a valid index for this query` 가 붙은 채로 풀스캔이 돈다. `use_index` 는 `["order-status", "order-status-idx"]` 형태로 준다.

JSON 인덱스는 인덱스에 들어간 필드가 선택자에 전부 나와야 쓰인다. 위 인덱스로 `type`, `status` 두 조건만 가진 쿼리를 `_explain` 하면 `_all_docs` 가 나왔다. `created_at` 조건이나 정렬이 선택자에 들어간 쿼리(`$gt` 조건 + `sort`)는 인덱스를 탔다.

## 복제 아키텍처

CouchDB의 복제는 단방향이 기본 단위다. source에서 target으로 변경분을 가져온다. 양방향은 두 방향을 각각 등록한다. 복제기는 source의 `_changes` 피드를 읽고, target이 이미 가진 리비전을 빼고, 나머지만 옮긴다. 3.3.3에서 단발 복제를 돌리며 CouchDB 요청 로그에 찍힌 순서가 아래 그림이다.

```mermaid
sequenceDiagram
    participant R as 복제기
    participant S as source
    participant T as target
    R->>S: GET /db/ 와 GET /_local/id
    R->>T: GET /db/ 와 GET /_local/id
    Note over R: 양쪽 체크포인트가 맞으면 recorded_seq부터, 없으면 since=0
    loop 배치마다 반복
        R->>S: GET /_changes?feed=normal&style=all_docs&since=...
        S-->>R: 문서 id와 리프 rev 목록
        R->>T: POST /_revs_diff
        T-->>R: target에 없는 rev만 missing으로 반환
        alt 첨부 없는 문서
            R->>S: POST /_bulk_get?latest=true&revs=true&attachments=false
            S-->>R: 본문과 리비전 이력
            R->>T: POST /_bulk_docs (new_edits=false)
        else 첨부가 있는 문서
            R->>S: GET /doc?revs=true&open_revs=[rev]
            S-->>R: multipart/related (본문 + 첨부)
            R->>T: PUT /doc?new_edits=false
        end
        R->>S: POST /_ensure_full_commit
        R->>T: POST /_ensure_full_commit
        R->>S: PUT /_local/id (recorded_seq)
        R->>T: PUT /_local/id (recorded_seq)
    end
    opt continuous 복제
        loop 따라잡은 뒤
            R->>S: GET /_changes?feed=continuous&timeout=10000&since=last_seq
            Note over R,S: 연결을 닫지 않고 물고 있다. 10초가 지나면 닫히고 다시 연다
            S-->>R: 변경이 생기면 한 줄씩 전달
            R->>T: _revs_diff, _bulk_get, _bulk_docs 반복
        end
    end
```

위쪽 `loop` 는 일회성 복제의 배치 처리, 아래쪽 `opt` 는 `continuous: true` 일 때만 추가되는 구간이다. 체크포인트 읽기에서 404가 먼저 나오는 것(처음 복제할 때 `_local` 문서가 없다)은 정상이다. continuous 복제가 `longpoll` 로 변경을 물고 있다고 알려져 있지만, 3.3.3 로그에는 `feed=continuous&timeout=10000` 이 찍혔다. 작업을 지웠을 때 그 요청이 10004ms 만에 끝난 기록이 남았다. `longpoll` 은 직접 `_changes` 를 호출하는 클라이언트가 고르는 모드다.

### 체크포인트와 배치

복제가 끝나면 source와 target 양쪽에 같은 ID의 `_local` 문서가 남는다. `_local` 문서는 복제되지 않는 문서로, `_rev` 가 `0-1` 형태다.

```bash
curl http://admin:password@localhost:5984/src/_local_docs
# {"total_rows":null,"offset":null,"rows":[
#  {"id":"_local/f746c6cefa80...","key":"_local/f746c6cefa80...","value":{"rev":"0-1"}}]}
```

문서 안에는 `session_id`, `source_last_seq`, `history`(`docs_read`, `docs_written`, `doc_write_failures`, `bulk_get_docs`)가 들어 있다. 복제가 중간에 죽어도 다음 실행이 `recorded_seq` 부터 이어가는 근거가 이 문서다. 복제 결과를 볼 때 `doc_write_failures` 가 0인지부터 본다.

`_revs_diff` 가 하는 일은 응답으로 보인다. target에 없는 리비전은 `missing` 이고, 같은 문서의 이전 리비전이 있으면 `possible_ancestors` 가 같이 온다.

```bash
curl -X POST http://admin:password@localhost:5984/tgt/_revs_diff \
     -H "Content-Type: application/json" \
     -d '{"d2":["1-7a7e4b29...","2-deadbeef"]}'
# 복제 전: {"d2":{"missing":["1-7a7e4b29...","2-deadbeef"]}}
# 복제 후: {"d2":{"missing":["2-deadbeef"],"possible_ancestors":["1-7a7e4b29..."]}}
```

복제기가 target에 쓰는 `new_edits=false` 는 "새 리비전을 만들지 말고 이 리비전과 이력을 그대로 넣어라"는 뜻이다.

```bash
curl -X POST http://admin:password@localhost:5984/tgt/_bulk_docs \
     -H "Content-Type: application/json" \
     -d '{"new_edits":false,"docs":[{"_id":"d3","_rev":"2-aaaa",
          "_revisions":{"start":2,"ids":["aaaa","bbbb"]},"v":9}]}'
# []   201     (같은 요청을 다시 보내도 [] 201)
```

실패한 문서가 있을 때만 배열에 오류가 담기고, 성공하면 빈 배열이다. 같은 요청을 반복해도 에러 없이 넘어가서 복제가 중복 전송에 안전하다.

### _changes 피드와 since

`_changes` 는 모드 세 가지가 있고, 직접 호출해 보면 동작이 갈린다.

| feed | 동작 | 확인한 결과 |
|---|---|---|
| `normal` (기본) | 쌓인 변경을 한 번에 응답하고 연결을 끝낸다 | `results` 배열과 `last_seq`, `pending` |
| `longpoll` | 변경이 생기거나 `timeout` 이 되면 한 번 응답하고 끝낸다 | 변경이 없을 때 3.018초 뒤 빈 `results` + `last_seq`, 1초 뒤 문서를 쓰자 1.037초에 해당 변경 반환 |
| `continuous` | 연결을 유지하고 변경마다 JSON 한 줄을 흘려보낸다 | `heartbeat=1000` 으로 빈 줄이 오고 변경은 한 줄로 도착. `curl -m 4` 가 끊을 때 exit 28 |

`since` 는 단일 클러스터에서도 숫자가 아니다. 클러스터에서는 샤드마다 시퀀스가 따로 있어서, 피드가 돌려주는 값이 불투명 문자열이다.

```bash
curl "http://admin:password@localhost:5984/orders/_changes"
# {"results":[
#  {"seq":"1-g1AAAAHjeJzLYWBg...","id":"q-3","changes":[{"rev":"1-c7a7a74e..."}]},
#  {"seq":"2-g1AAAAIDeJyV0EEK...","id":"q-2","changes":[{"rev":"1-b8f97323..."}]},
#  {"seq":"3-g1AAAAJDeJyV0EEO...","id":"q-1","changes":[{"rev":"1-7a7e4b29..."}]}
# ],"last_seq":"3-g1AAAAJDeJyV0EEO...","pending":0}
```

앞의 숫자는 참고용이고 뒤의 인코딩된 값이 실제 위치다. 세 문서를 `q-1`, `q-2`, `q-3` 순으로 썼는데 피드는 `q-3`, `q-2`, `q-1` 순서로 나왔다. 피드 순서가 쓴 순서와 같다고 가정하면 안 된다. `last_seq` 는 파싱하지 말고 통째로 저장했다가 다음 호출의 `since` 에 그대로 넘긴다. `since=now` 는 현재 시점부터 보겠다는 뜻이다.

`style=all_docs` 가 없으면 충돌 문서도 `changes` 배열에 winner 하나만 나온다. 충돌 문서 하나에서 기본은 `changes` 길이가 1이었고 `style=all_docs` 에서는 2였다. 충돌을 감시하는 소비자는 이 옵션을 켜야 한다.

### 지속 복제 등록

```bash
# 일회성 복제
curl -X POST http://admin:password@localhost:5984/_replicate \
     -H "Content-Type: application/json" \
     -d '{
       "source": "http://src:5984/orders",
       "target": "http://dst:5984/orders_replica"
     }'

# 지속 복제 (continuous)
curl -X POST http://admin:password@localhost:5984/_replicator \
     -H "Content-Type: application/json" \
     -d '{
       "_id": "orders-sync",
       "source": "http://src:5984/orders",
       "target": "http://dst:5984/orders",
       "continuous": true,
       "filter": "orders/active_only"
     }'
```

필터 복제를 쓰면 조건에 맞는 문서만 보낼 수 있다. 모바일 클라이언트가 자기 사용자 ID에 해당하는 문서만 받아가는 구조가 가능하다.

복제 작업은 `_replicator` DB에 저장하는 편이 낫다. CouchDB가 재시작돼도 자동으로 재개되기 때문이다. `_replicate` 엔드포인트 직접 호출은 일시적이라 프로세스가 죽으면 사라진다.

## 충돌 탐지와 해결

양방향 복제나 오프라인 동기화에서는 같은 문서가 양쪽에서 다르게 수정되는 일이 반드시 생긴다. CouchDB는 이걸 숨기지 않는다. 충돌이 나면 문서에 리프가 여럿 공존하고, 그중 하나가 winning revision이 되어 일반 GET에 반환된다. 나머지는 `_conflicts` 배열에 남는다. 어느 노드에서 읽어도 같은 winner가 나오는데, 선택 규칙이 리비전 트리만 보고 결정적으로 정해지기 때문이다.

```mermaid
flowchart TD
    base["2-a9bf58<br/>양쪽 노드의 공통 리비전"] --> a["노드 A가 수정<br/>3-ebcc60"]
    base --> b["노드 B가 수정<br/>3-25c2ad"]
    a --> rep["양방향 복제"]
    b --> rep
    rep --> leaves{"삭제되지 않은 리프가 둘"}
    leaves --> rule["winner 선택<br/>1 삭제 안 된 리프 우선<br/>2 리비전 깊이가 큰 쪽<br/>3 같으면 해시 문자열이 큰 쪽"]
    rule --> win["winner 3-ebcc60<br/>GET이 돌려주는 리비전"]
    rule --> lose["3-25c2ad<br/>_conflicts에 남음"]
    win --> detect["앱이 conflicts=true 또는 뷰로 감지"]
    lose --> detect
    detect --> merge["winner 3-ebcc60에 병합 문서 PUT<br/>결과 4-7efe12"]
    merge --> del["패배 리비전 DELETE ?rev=3-25c2ad<br/>결과 4-ac8753 삭제 표시"]
    del --> done["_conflicts 비어 있음<br/>복제로 양쪽 DB가 같은 상태로 수렴"]
```

그림은 3.3.3에서 실제로 만든 충돌의 해시를 줄여 쓴 것이다. 같은 `ord-1001` 을 두 DB에서 2-rev 에서 각자 수정하고 복제한 뒤의 응답은 이랬다.

```bash
curl "http://admin:password@localhost:5984/orders/ord-1001?conflicts=true"
# {"_id":"ord-1001","_rev":"3-ebcc60a...","status":"shipped",
#  "_conflicts":["3-25c2ad21..."]}
```

### winning revision 선택 규칙

winner는 순서대로 세 가지를 본다. 삭제되지 않은 리프가 삭제된 리프보다 먼저고, 그다음이 리비전 깊이(`N-` 의 N)가 큰 쪽, 마지막으로 N이 같을 때 해시 문자열이 사전순으로 큰 쪽이다. "깊이가 큰 쪽이 이긴다"만 알면 삭제 가지에서 틀린다. `new_edits=false` 로 가지를 직접 만들어 확인했다.

| 문서 | 리프 | 결과 |
|---|---|---|
| case1 | 4- (삭제됨), 3- (살아 있음) | 3- 가 winner. 4- 는 `_deleted_conflicts` |
| case2 | 4-aaaa (살아 있음), 3-ffff (살아 있음) | 4-aaaa 가 winner. 해시가 작아도 깊이가 먼저 |
| case3 | 3-aaaa, 3-bbbb | 3-bbbb 가 winner. 깊이가 같으면 해시 |
| case4 | 3-aaaa (삭제됨), 4-bbbb (삭제됨) | 모두 삭제면 문서가 404 `{"error":"not_found","reason":"deleted"}` |

winner는 의미 있는 승자가 아니라 결정적인 선택일 뿐이다. 앱이 두 버전을 가져와 병합해야 한다. 재고 수량처럼 양쪽에서 줄어든 값을 합쳐야 하는 경우도 있어서, 마지막 쓰기 승리를 그냥 받아들이면 데이터가 조용히 사라진다. 충돌 해결 로직이 CouchDB 앱 개발에서 가장 어려운 부분이다.

### 병합 문서를 쓰고 패배 리비전을 지운다

충돌은 병합 문서를 쓴다고 사라지지 않는다. 다음 순서로 실행했다.

```bash
# 1) winner 에 병합 문서 PUT
curl -X PUT http://admin:password@localhost:5984/na/ord-1001 \
     -d '{"_rev":"3-ebcc60...","status":"shipped","note":"merged"}'
# {"ok":true,"id":"ord-1001","rev":"4-7efe12c2..."}   201

curl "http://admin:password@localhost:5984/na/ord-1001?conflicts=true"
# {"_id":"ord-1001","_rev":"4-7efe12c2...","status":"shipped","note":"merged",
#  "_conflicts":["3-25c2ad21..."]}          <- 패배 리비전이 아직 남아 있다

# 2) 패배 리비전 삭제
curl -X DELETE "http://admin:password@localhost:5984/na/ord-1001?rev=3-25c2ad21..."
# {"ok":true,"id":"ord-1001","rev":"4-ac8753a0..."}   200

curl "http://admin:password@localhost:5984/na/ord-1001?conflicts=true&deleted_conflicts=true"
# {"_id":"ord-1001","_rev":"4-7efe12c2...","status":"shipped","note":"merged",
#  "_deleted_conflicts":["4-ac8753a0..."]}
```

1단계만 하고 끝내면 `_conflicts` 가 계속 남는다. 2단계의 DELETE 가 패배 가지의 끝에 삭제 리비전을 붙여 충돌에서 빼 준다. 이 상태를 `na` 에서 `nb` 로 복제하면 `nb` 도 같은 응답을 돌려줬다. 이미 패배 리비전을 DELETE 한 뒤에 그 `_rev` 로 PUT 하면 409다.

충돌 문서를 찾는 건 뷰 하나면 된다.

```javascript
{
  "_id": "_design/c",
  "views": {
    "conflicts": {
      "map": "function(doc) { if (doc._conflicts) { emit(doc._id, doc._conflicts); } }"
    }
  }
}
// GET /na/_design/c/_view/conflicts
// {"total_rows":1,"offset":0,"rows":[{"id":"ord-1001","key":"ord-1001","value":["3-25c2ad21..."]}]}
```

복제는 언제든 새 충돌을 들여온다. 이 뷰를 주기적으로 읽어 해결 로직을 돌려야 한다. 돌리지 않으면 `_conflicts` 가 쌓여 문서가 커진다.

## PouchDB와 오프라인 동기화

PouchDB는 브라우저와 Node.js에서 동작하는 JavaScript 구현체로, CouchDB와 복제 프로토콜이 호환된다. IndexedDB를 로컬 스토리지로 쓰고, 네트워크가 연결되면 CouchDB와 양방향 동기화를 한다.

```javascript
import PouchDB from 'pouchdb';

const local = new PouchDB('orders_local');
const remote = new PouchDB('http://admin:password@couch.example.com:5984/orders');

local.sync(remote, { live: true, retry: true })
  .on('change', (info) => {
    console.log('변경 동기화됨', info.direction, info.change.docs.length);
  })
  .on('error', (err) => {
    console.error('동기화 오류', err);
  });

// 오프라인에서도 그냥 로컬에 쓰면 된다
await local.put({
  _id: `order-${Date.now()}`,
  type: 'order',
  total: 25000,
  status: 'pending'
});
```

현장 직원이 태블릿으로 창고 입출고를 기록하는 시스템에 이 구조를 썼다. 창고 내부는 Wi-Fi가 약해서 수시로 끊기는데, PouchDB는 연결이 복구되면 밀린 변경을 자동으로 올려보낸다. 사용자는 오프라인이라는 상태를 느끼지 못한다.

다만 여러 단말이 같은 규칙으로 `_id` 를 만들면 단말끼리 같은 문서를 새로 만든다. 본문이 같으면 같은 1- 리비전이라 `docs_written` 이 0으로 합쳐지지만, 본문이 다르면 1- 리비전 두 개가 충돌한다. `order-${Date.now()}` 처럼 단말 ID나 UUID 를 섞어 `_id` 를 겹치지 않게 만든다.

## 클러스터링과 샤딩

CouchDB 2.0 이후부터는 BigCouch 기반의 샤드 클러스터링이 내장됐다. DB 생성 시 `q`(샤드 수)와 `n`(복제본 수)을 정하고, 각 요청에는 쿼럼(quorum)이 적용된다.

3.x에서 노드 추가 경로가 바뀌었다. 2.x 문서에 나오는 5986 포트는 3.3.3 컨테이너 안에서 `localhost:5986` 으로 호출해도 연결이 되지 않았다(curl 코드 000). 노드 정보는 5984 포트의 `/_node/_local/_nodes/` 에 쓴다.

```bash
# 노드 추가 (3.x)
curl -X PUT http://admin:password@node1:5984/_node/_local/_nodes/couchdb@node2.example.com \
     -d '{}'
# {"ok":true,"id":"couchdb@c2.cnet","rev":"1-967a00df..."}   201

curl http://admin:password@node1:5984/_membership
# {"all_nodes":["couchdb@c1.cnet","couchdb@c2.cnet","couchdb@c3.cnet"],
#  "cluster_nodes":["couchdb@c1.cnet","couchdb@c2.cnet","couchdb@c3.cnet"]}

# 시스템 DB도 만들어 둔다
curl -X PUT http://admin:password@node1:5984/_users
curl -X PUT http://admin:password@node1:5984/_replicator

# 샤드 8개, 복제본 3개로 DB 생성
curl -X PUT "http://admin:password@node1:5984/orders?q=8&n=3"
```

도커로 3.3.3 노드 세 개를 띄울 때 `ERL_FLAGS="-setcookie monster"` 처럼 기본 쿠키를 그대로 쓰면 `Monster detected ohno!, aborting startup.` 을 찍고 시작하지 않는다. 노드마다 같은 쿠키(기본값이 아닌 값)와 같은 `COUCHDB_SECRET` 을 줘야 한다.

### 샤드 배치와 코디네이터

`q=8, n=3` DB를 노드 3대에 만들고 `_shards` 를 읽으면 8개 레인지 모두에 노드 3대가 전부 올라온다. 노드 수가 `n` 과 같아서 각 노드가 레인지 8개의 사본을 하나씩 갖는 배치다. 샤드 파일은 노드당 8개, 전체 24개다.

```bash
curl http://admin:password@node1:5984/orders/_shards
# 00000000-1fffffff ['couchdb@c3.cnet', 'couchdb@c2.cnet', 'couchdb@c1.cnet']
# 20000000-3fffffff ['couchdb@c3.cnet', 'couchdb@c2.cnet', 'couchdb@c1.cnet']
# ...
# e0000000-ffffffff ['couchdb@c3.cnet', 'couchdb@c2.cnet', 'couchdb@c1.cnet']

curl http://admin:password@node1:5984/orders
# "cluster":{"q":8,"n":3,"w":2,"r":2}
```

노드가 6대라면 같은 24개 사본이 6대에 나뉘어 배치된다. 요청을 받은 노드가 코디네이터가 되어 문서 ID 해시로 레인지를 정하고, 그 레인지 사본을 가진 노드들에 요청을 보낸다.

```mermaid
flowchart TB
    client["클라이언트<br/>PUT /orders/ord-1001"] --> coord["코디네이터<br/>요청을 받은 노드"]
    coord -->|"문서 ID 해시로 레인지 결정<br/>예 40000000-5fffffff"| c1n
    coord --> c2n
    coord --> c3n
    subgraph node1["node1"]
        c1n["8개 레인지 사본 중<br/>40000000-5fffffff"]
    end
    subgraph node2["node2"]
        c2n["8개 레인지 사본 중<br/>40000000-5fffffff"]
    end
    subgraph node3["node3"]
        c3n["8개 레인지 사본 중<br/>40000000-5fffffff"]
    end
    c1n -.->|"ack"| coord
    c2n -.->|"ack"| coord
    c3n -.->|"ack"| coord
    coord -->|"ack가 w=2개 이상이면 201<br/>쓰기는 됐지만 w 미달이면 202"| client
```

점선이 각 사본의 응답이고 코디네이터가 `w`(쓰기)나 `r`(읽기)만큼 모아 클라이언트에 답한다. 기본값은 `n=3` 에서 `w=2, r=2` 였다.

### 쿼럼을 못 채웠을 때

쿼럼을 못 맞춘 쪽이 실패 응답을 낸다고 알고 있으면 틀린다. 노드 2대를 내리고 살아 있는 `c1` 하나에만 요청했더니 이랬다.

| 요청 | 상태 | 응답 |
|---|---|---|
| 3대 정상, `PUT /orders/q-1` | 201 | `{"ok":true,"id":"q-1","rev":"1-7a7e4b29..."}` |
| 2대 중단, `PUT /orders/q-2` (w=2 미달) | 202 | `{"ok":true,"id":"q-2","rev":"1-b8f97323..."}` |
| 2대 중단, `PUT /orders/q-3?w=1` | 201 | `{"ok":true,"id":"q-3","rev":"1-c7a7a74e..."}` |
| 2대 중단, `GET /orders/q-2` (r=2 미달) | 200 | 문서 본문 |
| 2대 중단, `GET /orders/q-2?r=3` | 200 | 문서 본문 |
| 2대 중단, `GET /orders/_all_docs` | 200 | 3건 |

3.x는 디스크에 쓰기가 됐으면 `w` 를 못 채워도 202 Accepted를 반환한다. 읽기도 `r` 에 못 미쳐도 가용한 사본에서 답한다. `_membership` 의 `all_nodes` 는 `c1` 하나인데 `cluster_nodes` 는 3대로 남아 있었다. 노드를 복구하고 얼마 뒤에 노드별 샤드를 직접 열어 보면 쓰기 때 내려가 있던 두 노드에도 `q-2` 가 들어와 있었다.

```bash
curl "http://admin:password@node2:5984/_node/_local/shards%2F40000000-5fffffff%2Forders.<타임스탬프>/_all_docs"
# {"total_rows":1,"offset":0,"rows":[{"id":"q-2","key":"q-2","value":{"rev":"1-b8f97323..."}}]}
```

운영에서 챙길 점은 두 가지다. 202는 2xx라서 대부분의 HTTP 클라이언트가 성공으로 처리한다. 쓰기 성공 여부를 "w 만큼 복제됐는가"로 판단하는 코드가 있으면 상태코드가 202인지 직접 봐야 한다. 두 번째로 노드가 갈라져 양쪽이 각자 쓰기를 받으면 복구 때 같은 문서가 서로 다른 가지가 된다. 이 경우 위 충돌 절의 처리가 필요하다.

다만 실무에서 CouchDB 클러스터를 적극적으로 운영하는 사례는 많지 않다. 쓰기 스케일이 정말 필요하면 보통 다른 DB를 고르고, CouchDB는 단일 노드와 복제본으로 읽기를 분산하는 형태로 많이 쓴다.

## 인증과 _users DB

CouchDB는 `_users` 라는 내장 DB에 사용자 정보를 저장한다. 사용자 문서는 일반 문서와 같은 구조지만 CouchDB가 자동으로 PBKDF2로 비밀번호를 해싱한다.

```bash
curl -X PUT http://admin:password@localhost:5984/_users/org.couchdb.user:alice \
     -H "Content-Type: application/json" \
     -d '{
       "name": "alice",
       "password": "plaintext_here",
       "roles": ["reader"],
       "type": "user"
     }'
```

DB별 권한은 `_security` 문서로 관리한다. 멤버(읽기/쓰기)와 어드민(설계 문서 수정 가능)을 역할 또는 사용자 이름으로 지정한다. 세션 인증은 `_session` 엔드포인트로 쿠키를 받는 방식이고, HTTP Basic도 지원한다.

3.3.3에서 관리자 계정을 만들어 띄우면 인증 없이 `GET /_all_dbs` 는 `401 {"error":"unauthorized","reason":"You are not a server admin."}`, 일반 DB 문서 조회는 `401 ... not authorized to access this db` 였다. 2.x 시절 설정을 옮겨 오는 경우에는 `admin_only_all_dbs` 와 `require_valid_user` 값을 `GET /_node/_local/_config` 로 확인한다. 5984 포트가 외부에 직접 열리지 않도록 리버스 프록시 뒤에 두는 것도 기본이다.

## 운영 중 자주 만나는 문제

디스크 사용량 급증이 가장 흔하다. 쓰기가 잦은 DB는 하루에 기대치의 5~10배 용량이 쌓이기도 한다. 위의 51번 수정 실험이 보여주듯 문서 하나의 수정만으로도 파일이 불어난다. 리비전 트리를 짧게 유지하려면 `_revs_limit` 을 조정하거나(기본 1000, `GET /db/_revs_limit` 으로 확인) compaction 을 스케줄링한다.

View 인덱스 빌드 시간도 골칫거리다. Design document를 수정하면 해당 design doc의 뷰가 전부 다시 빌드된다. 한 design doc에 뷰를 여러 개 묶으면 하나만 바뀌어도 전부 재빌드된다. 변경 빈도가 다른 뷰는 design doc을 분리한다.

Continuous 복제가 멈추는 경우는 `_scheduler/docs/_replicator/<문서 id>` 로 상태를 본다. source 인증 정보를 틀리게 넣은 복제 문서를 등록하면 `state` 가 `crashing` 이 되고 `info.error` 에 `replication_auth_error ... session_request_unauthorized` 가 찍혔고, 같은 문서가 `_scheduler/jobs` 에도 올라와 있었다. 대상 DB의 인증 오류나 충돌 폭증이 흔한 원인이다. 모니터링에 `_scheduler/docs` 의 `state` 확인을 넣어 둔다.

리비전 트리가 비정상적으로 커져 문서 하나가 수 MB가 되는 경우가 있다. 삭제한 문서를 같은 `_id` 로 다시 만드는 패턴이 반복될 때 생긴다. 삭제 표시(tombstone)도 트리에 남고 재생성은 그 뒤에 이어 붙는다. 11번째 리비전을 지우고 다시 만들자 12-가 삭제, 13-이 재생성이었다. 삭제 대신 `deleted: true` 플래그를 쓰는 소프트 딜리트로 우회한다.

## Node.js nano 드라이버

공식 Node.js 드라이버는 `nano` 다. HTTP 클라이언트를 얇게 감싼 정도라 CouchDB API를 그대로 쓴다. 이 절의 예제는 nano 11.0.7로 실행해서 확인했다.

```javascript
const nano = require('nano')('http://admin:password@localhost:5984');
const orders = nano.db.use('orders');

async function updateOrder(id, patch) {
  const retry = async (attempt = 0) => {
    try {
      const current = await orders.get(id);
      const updated = { ...current, ...patch };
      return await orders.insert(updated);
    } catch (err) {
      if (err.statusCode === 409 && attempt < 3) {
        return retry(attempt + 1);
      }
      throw err;
    }
  };
  return retry();
}

async function findPendingOrders() {
  const result = await orders.find({
    selector: { type: 'order', status: 'pending', created_at: { $gt: null } },
    sort: [{ type: 'desc' }, { status: 'desc' }, { created_at: 'desc' }],
    limit: 100,
    use_index: ['order-status', 'order-status-idx']
  });
  return result.docs;
}

function streamChanges(onChange) {
  const reader = orders.changesReader.start({ since: 'now', includeDocs: true });
  reader.on('change', onChange);
  return reader;
}
```

이전에 `orders.follow({ since: 'now', include_docs: true })` 로 쓰던 부분은 nano 11에서 `typeof orders.follow` 가 `undefined` 였다. 변경 스트림은 `changesReader` 를 쓴다. `include_docs` 가 아니라 `includeDocs` 이고, 변경 한 건 처리할 때 `c.doc._rev` 를 받는 것까지 `o1 2-7b` 처럼 확인했다.

409 재시도 로직은 CouchDB 앱의 기본기다. 낙관적 동시성이라 같은 문서를 동시에 고치면 409가 일상적으로 나고, 최신 rev를 다시 읽어 재시도하는 패턴이 기본이다. 위 `insert` 에 `_rev` 없이 기존 `_id` 를 넣으면 `statusCode` 409에 `Document update conflict.` 가 `reason` 으로 나온다. `changesReader` 는 이벤트 소싱이나 CQRS의 read model 갱신에 쓸 수 있다.

## CouchDB를 선택해야 하는 상황

오프라인 동기화가 핵심 요구사항인 경우, 예를 들어 현장 조사 앱, POS, 태블릿 기반 업무 시스템에서는 CouchDB와 PouchDB 조합 말고 마땅한 대안이 드물다. 지점별 로컬 DB가 본사와 양방향으로 동기화되어야 하는 유통·물류 시스템도 마찬가지다.

데이터 파이프라인에서 변경 피드가 핵심인 경우에도 맞는다. `_changes` 를 CDC(Change Data Capture)로 쓸 수 있어서 Debezium 같은 도구가 필요하지 않다. 소비자는 `since` 로 받은 문자열을 저장했다가 그대로 넘기면 되고, 충돌 문서까지 보려면 `style=all_docs` 를 켠다.

HTTP API만으로 모든 걸 처리할 수 있어서 스크립트로 빠르게 만드는 프로토타입이나 관리 도구에도 편하다.

## CouchDB를 피해야 하는 상황

쓰기 처리량이 초당 수천 건 이상 필요하면 맞지 않는다. 리비전 관리와 append-only 구조가 쓰기 오버헤드를 만든다. 시계열 데이터 적재, 로그 수집, 광고 이벤트 처리 같은 워크로드는 다른 DB를 써야 한다.

복잡한 집계 쿼리가 실시간으로 필요한 BI 시스템에도 맞지 않는다. Map/Reduce 뷰는 사전에 정의한 인덱스에 의존해서 ad-hoc 분석이 불편하다. Mango도 SQL에 비하면 표현력이 제한적이다.

다중 문서 트랜잭션이 필요한 업무(계좌 이체, 재고 차감과 주문 생성의 원자적 처리)는 CouchDB의 설계와 맞지 않는다. 억지로 구현하면 보정 로직이 복잡해지고, 리비전을 노출하는 낙관적 동시성의 이점도 사라진다.

CouchDB는 뭘 해도 평균 이상인 DB가 아니다. 복제와 오프라인 동기화라는 분명한 강점 영역이 있고, 그 밖에서는 대체재가 더 낫다. 도입 전에 이 강점이 우리 시스템에 실제로 필요한지부터 확인한다.
