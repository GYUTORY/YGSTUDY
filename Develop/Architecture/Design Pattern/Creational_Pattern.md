---
title: 생성 패턴 (Creational Patterns)
tags: [design-patterns, javascript, nodejs, backend]
updated: 2026-08-24
---

# 생성 패턴 (Creational Patterns)

생성 패턴은 객체를 어떻게 만들지를 캡슐화한다. 호출하는 쪽이 구체 클래스를 직접 `new`로 찍어내지 않아도 되게 하는 것이 목적이다.

Node.js 백엔드에서 반복적으로 나타나는 상황들 — 데이터베이스 연결 관리, API 클라이언트 생성, 환경별 설정 분기, 복잡한 요청 객체 조립 — 은 대부분 생성 패턴 중 하나로 정리된다.

## 객체 생성이 문제가 되는 순간

### 매개변수 폭발

```javascript
// 9개 매개변수 생성자는 순서를 외울 수 없다
const user = new User(
    "홍길동",
    "hong@example.com",
    "010-1234-5678",
    "서울시 강남구",
    "개발자",
    true,
    false,
    "2023-01-01",
    "ACTIVE"
);
```

세 번째가 전화번호인지 주소인지 코드 리뷰에서 바로 보이지 않는다. 여섯 번째와 일곱 번째 불리언이 뒤바뀌어도 타입 에러가 없다. 런타임에서만 잘못된 동작으로 나타난다.

### 구체 클래스에 직접 의존

```javascript
class OrderService {
    async processOrder() {
        const dbConnection = new MySQLConnection(); // MySQL에 묶임
        const logger = new FileLogger();            // 파일 로깅에 묶임
        const emailService = new SendGridService(); // SendGrid에 묶임
    }
}
```

데이터베이스를 PostgreSQL로 바꾸거나 로깅 시스템을 교체할 때마다 `OrderService` 내부를 수정해야 한다. 테스트에서 실제 MySQL 없이는 `OrderService`를 인스턴스화할 수도 없다.

### 런타임 타입 분기의 확산

```javascript
function createPaymentProcessor(type) {
    if (type === "card") return new CardPaymentProcessor();
    if (type === "bank") return new BankPaymentProcessor();
    if (type === "kakao") return new KakaoPayProcessor();
    throw new Error('Unsupported payment type');
}
```

결제 수단이 추가될 때마다 이 분기문을 찾아서 고쳐야 한다. 같은 분기가 서비스 레이어와 어드민 레이어에 따로 복사되어 있으면, 새 카드사 추가 시 두 곳을 동시에 수정해야 한다.

---

## 패턴 목록

각 패턴의 상세 내용은 개별 파일을 참조한다.

### 1. Singleton Pattern (싱글톤 패턴)

애플리케이션 전체에서 단 하나의 인스턴스만 존재하도록 보장하는 패턴. 데이터베이스 연결 풀, Redis 클라이언트, 로깅 시스템, 전역 설정 관리에 쓴다.

→ 상세: [[Singleton_Pattern]]

### 2. Factory Method Pattern (팩토리 메서드 패턴)

객체 생성 인터페이스를 정의하되 어떤 클래스를 생성할지는 서브클래스가 결정하는 패턴. 결제 모듈, 알림 서비스, 데이터베이스 드라이버처럼 런타임에 타입이 결정되는 경우에 쓴다.

→ 상세: [[Factory Method]]

### 3. Abstract Factory Pattern (추상 팩토리 패턴)

관련 객체들의 집합을 일관성 있게 생성하는 패턴. 환경별 인프라 조합(DB + Cache + Logger), 결제 시스템 조합처럼 연관된 여러 객체를 함께 생성할 때 쓴다.

→ 상세: [[Abstract_Factory_Pattern]]

### 4. Builder Pattern (빌더 패턴)

복잡한 객체의 생성 과정을 단계별로 분리하는 패턴. HTTP 요청 구성, 동적 SQL 쿼리 생성, 이메일 메시지 구성처럼 선택적 매개변수가 많은 객체에 쓴다.

→ 상세: [[Builder_Pattern]]

### 5. Prototype Pattern (프로토타입 패턴)

기존 객체를 복제해 새 객체를 만드는 패턴. 복잡한 설정 객체를 기반으로 변형된 버전을 만들거나, 생성 비용이 큰 객체를 재사용할 때 쓴다.

→ 상세: [[Prototype_Pattern]]

---

## 패턴 선택 — 후회했던 경험 기준으로

### Singleton

전역에 하나만 있어야 하는 자원 — DB 커넥션 풀, Redis 클라이언트, 설정 객체 — 이 여기 해당된다.

Singleton 없이 운영하다가 후회한 상황은, 서버 초기화 코드 여러 곳에서 각자 `new RedisClient()`를 하고 있었을 때다. 커넥션이 요청마다 새로 열려 Redis 서버의 커넥션 수가 한도를 넘었고, 프로덕션에서 타임아웃이 터졌다. 개발 환경에서는 트래픽이 적어 보이지 않았다.

반대로 Singleton이 발목을 잡은 경우도 있다. 비즈니스 로직 내부에서 전역 상태를 직접 참조하면, 테스트 케이스가 실행 순서에 의존하게 된다. 앞 테스트가 남긴 상태가 다음 테스트에 영향을 준다. `beforeEach`에서 상태를 초기화하지 않으면 CI에서 랜덤하게 실패하는 테스트가 나온다.

### Factory Method

런타임 입력에 따라 다른 구현체를 만들어야 할 때다. 조건문 분기로 시작하되, 그 분기가 여러 파일에 복사·붙여넣기 되기 시작하면 Factory Method를 도입할 때다.

결제 모듈에서 이를 늦게 배웠다. 처음엔 `if/else`로 시작했고, 카드사가 3개에서 7개로 늘었을 때 같은 분기 로직이 서비스 레이어와 어드민 레이어에 따로 존재했다. 새 카드사 추가 시 두 곳을 동시에 수정해야 했고, 한 곳을 빠뜨린 적도 있다.

### Abstract Factory

환경(개발/스테이징/프로덕션)별로 DB, 캐시, 로거를 교체해야 하는 상황에서 맞다. 단, 초기 설계 비용이 크다.

Abstract Factory를 너무 일찍 도입한 적이 있다. "나중에 확장될 것 같다"는 이유였는데, 결국 그 팩토리가 추가된 환경 없이 1년을 갔다. 유지보수할 코드만 늘었다. 실제로 두 개 이상의 팩토리가 필요한 시점에 추가하는 편이 낫다.

### Builder

매개변수가 5개를 넘고 선택적 필드가 있으면 Builder를 쓴다. 이 기준이 생긴 건, 불리언 매개변수 두 개의 순서를 바꿔서 6시간을 디버깅한 뒤부터다. 코드 리뷰에서도, 타입 시스템에서도 잡히지 않았다. 런타임에서만 잘못된 동작으로 나타났다.

### Prototype

설정 객체의 기본값을 복제해서 환경별로 오버라이드하는 용도로 자주 쓴다. 문제는 중첩된 객체다. `Object.assign`은 shallow copy라서 중첩 객체를 공유하게 된다. 기본 설정을 수정했더니 파생된 설정 전부가 바뀐 경험이 있다. Prototype 패턴을 쓸 때는 deep clone 구현을 반드시 검증한다.

### 직접 `new`로도 되는 경우

생성 로직이 단순하고 구현체를 교체할 일이 없으면 패턴이 필요 없다. `{ id: 1, name: 'foo' }` 같은 단순 객체에 Builder를 붙이면 코드만 늘어난다. 패턴은 도구지 목표가 아니다.

---

## 패턴 간 비교

| 패턴 | 구현 비용 | 테스트 격리 | 타입 교체 | 주의사항 |
|------|----------|------------|----------|---------|
| Singleton | 구현 10줄 이하 | 테스트 간 상태 공유 — `beforeEach` 초기화 필요 | 인터페이스 없으면 교체 불가 | 전역 상태 의존 누적 |
| Factory Method | 서브클래스 1개 추가 | Mock 팩토리 주입으로 격리 가능 | 서브클래스 추가로 확장 | 서브클래스 수 비례 증가 |
| Abstract Factory | 인터페이스 3개 이상 설계 필요 | 팩토리 교체로 전체 Mock 가능 | 팩토리 교체로 패밀리 전환 | 초기 설계 오류 시 수정 범위 큼 |
| Builder | 메서드 체이닝 구현 | 필요 필드만 세팅해 독립 객체 생성 | 빌더 교체 또는 상속으로 확장 | 필드 추가 시 빌더도 수정 |
| Prototype | `clone()` 구현 필요 | 복사본이 원본과 독립적 | 제한적 | 중첩 객체 deep clone 누락 시 공유 버그 |

---

## 의사결정 트리

```
객체 생성이 필요한가?
├─ 전역적으로 하나만 존재해야 하는가?
│  ├─ 예 → Singleton Pattern
│  └─ 아니오 → 다음 질문
├─ 런타임에 타입이 결정되는가?
│  ├─ 예 → Factory Method Pattern
│  └─ 아니오 → 다음 질문
├─ 관련된 여러 객체를 함께 생성해야 하는가?
│  ├─ 예 → Abstract Factory Pattern
│  └─ 아니오 → 다음 질문
├─ 매개변수가 5개 이상이거나 선택적 필드가 많은가?
│  ├─ 예 → Builder Pattern
│  └─ 아니오 → 다음 질문
└─ 기존 객체를 복제해서 생성하는가?
   ├─ 예 → Prototype Pattern
   └─ 아니오 → 직접 생성
```