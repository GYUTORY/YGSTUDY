---
title: 자연키
tags: [database, natural-key, primary-key, composite-key, foreign-key, on-update-cascade, iso-code, surrogate-key, legacy, business-identifier, key-space, postal-code, isbn]
updated: 2026-07-30
---

# 자연키

자연키(Natural Key)는 도메인 데이터 자체를 PK로 쓰는 방식이다. 이메일, ISO 국가 코드, 상품 바코드처럼 비즈니스 세계에서 이미 유일성이 보장된다고 가정하는 값이다.

자연키를 PK로 쓰는 결정 자체보다, 그 키가 정말로 "변하지 않는다"는 보장을 누가 어떻게 하는지가 핵심이다. 도메인 설계 초반에는 자명해 보이던 유일성이 시스템이 커지면서 흔들리는 경우가 많다.

## 키 공간

자연키의 유일성 보장 범위를 키 공간이라고 부른다. 기술적으로 표현 가능한 값의 집합과, 실제로 유일하다는 보장이 있는 값의 집합이 일치하지 않는 경우가 많다.

ISO 4217 통화 코드 `CHAR(3)`은 알파벳 3자 조합으로 표현 가능한 값이 수만 가지지만, ISO가 실제로 할당하고 관리하는 코드는 180개 안팎이다. ISO가 이 공간의 유일성을 직접 보증하므로 `KRW`가 다른 통화를 가리키는 일은 표준 위원회가 결정하지 않는 한 발생하지 않는다.

이메일 주소는 표현 가능한 값이 사실상 무한하지만 유일성을 보증하는 중앙 기관이 없다. 도메인 소유권이 만료되면 같은 주소를 다른 사람이 취득한다. 시스템 내에서 `UNIQUE` 제약으로 유일성을 관리하더라도 "이 이메일이 항상 같은 사람을 가리킨다"는 보장은 DB 밖에 있다.

키 공간 크기가 사용 범위에 비해 충분한지 확인한다. 4자리 숫자 사번은 최대 9,999명까지 수용한다. 조직이 성장해 자릿수를 늘리면 PK 컬럼 타입이 바뀌고, FK를 참조하는 모든 자식 테이블도 함께 수정해야 한다.

관리 주체가 외부 기관인지 내부인지 구분한다. 외부 기관이 키 공간을 관리하면 내부 정책 변경과 무관하게 유일성이 유지된다. 내부에서 관리하는 키는 정책 변경, 조직 개편, 시스템 통합 시 키 공간 자체가 흔들린다.

키 공간 자체가 재정의될 가능성도 있다. ISBN-10에서 ISBN-13으로의 전환, 한국 우편번호 6자리→5자리 개편이 여기에 해당한다. 외부 기관이 관리하는 키라도 그 기관이 기준을 바꾸면 기존 키 공간이 무효화된다.

## 자연키가 적합한 경우

자연키를 PK로 쓸 때 가장 중요한 조건은 두 가지다. 값이 바뀌지 않고, 외부 권위 기관이 유일성을 보증한다.

### ISO 코드류

국가 코드(ISO 3166-1 alpha-2), 통화 코드(ISO 4217), 언어 코드(ISO 639-1)는 이 조건을 모두 충족한다.

```sql
CREATE TABLE currencies (
    code          CHAR(3) NOT NULL,   -- KRW, USD, JPY
    name          VARCHAR(50) NOT NULL,
    decimal_places TINYINT NOT NULL DEFAULT 2,
    PRIMARY KEY (code)
);

CREATE TABLE exchange_rates (
    from_currency CHAR(3) NOT NULL,
    to_currency   CHAR(3) NOT NULL,
    rate          DECIMAL(18, 6) NOT NULL,
    updated_at    DATETIME NOT NULL,
    PRIMARY KEY (from_currency, to_currency),
    FOREIGN KEY (from_currency) REFERENCES currencies(code),
    FOREIGN KEY (to_currency)   REFERENCES currencies(code)
);
```

`exchange_rates`에서 `(from_currency, to_currency)` 복합 자연키가 PK다. 'KRW', 'USD' 같은 값은 ISO 표준이 유일성을 보증하고, 실제로 코드가 바뀐 사례가 거의 없다. FK 컬럼 자체에서 의미를 파악할 수 있으므로 `exchange_rate_id=7` 같은 대리키보다 가독성이 높다.

이 경우 대리키를 도입하면 오히려 복잡해진다. 통화 코드 조회 시 조인을 한 번 더 타야 하고, 환율 조회 API에서 `from_currency_id=3`이라는 값을 받으면 별도 조회 없이 의미를 알 수 없다.

IATA 공항 코드('ICN', 'LAX'), ITU 국가 전화 코드도 같은 이유로 자연키가 유효하다. 공통점은 외부 표준 기관이 유일성과 안정성을 관리한다는 점이다.

### 내부 코드 테이블

사내에서 정의하고 변경 권한이 명확한 코드 테이블도 자연키가 가능하다.

```sql
CREATE TABLE order_statuses (
    code        VARCHAR(20) NOT NULL,   -- PENDING, PAID, SHIPPED, CANCELLED
    description VARCHAR(100) NOT NULL,
    PRIMARY KEY (code)
);
```

애플리케이션 코드에 이 status 코드가 enum으로 하드코딩되어 있으면, 실제로 코드 값이 바뀌는 일은 거의 없다. 바꾸려면 코드 배포가 선행돼야 하기 때문이다.

## ON UPDATE CASCADE 한계

자연키에 `ON UPDATE CASCADE`를 걸면 부모 테이블의 키가 바뀔 때 자식 테이블의 FK 컬럼도 자동으로 업데이트된다. 선언적으로 편해 보이지만 실제 운영에서 몇 가지 상황에서 문제가 된다.

### 잠금 범위

MySQL InnoDB에서 `ON UPDATE CASCADE`는 부모 행 수정 시 자식 테이블의 해당 FK 컬럼 전체에 범위 잠금을 건다. 자식 테이블이 크면 잠금 범위가 넓어 다른 쓰기 작업이 대기 상태에 걸린다.

```sql
CREATE TABLE product_categories (
    code VARCHAR(20) NOT NULL,
    name VARCHAR(50) NOT NULL,
    PRIMARY KEY (code)
);

CREATE TABLE products (
    id            BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    category_code VARCHAR(20) NOT NULL,
    name          VARCHAR(200) NOT NULL,
    FOREIGN KEY (category_code) REFERENCES product_categories(code)
        ON UPDATE CASCADE
);
```

'ELEC' 카테고리에 상품이 50만 건이면 `product_categories.code`를 'ELEC'에서 'ELECTRONICS'로 바꾸는 UPDATE 한 번으로 50만 건 행에 잠금이 발생한다. 이 잠금이 해제되기 전까지 `products` 테이블에 INSERT나 UPDATE를 시도하는 다른 쿼리가 모두 대기한다.

### 연쇄 전파

FK 테이블이 여러 단계로 중첩되면 CASCADE가 연쇄적으로 실행된다.

```
product_categories → products → order_items
```

`product_categories.code`를 바꾸면 `products.category_code`가 바뀌고, `products.id`를 참조하는 `order_items`도 처리 대상이 된다. `order_items`에 `ON UPDATE CASCADE`가 없으면 UPDATE가 실패한다. 있으면 `order_items`까지 잠금이 전파된다. 테이블 구조를 모르는 상태에서 부모 키 하나를 바꿨다가 예상치 못한 테이블까지 영향이 미치는 상황이 생긴다.

### 이력 데이터 오염

변경 이력을 보관하는 테이블에서 CASCADE로 값이 바뀌면 과거 이력이 덮어써진다.

```sql
CREATE TABLE order_history (
    id            BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    order_id      BIGINT NOT NULL,
    category_code VARCHAR(20) NOT NULL,   -- 주문 당시 카테고리 코드
    changed_at    DATETIME NOT NULL
);
```

`category_code`에 `ON UPDATE CASCADE`가 걸려 있으면, 카테고리 코드가 'ELEC'에서 'ELECTRONICS'로 바뀔 때 과거 이력의 `category_code`도 바뀐다. "이 주문이 생성됐을 당시 어떤 카테고리였는가"를 이 테이블로는 알 수 없게 된다.

자연키에 `ON UPDATE CASCADE`는 키가 절대 바뀌지 않는 환경(ISO 코드류)에서만 안전하다. 조금이라도 변경 가능성이 있는 키라면 대리키로 분리하는 것이 낫다.

## 복합 자연키를 FK로 쓸 때 조인 복잡도

ISO 코드처럼 단순한 단일 컬럼 자연키는 FK 선언이 깔끔하다. 복합 자연키를 FK로 참조할 때부터 복잡도가 누적된다.

```sql
-- 제품과 버전의 조합을 복합 자연키로 관리
CREATE TABLE product_versions (
    product_code VARCHAR(20) NOT NULL,
    version      INT NOT NULL,
    description  TEXT,
    released_at  DATE NOT NULL,
    PRIMARY KEY (product_code, version)
);

CREATE TABLE version_reviews (
    id           BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    product_code VARCHAR(20) NOT NULL,
    version      INT NOT NULL,
    reviewer     VARCHAR(100) NOT NULL,
    score        TINYINT NOT NULL,
    FOREIGN KEY (product_code, version)
        REFERENCES product_versions(product_code, version)
);
```

조인 조건이 두 컬럼이다. 여기에 `version_reviews`를 참조하는 테이블이 생기면 복합 FK가 또 전달된다.

```sql
CREATE TABLE review_comments (
    id           BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    product_code VARCHAR(20) NOT NULL,
    version      INT NOT NULL,
    review_id    BIGINT NOT NULL,
    comment      TEXT,
    FOREIGN KEY (product_code, version)
        REFERENCES product_versions(product_code, version),
    FOREIGN KEY (review_id) REFERENCES version_reviews(id)
);
```

`product_code`와 `version`이 `review_comments`까지 퍼진다. 테이블이 늘어날수록 복합 FK가 계속 전달된다. 인덱스 크기가 커지고, INSERT 시 복합 FK 검증 비용도 증가한다. 조인 조건도 매번 두 컬럼을 써야 한다.

```sql
-- 복합 자연키로 조인할 때
SELECT pv.product_code, pv.version, AVG(vr.score) AS avg_score
FROM product_versions pv
JOIN version_reviews vr
    ON pv.product_code = vr.product_code
    AND pv.version = vr.version
WHERE pv.product_code = 'PROD-001'
GROUP BY pv.product_code, pv.version;
```

대리키를 쓰면 `version_id BIGINT` 하나가 복합 FK 전체를 대체한다.

```sql
CREATE TABLE product_versions (
    id           BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    product_code VARCHAR(20) NOT NULL,
    version      INT NOT NULL,
    released_at  DATE NOT NULL,
    UNIQUE INDEX uq_product_version (product_code, version)
);

CREATE TABLE version_reviews (
    id         BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    version_id BIGINT NOT NULL,
    reviewer   VARCHAR(100) NOT NULL,
    score      TINYINT NOT NULL,
    FOREIGN KEY (version_id) REFERENCES product_versions(id)
);
```

조인 조건도 단순해진다.

```sql
SELECT pv.product_code, pv.version, AVG(vr.score)
FROM product_versions pv
JOIN version_reviews vr ON pv.id = vr.version_id
WHERE pv.product_code = 'PROD-001'
GROUP BY pv.id;
```

복합 자연키가 PK인 경우, 단일 컬럼으로 FK를 선언할 수 없다. 그 구조가 두 단계 이상 전파될 수 있다면 대리키를 PK로 두고 복합 자연키를 UNIQUE 제약으로 내리는 것이 낫다.

## 복합 자연키의 키 공간 교차 문제

복합 자연키는 개별 컬럼이 각자의 범위에서 유일하더라도 조합의 유일성이 자동으로 보장되지 않는다. `(A, B)` 복합 키의 유효 키 공간은 비즈니스 규칙상 그 조합이 실제로 유일하다는 별도의 보장이 필요하다.

공급사 코드와 제품 SKU를 복합 자연키로 관리하는 경우를 보자.

```sql
CREATE TABLE supplier_products (
    supplier_code VARCHAR(10) NOT NULL,
    product_sku   VARCHAR(20) NOT NULL,
    price         DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (supplier_code, product_sku)
);
```

`supplier_code`는 공급사별로 유일하고 `product_sku`는 각 공급사가 자체 발급한다. 공급사 A가 공급사 B에 인수되면 두 회사의 SKU를 단일 `supplier_code` 아래로 통합해야 한다. 두 회사가 같은 제품군을 취급했다면 `product_sku`가 겹친다. 기존 `(supplier_code, product_sku)` 복합 키 공간이 충돌하고, PK 중복 오류가 발생한다.

지역 코드와 부서 번호를 복합 PK로 쓰는 경우도 같다.

```sql
CREATE TABLE departments (
    region_code VARCHAR(5) NOT NULL,
    dept_no     INT NOT NULL,
    dept_name   VARCHAR(100) NOT NULL,
    PRIMARY KEY (region_code, dept_no)
);
```

`dept_no`는 각 지역 내에서 순번이다. 두 지역이 합쳐지면 `region_code`가 하나로 통일된다. 두 지역에 각각 `dept_no = 1`이 있었다면 통합 후 충돌이 발생한다. 개별 컬럼은 각자의 키 공간에서 유일했지만, 조합의 유일성이 조직 개편으로 깨진다.

이 복합 키를 FK로 참조하는 테이블이 있으면 키 공간 변경이 전파된다.

```sql
CREATE TABLE employees (
    id          BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    region_code VARCHAR(5) NOT NULL,
    dept_no     INT NOT NULL,
    FOREIGN KEY (region_code, dept_no)
        REFERENCES departments(region_code, dept_no)
);
```

`departments`의 복합 PK를 재조합하면 `employees`의 복합 FK 값도 전부 바꿔야 한다. `departments`에 대리키를 PK로 두고 복합 자연키를 UNIQUE 제약으로 관리했다면, 재조합 작업은 `departments` 내부로 격리된다. `employees`에서 `dept_id BIGINT` 하나로 참조하는 구조라면 `dept_id` 값은 바꾸지 않아도 된다.

## 자연키+대리키 병행 설계

자연키와 대리키를 병행하는 패턴은 "대리키를 PK로, 자연키를 UNIQUE 제약으로" 구성한다.

```sql
CREATE TABLE currencies (
    id   SMALLINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    code CHAR(3) NOT NULL,
    name VARCHAR(50) NOT NULL,
    UNIQUE INDEX uq_code (code)
);
```

내부 조인과 FK는 `id`(SMALLINT)를 쓴다. 외부 API나 사람이 읽는 쿼리에서는 `code`('KRW', 'USD')를 쓴다.

### 대용량 조인에서 얻는 이점

```sql
CREATE TABLE exchange_rate_history (
    id               BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    from_currency_id SMALLINT NOT NULL,
    to_currency_id   SMALLINT NOT NULL,
    rate             DECIMAL(18, 6) NOT NULL,
    recorded_at      DATETIME NOT NULL,
    INDEX idx_from_to_time (from_currency_id, to_currency_id, recorded_at),
    FOREIGN KEY (from_currency_id) REFERENCES currencies(id),
    FOREIGN KEY (to_currency_id)   REFERENCES currencies(id)
);
```

`CHAR(3)` FK 대신 `SMALLINT` FK를 쓰면 인덱스 크기가 3분의 1로 줄어든다. 수억 건 환율 이력 테이블에서 복합 인덱스의 크기 차이가 버퍼 풀 효율에 영향을 준다.

조건 필터는 의미 있는 코드로 걸 수 있다.

```sql
SELECT r.rate, r.recorded_at
FROM exchange_rate_history r
JOIN currencies fc ON r.from_currency_id = fc.id
JOIN currencies tc ON r.to_currency_id = tc.id
WHERE fc.code = 'KRW' AND tc.code = 'USD'
ORDER BY r.recorded_at DESC
LIMIT 100;
```

`currencies` 테이블은 코드 수가 180개 안팎으로 작아 인메모리에 캐싱하거나 조인 비용이 거의 없다. 내부적으로 정수 FK로 조인하면서 조건 필터는 의미 있는 코드로 거는 구조다.

### 외부 연동 기준이 자연키일 때

타사 API가 통화 코드를 문자열로 주고받는 경우, `code` 컬럼이 연동 기준이다. 내부 PK를 외부에 노출하지 않아도 되고, 내부 PK가 변경돼도 외부 연동에 영향이 없다.

외부 시스템이 `from_currency=KRW&to_currency=USD` 형태로 요청을 보내면, `currencies` 테이블에서 코드로 조회해 `id`로 변환한 뒤 내부 처리를 한다. 외부 인터페이스와 내부 구조가 분리된다.

## 비즈니스 식별자를 자연키로 쓸 때 유일성 보장 문제

주문번호, 사번, ISBN처럼 비즈니스 세계에서 유일하다고 가정하는 식별자를 PK로 쓰면, 유일성 관리 책임이 애플리케이션으로 넘어온다.

### 주문번호

주문번호는 보통 날짜 + 순번 조합이다. 단일 서버라면 메모리 카운터나 DB 시퀀스로 처리할 수 있다. 서버가 두 대 이상이면 동시에 같은 번호를 생성할 수 있다.

```typescript
// 충돌 가능성이 있는 주문번호 생성
async generateOrderNo(date: Date): Promise<string> {
    const count = await this.orderRepository.countByDate(date);  // SELECT COUNT(*)
    const formatted = date.toISOString().slice(0, 10).replace(/-/g, '');
    return `ORDER-${formatted}-${String(count + 1).padStart(6, '0')}`;
}
// SELECT COUNT(*) 시점과 INSERT 사이에 다른 요청이 끼어들 수 있다
```

`UNIQUE` 제약이 PK라면 충돌 시 예외가 발생하고 재시도 로직이 필요하다. 재시도 로직이 또 충돌하면 무한 루프다.

실무에서 흔한 방식은 주문번호를 비즈니스 식별자로는 관리하되 PK로는 쓰지 않는 것이다.

```sql
CREATE TABLE orders (
    id       BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    order_no VARCHAR(30) NOT NULL UNIQUE,  -- 고객에게 보여주는 식별자
    user_id  BIGINT NOT NULL,
    total    DECIMAL(12, 2) NOT NULL
);
```

`order_no`는 DB 시퀀스나 별도 채번 서비스로 원자적으로 발급한다. 충돌 시 예외를 잡아 재생성하는 로직은 `order_no` 생성 레이어에만 존재하고, PK 충돌과 섞이지 않는다.

### 사번

사번은 회사 내에서 유일하다는 보장이 있지만 몇 가지 상황에서 문제가 된다.

퇴직자 사번을 신규 입사자에게 재발급하는 정책이 있으면 사번을 PK로 쓸 수 없다. 같은 사번에 급여 내역, 접근 로그, 성과 기록이 뒤섞인다. 두 회사가 합병하면 사번이 겹친다. PK 충돌이 발생하고 데이터 통합 시 기존 PK를 전부 바꿔야 한다. 4자리 사번을 8자리로 바꾸는 정책이 생기면 PK 전체가 바뀐다.

```sql
CREATE TABLE employees (
    id      BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    emp_no  VARCHAR(10) NOT NULL UNIQUE,  -- 사번은 UNIQUE로만
    name    VARCHAR(50) NOT NULL,
    dept_id BIGINT NOT NULL,
    hired_at DATE NOT NULL
);
```

### ISBN

ISBN-10은 10자리 숫자 코드로 도서 키 공간을 구성했다. 출판 산업이 성장하면서 표현 가능한 10억 개의 공간이 부족해졌고, 2007년부터 ISBN-13으로 전환됐다. 키 공간 크기 자체가 10자리에서 13자리로 확장된 케이스다.

ISBN-10을 PK로 쓰던 시스템은 이 전환에서 세 가지 문제를 마주했다. `CHAR(10)` PK를 `CHAR(13)`으로 바꿔야 하고, 그 FK를 참조하는 모든 자식 테이블의 컬럼 타입도 바꿔야 한다. 기존 ISBN-10을 ISBN-13으로 변환하는 로직(앞에 '978' 접두사 추가 + 체크 디짓 재계산)을 작성하고 변환 결과가 기존 데이터와 충돌하지 않는지 검증해야 한다. 2007년 이후 출간된 도서는 ISBN-10 자체가 존재하지 않는 경우도 생겼다.

```sql
-- ISBN-10 PK 기반 기존 구조
CREATE TABLE books_legacy (
    isbn10 CHAR(10) NOT NULL,
    title  VARCHAR(500) NOT NULL,
    PRIMARY KEY (isbn10)
);

-- 키 공간 전환 후 구조
CREATE TABLE books (
    id     BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    isbn13 CHAR(13) NOT NULL UNIQUE,
    isbn10 CHAR(10),         -- 구버전 호환용, NULL 가능
    title  VARCHAR(500) NOT NULL
);
```

`isbn10`에 `UNIQUE`를 걸지 않는다. 2007년 이후 발행 도서는 ISBN-10이 없어 NULL로 들어가는데, MySQL은 NULL을 UNIQUE 제약의 중복 판단에서 제외해 여러 행에 NULL이 허용된다. Oracle은 다르게 처리하므로 NULL 허용 컬럼에 UNIQUE를 거는 방식은 DB마다 동작이 달라진다.

### 한국 우편번호 개편

2015년 8월, 한국의 우편번호 체계가 6자리(구 우편번호, 예: `135-080`)에서 5자리(신 우편번호, 예: `06000`)로 전환됐다. 자릿수만 바뀐 것이 아니라 분류 기준이 지번 주소 기반에서 도로명 주소 기반으로 바뀌었다. 구 우편번호 하나가 신 우편번호 여러 개에 대응하거나, 여러 구 우편번호가 신 우편번호 하나로 통합되는 경우도 있었다. 1:1 변환이 불가능했다.

우편번호를 PK로 쓰던 배송 구역 테이블이 있었다면 이 전환이 PK 전체를 건드린다.

```sql
-- 구 우편번호 기반 기존 구조
CREATE TABLE delivery_zones (
    postal_code  CHAR(7) NOT NULL,   -- '135-080' 형식
    region_name  VARCHAR(100) NOT NULL,
    delivery_fee DECIMAL(8, 2) NOT NULL,
    PRIMARY KEY (postal_code)
);

CREATE TABLE orders (
    id          BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    postal_code CHAR(7) NOT NULL,
    address     VARCHAR(300) NOT NULL,
    FOREIGN KEY (postal_code) REFERENCES delivery_zones(postal_code)
);
```

신 우편번호로 전환하면 `CHAR(7)`이 `CHAR(5)`로 바뀐다. `delivery_zones.postal_code` PK와 `orders.postal_code` FK 컬럼 타입이 모두 바뀌고, 기존 주문 데이터의 구 우편번호를 신 우편번호로 변환하는 로직도 필요하다. 1:1 매핑이 안 되는 케이스는 처리 기준을 별도로 정해야 한다.

대리키를 PK로 분리했다면 우편번호 형식 변환은 `delivery_zones` 내부 문제로 격리된다.

```sql
CREATE TABLE delivery_zones (
    id           BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    postal_code  CHAR(5) NOT NULL UNIQUE,   -- 신 우편번호
    old_code     CHAR(7),                   -- 구 우편번호, NULL 가능
    region_name  VARCHAR(100) NOT NULL,
    delivery_fee DECIMAL(8, 2) NOT NULL
);

CREATE TABLE orders (
    id      BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    zone_id BIGINT NOT NULL,
    address VARCHAR(300) NOT NULL,
    FOREIGN KEY (zone_id) REFERENCES delivery_zones(id)
);
```

`orders.zone_id`는 구 우편번호를 신 우편번호로 바꾸는 작업과 무관하다. `delivery_zones`에 신 우편번호 기반 행을 추가하고, 필요한 경우 기존 주문의 `zone_id`를 새 행으로 업데이트하면 된다. 1:1 매핑이 안 되는 경우에도 `zone_id`가 NULL이 되는 것과 PK 충돌은 전혀 다른 문제다.

비즈니스 식별자는 값이 바뀌거나, 재사용되거나, 시스템 통합 시 충돌하는 경우가 생각보다 많다. 외부 기관이 키 공간을 관리하더라도 그 기관이 기준을 바꾸면 내부 시스템이 영향을 받는다. PK로 채택하기 전에 키 공간의 크기, 관리 주체, 변경 가능성을 명시적으로 확인해야 한다.

## 레거시 시스템에서 자연키로 굳어진 경우

오래된 시스템에서 자연키를 PK로 쓰고 수십 개 테이블이 FK로 참조하고 있다. 이 상태를 어떻게 처리하느냐는 상황에 따라 다르다.

### 그대로 유지하는 경우

자연키가 바뀌지 않고, 현재 구조에 실질적인 문제가 없다면 굳이 바꿀 필요가 없다. ISO 코드를 PK로 쓰는 코드 테이블, 변경이 일어나지 않는 사내 상품 코드 테이블이 여기에 해당한다. 마이그레이션 비용이 얻는 이득보다 크다.

### 단계적 전환

자연키가 바뀌기 시작하거나 시스템이 확장되면서 외부 연동이 필요한 상황이다. 핵심은 한 번에 PK를 교체하지 않는 것이다.

대리키 컬럼을 추가하고, 기존 FK 참조 테이블에도 새 컬럼을 추가한 뒤, 애플리케이션 코드를 먼저 전환하고 마지막에 구 컬럼을 제거한다. 자세한 절차는 `Surrogate_Key.md`의 마이그레이션 섹션에서 다룬다.

### 자연키 유지 + 대리키 신규 추가

PK를 바꾸는 대신 대리키 컬럼을 UNIQUE로 추가하고, 새로 생기는 테이블의 참조는 대리키로 연결하는 방식이다.

```sql
-- 기존 테이블의 PK는 유지
ALTER TABLE product_categories
    ADD COLUMN surrogate_id BIGINT NOT NULL AUTO_INCREMENT UNIQUE FIRST;

-- 신규 테이블은 surrogate_id로 참조
CREATE TABLE product_promotions (
    id          BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    category_id BIGINT NOT NULL,
    discount    DECIMAL(5, 2) NOT NULL,
    FOREIGN KEY (category_id) REFERENCES product_categories(surrogate_id)
);
```

기존 FK는 수정하지 않고 신규 테이블만 대리키를 쓰도록 한다. 레거시 코드에 영향을 최소화하면서 새 설계를 적용할 수 있다.

단점은 두 가지 참조 방식이 혼재한다는 점이다. 어느 테이블이 자연키로 참조하고 어느 테이블이 대리키로 참조하는지 명시하지 않으면 나중에 파악하기 어렵다.

### 애플리케이션 레벨 처리

트래픽이 높아 `pt-online-schema-change` 같은 도구도 쓰기 어렵고, 테이블 재작성이 불가한 상황이다.

```typescript
async changeCategoryCode(oldCode: string, newCode: string): Promise<void> {
    // ON UPDATE CASCADE 대신 애플리케이션에서 순서를 제어
    await this.dataSource.transaction(async (manager) => {
        await manager.query(
            'UPDATE products SET category_code = $1 WHERE category_code = $2',
            [newCode, oldCode]
        );
        // 이력 테이블은 의도적으로 건드리지 않음
        await manager.query(
            'UPDATE product_categories SET code = $1 WHERE code = $2',
            [newCode, oldCode]
        );
    });
}
```

`ON UPDATE CASCADE` 대신 애플리케이션에서 순서를 제어하면 히스토리 테이블을 건드리지 않거나, 테이블마다 다른 처리를 할 수 있다. 자동 CASCADE보다 코드가 길지만 각 테이블에 어떤 처리를 할지 명시할 수 있다.
