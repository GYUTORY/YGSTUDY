---
title: 직렬화(Serialization)와 역직렬화(Deserialization)
tags: [network, api]
updated: 2026-11-19
---

# 직렬화(Serialization)와 역직렬화(Deserialization)

## 개요

직렬화는 메모리에 존재하는 객체나 데이터 구조를 바이트 스트림으로 변환하는 과정이다. 반대로 바이트 스트림을 다시 원래의 객체로 복원하는 과정을 역직렬화라고 한다.

## 직렬화가 필요한 이유

메모리의 객체는 참조와 메타데이터를 포함하지만, 저장소나 네트워크는 단순한 바이트 시퀀스만 처리할 수 있다.

서로 다른 시스템 간에 데이터를 교환하려면 일관된 형식이 필요하다.

직렬화해 두면 프로그램이 종료되어도 데이터를 보존할 수 있다.

## 직렬화의 주요 용도

- 네트워크 통신: 클라이언트-서버 간 데이터 교환
- 데이터 저장: 파일 시스템이나 데이터베이스에 객체 저장
- 캐싱: 메모리나 디스크에 객체 캐시
- 분산 시스템: 마이크로서비스 간 데이터 전송
- 백업 및 복구: 시스템 상태 저장 및 복원

## 직렬화 방식의 분류

- 텍스트 기반: JSON, XML, YAML - 가독성이 좋고 디버깅이 용이
- 바이너리 기반: Protocol Buffers, MessagePack, BSON - 효율적이고 빠름
- 언어별: Java Serializable, Python pickle - 특정 언어에 최적화

웹 API는 JSON을 사용한다. 마이크로서비스 간 통신은 Protocol Buffers를 고려한다.

## 직렬화 방식

### JSON 직렬화

JSON의 특징:
- 가독성: 사람이 읽기 쉬운 텍스트 형식
- 호환성: 대부분의 프로그래밍 언어에서 지원
- 웹 친화적: HTTP API에서 널리 사용
- 구조화: 객체, 배열, 기본 타입을 모두 표현 가능

JSON 직렬화는 객체 분석, 타입 변환, 문자열 생성, 인코딩 네 단계로 진행된다.

1. 객체 분석: 메모리의 객체 구조를 파악
2. 타입 변환: 각 속성의 데이터 타입을 JSON 형식으로 변환
3. 문자열 생성: JSON 문법에 따라 문자열 생성
4. 인코딩: UTF-8로 인코딩하여 바이트 스트림 생성

#### JSON 직렬화의 장단점

JSON은 가독성이 뛰어나 디버깅이 쉽고, 웹 표준이라 널리 지원되며, 구조가 단순해 이해하기 쉽다. 반면 바이너리 형식보다 크기가 크고, 순환 참조를 처리하기 어렵고, 타입 정보가 손실된다(모든 숫자가 실수로 처리된다).

JavaScript에서 `JSON.stringify`와 `JSON.parse`로 객체를 직렬화하고 복원하는 예시다.

```javascript
// JavaScript
const user = { id: 1, name: "홍길동" };
const json = JSON.stringify(user);
// 결과: '{"id":1,"name":"홍길동"}'

// 역직렬화
const parsed = JSON.parse(json);
// 결과: { id: 1, name: "홍길동" }
```

순환 참조가 있는 객체는 JSON.stringify가 실패한다. 순환 참조를 제거하거나 커스텀 replacer 함수를 사용한다.

### 바이너리 직렬화

바이너리 직렬화의 특징:
- 효율성: 텍스트 형식보다 크기가 작고 처리 속도가 빠름
- 타입 안전성: 원본 데이터 타입을 정확히 보존
- 압축: 데이터를 압축하여 전송량 최소화
- 보안: 바이너리 형식으로 내용을 직접 읽기 어려움

바이너리 직렬화는 스키마 정의, 바이트 매핑, 순서 보장, 압축 네 단계로 진행된다.

1. 스키마 정의: 데이터 구조를 미리 정의
2. 바이트 매핑: 각 필드를 고정 크기 바이트로 변환
3. 순서 보장: 필드 순서를 엄격히 정의
4. 압축: 필요시 추가 압축 적용

#### 바이너리 직렬화의 장단점

바이너리 형식은 성능이 높고 크기가 작으며, 타입 정보를 완전히 보존하고, 네트워크 대역폭을 아낀다. 반면 가독성이 없어 디버깅이 어렵고, 스키마를 바꾸면 호환성 문제가 생기며, 플랫폼별 엔디언 문제가 생길 수 있다.

Protocol Buffers는 `.proto` 파일에 메시지 구조를 먼저 정의한다.

```protobuf
// .proto 파일
message User {
  int32 id = 1;
  string name = 2;
  string email = 3;
}
```

대용량 데이터나 실시간 통신에는 바이너리 직렬화가 유리하다. Protocol Buffers는 스키마 진화를 지원한다.

### 직렬화 방식별 비교

#### 텍스트 기반 vs 바이너리 기반

| 특성 | 텍스트 기반 (JSON/XML) | 바이너리 기반 (Protocol Buffers) |
|------|----------------------|--------------------------------|
| 가독성 | 높음 (사람이 읽기 쉬움) | 낮음 (바이너리 형식) |
| 크기 | 상대적으로 큼 | 작음 (압축 효율적) |
| 성능 | 보통 | 빠름 |
| 호환성 | 높음 (표준 형식) | 중간 (스키마 필요) |
| 디버깅 | 쉬움 | 어려움 |
| 타입 안전성 | 낮음 | 높음 |

#### 주요 직렬화 형식별 특징

##### JSON (JavaScript Object Notation)

- 웹 API의 표준 형식
- 가독성이 뛰어나 개발자 친화적
- 대부분의 언어에서 네이티브 지원

##### XML (eXtensible Markup Language)

- 구조화된 문서 교환에 적합
- 스키마 검증 가능 (XSD)
- 상대적으로 큰 크기

##### Protocol Buffers (protobuf)

- Google에서 개발한 바이너리 형식
- 높은 성능과 작은 크기
- 스키마 진화 지원

##### MessagePack

- JSON과 유사한 구조를 바이너리로 표현
- JSON보다 20-30% 작은 크기
- Java, Python, Go 등 주요 언어 지원

## 사용 사례

### 웹 API 통신

REST API에서의 직렬화:
- 요청 데이터: 클라이언트에서 서버로 전송할 데이터를 JSON으로 직렬화
- 응답 데이터: 서버에서 클라이언트로 반환할 데이터를 JSON으로 직렬화
- Content-Type: `application/json` 헤더로 데이터 형식 명시

클라이언트가 PUT 요청으로 사용자 정보를 보내고 서버가 결과를 응답하는 예시다.

```javascript
// 클라이언트 → 서버: 사용자 정보 업데이트 요청
fetch('/api/users/123', {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    userId: 123,
    name: "홍길동",
    email: "hong@example.com"
  })
});

// 서버 → 클라이언트: 업데이트 결과 응답
{
  "success": true,
  "message": "사용자 정보가 업데이트되었습니다",
  "updatedAt": "2025-12-06T10:30:00Z"
}
```

### 데이터 저장 및 캐싱

#### 파일 시스템 저장

- 설정 파일: 애플리케이션 설정을 JSON이나 YAML로 저장
- 로그 파일: 구조화된 로그 데이터를 JSON Lines 형식으로 저장
- 백업 데이터: 시스템 상태를 직렬화하여 백업 파일로 저장

#### 데이터베이스 저장

- NoSQL: MongoDB의 BSON, Redis의 직렬화된 객체
- 관계형 DB: JSON 컬럼에 구조화된 데이터 저장
- 캐시: 메모리 캐시에 객체를 직렬화하여 저장

설정 파일을 JSON으로 저장한 예시다.

```json
// config.json
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "myapp"
  },
  "features": {
    "enableLogging": true,
    "maxConnections": 100
  }
}
```

### 분산 시스템 통신

#### 마이크로서비스 간 통신

- 메시지 큐: RabbitMQ, Kafka에서 메시지를 직렬화하여 전송
- RPC: gRPC에서 Protocol Buffers 사용
- 이벤트 스트리밍: 이벤트 데이터를 JSON이나 Avro로 직렬화

Kafka 이벤트 메시지를 JSON으로 직렬화한 예시다.

```json
// Kafka 이벤트 메시지
{
  "eventId": "evt_12345",
  "eventType": "user.created",
  "timestamp": "2025-12-06T10:30:00Z",
  "data": {
    "userId": 123,
    "email": "user@example.com",
    "source": "web"
  }
}
```

## 운영 고려사항

### 성능 최적화

직렬화 성능은 형식 선택, 캐싱, 배치 처리로 개선한다.

1. 적절한 형식 선택
   - 대용량 데이터: 바이너리 형식 (Protocol Buffers, MessagePack)
   - 웹 API: JSON (가독성과 호환성)
   - 실시간 통신: 바이너리 (낮은 지연시간)

2. 캐싱 활용
   - 자주 직렬화되는 객체는 캐시에 저장
   - 메모리 사용량과 성능의 균형 고려
   - LRU 캐시로 메모리 효율성 확보

3. 배치 처리
   - 여러 객체를 한 번에 직렬화
   - 네트워크 왕복 횟수 감소
   - 스트리밍 처리로 메모리 사용량 최적화

### 에러 처리

직렬화할 때는 순환 참조, 타입 안전성, 데이터 검증을 확인해야 한다.

1. 순환 참조 처리
   - 객체가 자기 자신을 참조하는 경우 무한 루프 발생 가능
   - WeakSet을 사용하여 순환 참조 감지
   - 순환 참조 발견 시 특별한 값으로 대체

`WeakSet`으로 순환 참조를 감지하는 예시다.

```javascript
// 순환 참조 처리
function safeStringify(obj) {
  const seen = new WeakSet();
  return JSON.stringify(obj, (key, val) => {
    if (typeof val === 'object' && val !== null) {
      if (seen.has(val)) {
        return '[Circular]';
      }
      seen.add(val);
    }
    return val;
  });
}
```

2. 타입 안전성
   - 직렬화/역직렬화 시 데이터 타입 검증
   - 스키마 기반 검증으로 데이터 무결성 보장
   - 예외 상황에 대한 적절한 에러 처리

3. 데이터 검증
   - 필수 필드 존재 여부 확인
   - 데이터 타입 및 범위 검증
   - 비즈니스 로직 규칙 적용

## 참고

### 직렬화 형식별 성능 비교

| 형식 | 크기 | 속도 | 가독성 | 호환성 | 주요 용도 |
|------|------|------|--------|--------|-----------|
| JSON | 중간 | 보통 | 높음 | 높음 | 웹 API, 설정 파일 |
| XML | 큼 | 느림 | 높음 | 높음 | 문서 교환, 웹 서비스 |
| Protocol Buffers | 작음 | 빠름 | 낮음 | 중간 | 마이크로서비스, RPC |
| MessagePack | 작음 | 빠름 | 낮음 | 중간 | 캐싱, 실시간 통신 |
| BSON | 중간 | 보통 | 낮음 | 중간 | MongoDB, 바이너리 JSON |

### 용도별 권장 직렬화 형식

- 웹 API: JSON (가독성과 호환성)
- 실시간 게임: Protocol Buffers (낮은 지연시간)
- 설정 파일: JSON 또는 YAML (가독성)
- 로그 파일: JSON Lines (구조화된 로그)
- 마이크로서비스: Protocol Buffers (성능과 타입 안전성)
- 캐싱: MessagePack (효율적인 크기)

