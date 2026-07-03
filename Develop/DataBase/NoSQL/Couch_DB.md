---
title: CouchDB
tags:
  - DataBase
  - NoSQL
  - CouchDB
  - Replication
  - MVCC
updated: 2026-04-17
---

# CouchDB

## 정의와 철학

CouchDB는 Apache 재단이 관리하는 문서 지향 NoSQL 데이터베이스다. JSON 문서를 HTTP/REST API로 읽고 쓰는 구조라서, 드라이버 없이 `curl`만으로도 모든 기능을 쓸 수 있다. MongoDB가 바이너리 프로토콜(MongoDB Wire Protocol)과 BSON 위에서 동작하는 반면, CouchDB는 처음부터 "웹과 같은 방식"을 지향해서 모든 요청이 HTTP 메서드(GET/PUT/POST/DELETE)로 매핑된다.

실무에서 CouchDB를 선택하는 이유는 대부분 성능이 아니라 복제(replication)와 오프라인 동기화다. 모바일 클라이언트가 간헐적으로 연결되는 환경, 지점별 로컬 DB가 본사와 양방향으로 동기화되어야 하는 환경에서 CouchDB의 진가가 드러난다. 대신 쓰기 처리량이나 쿼리 유연성에서는 MongoDB에 비해 부족한 점이 많다.

## MongoDB와의 핵심 차이

가장 큰 차이는 동시성 모델이다. MongoDB는 문서 단위 락(WiredTiger의 document-level concurrency)을 쓰고, CouchDB는 MVCC(Multi-Version Concurrency Control)를 쓴다. CouchDB에서 모든 문서는 `_id`와 `_rev`를 갖고, 수정 시 기존 리비전을 덮어쓰는 게 아니라 새 리비전을 만든다. 이게 복제와 충돌 해결의 기반이다.

```bash
# 문서 생성
curl -X PUT http://admin:password@localhost:5984/orders/ord-1001 \
     -H "Content-Type: application/json" \
     -d '{"customer":"kim","total":45000,"status":"pending"}'

# 응답
# {"ok":true,"id":"ord-1001","rev":"1-a8f3c4..."}

# 수정 시 반드시 현재 rev를 함께 보내야 한다
curl -X PUT http://admin:password@localhost:5984/orders/ord-1001 \
     -H "Content-Type: application/json" \
     -d '{"_rev":"1-a8f3c4...","customer":"kim","total":45000,"status":"paid"}'
```

`_rev` 없이 수정하면 409 Conflict가 떨어진다. MongoDB의 `findAndModify`나 `$set`처럼 블라인드 업데이트가 불가능하다. 클라이언트는 항상 "내가 본 버전"을 명시해야 한다. 처음 쓰면 불편하지만, 이 제약이 복제 충돌을 구조적으로 막아준다.

또 하나 큰 차이는 트랜잭션이다. CouchDB는 다중 문서 트랜잭션이 없다. `_bulk_docs` API로 여러 문서를 한 번에 보낼 수는 있지만, 일부 성공/일부 실패가 가능한 "all-or-nothing이 아닌" 일괄 처리다. 금융 거래 같은 원자성이 필요한 업무는 애초에 맞지 않는다.

## 문서 모델과 JSON 저장 구조

CouchDB의 문서는 그냥 JSON이다. 스키마가 없고, `_id`와 `_rev`만 예약 필드다. 중첩 구조도 자유롭고 배열도 된다.

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

한 데이터베이스에 여러 타입의 문서가 섞여 들어간다. MongoDB처럼 컬렉션 개념이 없어서, 보통 `type` 필드로 문서를 구분하고 뷰나 Mango 쿼리에서 필터링한다. 이게 어색하지만 복제 단위를 DB로 쓰려면 이렇게 섞는 편이 오히려 낫다. "사용자 관련 데이터 전체를 한 번에 복제"하는 구조가 되기 때문이다.

## B-tree 기반 Append-only 스토리지

CouchDB의 스토리지 엔진은 전통적인 B+tree지만 append-only 방식이다. 모든 쓰기는 파일 끝에 새 B-tree 노드를 추가하고, 루트 포인터만 갱신한다. 기존 페이지를 덮어쓰지 않기 때문에 크래시가 나도 파일 앞쪽 데이터는 절대 깨지지 않는다. `fsync`만 끝나면 그 시점까지의 데이터는 복구 가능하다.

단점은 디스크 사용량이다. 문서를 10번 수정하면 예전 버전 10개가 파일에 그대로 남는다. 이걸 정리하려면 compaction을 돌려야 한다.

```bash
# 특정 DB compaction
curl -X POST http://admin:password@localhost:5984/orders/_compact \
     -H "Content-Type: application/json"

# 뷰 인덱스 compaction
curl -X POST http://admin:password@localhost:5984/orders/_compact/design_doc_name \
     -H "Content-Type: application/json"
```

Compaction은 현재 리비전만 살려서 새 파일로 다시 쓰는 작업이다. 운영 중에 돌아가지만 I/O를 많이 먹는다. DB가 100GB 넘어가면 compaction 자체가 몇 시간 걸리고, 그 동안 디스크는 원본 + 작업본 두 벌이 존재해서 순간적으로 2배 공간이 필요하다. 용량 계획할 때 이 점을 꼭 고려해야 한다. 5년 전에 운영 중인 50GB DB를 compaction 돌렸다가 디스크 가득 찼던 경험이 있다. 그 뒤로는 여유 공간을 항상 DB 크기의 2배 이상 확보한다.

`auto_compaction`을 켜면 조각화 비율을 보고 자동으로 돌아가지만, 큰 DB에서는 새벽 시간대에 수동으로 돌리는 편이 예측 가능하다.

## 뷰(Map/Reduce)와 Mango 쿼리

CouchDB의 원래 쿼리 방식은 JavaScript로 작성하는 Map/Reduce 뷰다. Design document 안에 뷰를 정의하고, CouchDB가 그 결과를 인덱스로 영구 저장한다.

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

이 뷰를 처음 조회하면 CouchDB가 전체 DB를 스캔해서 인덱스를 만든다. 1000만 건짜리 DB에 새 뷰를 추가하면 첫 요청이 몇십 분 걸리는 경우도 있다. 운영 환경에서 뷰를 추가할 때는 사전에 스테이징에서 빌드 시간을 측정하고, 실제 배포 시에는 조회 트래픽이 적은 시간대에 더미 요청으로 먼저 인덱스를 채워놓는 전략을 쓴다.

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

Mango는 내부적으로 뷰를 만들거나 기존 인덱스를 쓴다. `_index` 엔드포인트로 명시적 인덱스를 만들어두지 않으면 warning 로그가 찍히면서 풀스캔이 돌아간다. 이게 운영에서 제일 자주 만나는 함정이다.

```bash
# 인덱스 명시 생성
curl -X POST http://admin:password@localhost:5984/orders/_index \
     -H "Content-Type: application/json" \
     -d '{
       "index": {"fields": ["type", "status", "created_at"]},
       "name": "order-status-idx",
       "type": "json"
     }'
```

## 복제 아키텍처

CouchDB의 복제는 단방향이 기본 단위다. "source → target"으로 변경분을 당겨온다. `_changes` 피드가 순차적인 시퀀스 번호를 가지고 있어서, 마지막으로 복제된 시퀀스만 기억하면 중단됐다 재개해도 정확히 이어진다.

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

양방향 복제는 두 방향을 각각 등록하면 된다. `continuous: true`로 걸어두면 `_changes` 피드를 long-polling으로 물고 있다가 변경이 생기면 즉시 전파한다. 필터 복제를 쓰면 특정 조건의 문서만 내려보낼 수 있어서, 모바일 클라이언트가 자기 사용자 ID에 해당하는 문서만 받아가는 구조가 가능하다.

실무에서 `_replicator` DB에 복제 작업을 저장하는 방식을 권장한다. CouchDB가 재시작돼도 자동으로 재개되기 때문이다. `_replicate` 엔드포인트 직접 호출은 일시적이라 프로세스가 죽으면 사라진다.

## 충돌 탐지와 해결

양방향 복제나 오프라인 동기화에서는 같은 문서가 양쪽에서 다르게 수정되는 일이 반드시 생긴다. CouchDB는 이걸 숨기지 않고 명시적으로 드러낸다. 충돌이 발생하면 문서에 여러 리비전이 공존하고, 그 중 하나가 "winning revision"으로 선택되어 일반 GET에 반환된다. 나머지는 `_conflicts` 배열에 남아있다.

```bash
# 충돌 확인
curl "http://admin:password@localhost:5984/orders/ord-1001?conflicts=true"

# 응답
# {
#   "_id": "ord-1001",
#   "_rev": "3-abc...",
#   "status": "shipped",
#   "_conflicts": ["3-xyz..."]
# }
```

Winning revision은 리비전 트리 깊이가 큰 쪽, 같으면 `_rev` 값의 사전 순으로 큰 쪽이 선택된다. 이게 의미 있는 "승자"는 아니고 결정적인 선택일 뿐이다. 애플리케이션 레벨에서 두 버전을 가져와 병합 로직을 돌려야 한다.

"마지막 쓰기 승리" 전략을 당연하게 쓰지 말라는 말이다. 재고 수량처럼 양쪽에서 감소된 값을 더해야 하는 경우도 있다. 충돌 해결 로직을 짜는 게 CouchDB 앱 개발의 가장 어려운 부분이다.

## PouchDB와 오프라인 동기화

PouchDB는 브라우저와 Node.js에서 동작하는 JavaScript 구현체로, CouchDB와 복제 프로토콜이 완전히 호환된다. IndexedDB를 로컬 스토리지로 쓰고, 네트워크가 연결되면 CouchDB와 양방향 동기화를 한다.

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

현장 직원이 태블릿으로 창고 입출고를 기록하는 시스템에 이 구조를 썼던 적이 있다. 창고 내부는 Wi-Fi가 약해서 수시로 끊기는데, PouchDB는 연결이 복구되면 자동으로 밀린 변경을 올려보낸다. 사용자 입장에서는 오프라인이라는 개념 자체를 느끼지 못한다. 이런 시나리오는 MongoDB로는 직접 구현하기 어렵다.

## 클러스터링과 샤딩

CouchDB 2.0 이후부터는 BigCouch 기반의 샤드 클러스터링이 내장됐다. DB 생성 시 `q`(샤드 수)와 `n`(복제본 수)를 정하고, 각 요청에는 쿼럼(quorum)이 적용된다.

```bash
# 노드 추가
curl -X PUT http://admin:password@node1:5986/_nodes/couchdb@node2.example.com \
     -d '{}'

# 샤드 8개, 복제본 3개로 DB 생성
curl -X PUT "http://admin:password@node1:5984/orders?q=8&n=3"
```

읽기/쓰기 기본 쿼럼은 `(n+1)/2`다. n=3이면 2개 노드가 응답해야 성공이다. 이 값이 일관성과 가용성의 트레이드오프를 결정한다. 네트워크 파티션 상황에서 소수 측 노드는 쿼럼을 못 맞춰 실패 응답이 나가는 게 기본 동작이다.

다만 실무에서 CouchDB 클러스터를 적극적으로 운영하는 사례는 많지 않다. 쓰기 스케일이 정말 필요하면 보통 다른 DB를 선택하고, CouchDB는 단일 노드 + 복제본으로 읽기를 분산하는 형태로 많이 쓴다.

## 인증과 _users DB

CouchDB는 `_users`라는 내장 DB에 사용자 정보를 저장한다. 사용자 문서는 일반 문서와 같은 구조지만 CouchDB가 자동으로 PBKDF2로 비밀번호를 해싱한다.

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

운영에서는 `httpd/secure_rewrites`, `admin_only_all_dbs` 같은 옵션을 반드시 확인해야 한다. 초기 설정 그대로 두면 `_all_dbs`로 DB 목록이 노출된다. 또 5984 포트가 외부에 직접 열리지 않도록 리버스 프록시 뒤에 두는 게 기본이다.

## 운영 중 자주 만나는 문제

디스크 사용량 급증이 가장 흔한 이슈다. 쓰기 빈도가 높은 DB는 하루에 기대치의 5~10배 용량이 쌓일 수 있다. 리비전 트리를 짧게 유지하려면 `_revs_limit`를 조정하거나(기본 1000), 주기적인 compaction을 스케줄링한다.

View 인덱스 빌드 시간도 골칫거리다. Design document를 수정하면 해당 뷰 전체가 다시 빌드된다. 한 design doc에 뷰를 여러 개 묶으면 하나만 바뀌어도 전부 재빌드된다는 점을 기억해야 한다. 변경 빈도가 다른 뷰는 design doc을 분리한다.

Continuous 복제가 조용히 멈추는 경우도 있다. `_scheduler/jobs`로 상태를 확인하고, crashed 상태면 원인(대부분 대상 DB의 인증 오류나 문서 충돌 폭증)을 찾아야 한다. 모니터링에 `_scheduler/jobs` 체크를 반드시 넣어두는 게 좋다.

리비전 트리가 비정상적으로 커져서 문서 하나의 크기가 수 MB가 되는 경우가 있다. 삭제했던 문서를 같은 `_id`로 다시 만드는 패턴이 반복되면 발생한다. 삭제된 리비전(tombstone)도 트리에 남기 때문이다. 삭제 대신 `deleted: true` 플래그를 쓰는 소프트 딜리트로 우회한다.

## Node.js nano 드라이버

공식 Node.js 드라이버는 `nano`다. HTTP 클라이언트를 살짝 감싼 정도라 CouchDB API를 그대로 쓴다.

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
    selector: { type: 'order', status: 'pending' },
    sort: [{ created_at: 'desc' }],
    limit: 100,
    use_index: 'order-status-idx'
  });
  return result.docs;
}

async function streamChanges(onChange) {
  const feed = orders.follow({ since: 'now', include_docs: true });
  feed.on('change', onChange);
  feed.follow();
  return feed;
}
```

409 재시도 로직은 CouchDB 앱의 기본기다. 낙관적 동시성이라 쓰기 충돌이 일상적으로 발생하고, 애플리케이션이 최신 rev를 다시 읽어 재시도하는 패턴이 기본이다. `follow`는 `_changes` 피드를 스트리밍으로 물고 있다가 변경 이벤트를 준다. 이벤트 소싱이나 CQRS의 read model 갱신에 쓸 수 있다.

## CouchDB를 선택해야 하는 상황

오프라인 동기화가 핵심 요구사항인 경우, 예를 들어 현장 조사 앱, POS, 태블릿 기반 업무 시스템에서는 CouchDB + PouchDB 조합이 독보적이다. 지점별 로컬 DB가 본사와 양방향으로 동기화되어야 하는 유통·물류 시스템도 마찬가지다.

데이터 파이프라인에서 "변경 피드"가 핵심인 경우도 잘 맞는다. `_changes`는 거의 완벽한 CDC(Change Data Capture)로 쓸 수 있다. 별도 Debezium 같은 게 필요 없다.

HTTP API만으로 모든 걸 처리할 수 있다는 점 때문에 스크립트로 빠르게 만드는 프로토타입이나 관리 도구에도 편리하다.

## CouchDB를 피해야 하는 상황

쓰기 처리량이 초당 수천 건 이상 필요하면 맞지 않는다. MVCC와 append-only 구조가 쓰기 오버헤드를 크게 만든다. 시계열 데이터 적재, 로그 수집, 광고 이벤트 처리 같은 워크로드는 다른 DB를 써야 한다.

복잡한 집계 쿼리가 실시간으로 필요한 BI 시스템에도 맞지 않는다. Map/Reduce 뷰는 사전 정의된 인덱스에 의존해서 ad-hoc 분석에는 불편하다. Mango도 SQL에 비하면 표현력이 제한적이다.

다중 문서 트랜잭션이 필요한 업무(계좌 이체, 재고 차감과 주문 생성의 원자적 처리)는 애초에 CouchDB의 철학과 맞지 않는다. 억지로 구현하려면 복잡한 보정 로직이 필요하고, 그 과정에서 MVCC의 이점이 사라진다.

CouchDB는 "뭘 해도 평균 이상인" DB가 아니다. 복제와 오프라인 동기화라는 명확한 강점 영역이 있고, 그 외의 영역에서는 대체재가 항상 더 낫다. 도입 전에 "이 강점이 우리 시스템에 실제로 필요한가"를 먼저 확인하는 게 가장 중요하다.
