---
title: DB 모델링
tags: [database, modeling, normalization, denormalization, erd, schema-design, jpa, ddl]
updated: 2026-04-07
---

# DB 모델링

## 개요

DB 모델링은 비즈니스 요구사항을 테이블 구조로 변환하는 작업이다. 개념 모델링(엔티티와 관계 정의) → 논리 모델링(속성과 키 결정) → 물리 모델링(실제 DDL 작성) 순서로 진행한다.

실무에서는 이 단계를 명확하게 구분하지 않는 경우가 많다. 요구사항을 받으면 ERD를 그리면서 동시에 테이블을 만드는 식으로 진행하는데, 이게 나중에 문제가 된다. 초기에 관계를 잘못 잡으면 서비스가 커진 뒤 테이블 구조를 바꾸기가 매우 어렵다.

## 정규화 (Normalization)

정규화는 데이터 중복을 제거하고 이상 현상(Anomaly)을 방지하기 위해 테이블을 분리하는 과정이다.

### 1NF (제1정규형)

한 컬럼에 하나의 값만 저장한다. 반복 그룹이나 다중 값을 허용하지 않는다.

```sql
-- 1NF 위반: 한 컬럼에 여러 값
CREATE TABLE orders (
    order_id BIGINT PRIMARY KEY,
    product_names VARCHAR(500)  -- "노트북,마우스,키보드" 이런 식으로 저장
);

-- 1NF 준수: 별도 테이블로 분리
CREATE TABLE orders (
    order_id BIGINT PRIMARY KEY
);

CREATE TABLE order_items (
    order_item_id BIGINT PRIMARY KEY,
    order_id BIGINT REFERENCES orders(order_id),
    product_name VARCHAR(100)
);
```

실무에서 1NF를 위반하는 대표적인 경우가 JSON 컬럼이다. MySQL 5.7 이후로 JSON 타입을 지원하면서 한 컬럼에 배열이나 객체를 넣는 경우가 늘었다. 검색이나 집계가 필요 없는 부가 정보(예: 사용자 설정값)는 JSON으로 넣어도 괜찮지만, WHERE 절이나 JOIN에 사용할 데이터라면 테이블을 분리해야 한다.

### 2NF (제2정규형)

1NF를 만족하면서, 기본키의 일부에만 종속되는 컬럼이 없어야 한다. 복합키를 사용할 때 발생하는 문제다.

```sql
-- 2NF 위반: student_name은 student_id에만 종속
CREATE TABLE enrollment (
    student_id BIGINT,
    course_id BIGINT,
    student_name VARCHAR(50),  -- student_id에만 종속 (부분 종속)
    grade CHAR(1),
    PRIMARY KEY (student_id, course_id)
);

-- 2NF 준수: 부분 종속 제거
CREATE TABLE students (
    student_id BIGINT PRIMARY KEY,
    student_name VARCHAR(50)
);

CREATE TABLE enrollment (
    student_id BIGINT REFERENCES students(student_id),
    course_id BIGINT,
    grade CHAR(1),
    PRIMARY KEY (student_id, course_id)
);
```

실무에서 복합키를 쓰면 2NF 위반이 자주 생긴다. JPA에서 `@IdClass`나 `@EmbeddedId`를 쓸 때 복합키에 종속되지 않는 컬럼을 같은 테이블에 넣는 실수가 잦다.

### 3NF (제3정규형)

2NF를 만족하면서, 이행적 종속(A → B → C)이 없어야 한다. 기본키가 아닌 컬럼이 다른 비키 컬럼을 결정하면 안 된다.

```sql
-- 3NF 위반: department_name은 department_id에 종속 (이행적 종속)
CREATE TABLE employees (
    employee_id BIGINT PRIMARY KEY,
    employee_name VARCHAR(50),
    department_id BIGINT,
    department_name VARCHAR(50)  -- department_id → department_name (이행적 종속)
);

-- 3NF 준수
CREATE TABLE departments (
    department_id BIGINT PRIMARY KEY,
    department_name VARCHAR(50)
);

CREATE TABLE employees (
    employee_id BIGINT PRIMARY KEY,
    employee_name VARCHAR(50),
    department_id BIGINT REFERENCES departments(department_id)
);
```

3NF 위반은 조회 성능을 위해 의도적으로 하는 경우가 있다. 주문 테이블에 주문 시점의 상품명을 저장하는 것이 대표적인 예다. 이건 반정규화가 아니라 비즈니스 요구사항이다—상품명이 나중에 바뀌더라도 주문 당시의 상품명을 보여줘야 하기 때문이다.

### BCNF (Boyce-Codd 정규형)

3NF를 만족하면서, 모든 결정자가 후보키여야 한다. 3NF에서 잡지 못하는 미묘한 이상을 처리한다.

```sql
-- BCNF 위반 예시: 수강 신청
-- 학생은 과목당 한 교수만 수강, 교수는 한 과목만 담당
-- {학생, 과목} → 교수 (OK)
-- 교수 → 과목 (교수가 결정자인데 후보키가 아님 → 위반)

CREATE TABLE course_assignment (
    student_id BIGINT,
    course_id BIGINT,
    professor_id BIGINT,
    PRIMARY KEY (student_id, course_id)
);

-- BCNF 준수: 테이블 분리
CREATE TABLE professor_course (
    professor_id BIGINT PRIMARY KEY,
    course_id BIGINT NOT NULL
);

CREATE TABLE student_professor (
    student_id BIGINT,
    professor_id BIGINT REFERENCES professor_course(professor_id),
    PRIMARY KEY (student_id, professor_id)
);
```

BCNF까지 신경 쓰는 경우는 실무에서 드물다. 대부분 3NF까지 맞추면 충분하다.

### 실무에서 정규화 판단 기준

정규화를 어디까지 할지는 테이블의 성격에 따라 다르다.

**3NF까지 반드시 맞춰야 하는 경우:**

- 마스터 데이터(회원, 상품, 카테고리 등): 여러 곳에서 참조하는 데이터는 중복이 생기면 수정할 때 정합성이 깨진다
- 금융/결제 관련 테이블: 데이터 정합성이 돈과 직결된다
- 자주 변경되는 데이터: 중복 저장된 데이터를 여러 곳에서 동시에 갱신해야 하면 UPDATE 누락이 생긴다

**2NF 정도에서 타협하는 경우:**

- 로그성 데이터: 한번 적재하면 수정하지 않는다. JOIN 비용을 줄이기 위해 필요한 정보를 함께 저장한다
- 대시보드/리포트용 집계 테이블: 조회 성능이 중요하다
- 이벤트 소싱 저장소: 이벤트 발생 시점의 스냅샷을 그대로 저장하는 것이 목적이다

## 반정규화 (Denormalization)

정규화된 테이블에서 조회 성능을 올리기 위해 의도적으로 중복을 허용하는 작업이다.

### 반정규화를 고려해야 하는 시점

반정규화는 인덱스 튜닝으로도 해결이 안 될 때 마지막 수단이다. 이 순서를 따른다:

1. 쿼리 자체를 개선한다 (불필요한 서브쿼리 제거, 실행 계획 확인)
2. 인덱스를 추가하거나 조정한다
3. 캐시(Redis 등)를 도입한다
4. 그래도 안 되면 반정규화를 검토한다

### 반정규화 방법과 트레이드오프

**컬럼 추가 (파생 컬럼)**

```sql
-- 주문 테이블에 총 금액 컬럼 추가
ALTER TABLE orders ADD COLUMN total_amount DECIMAL(15,2);

-- 주문 아이템이 변경될 때마다 갱신해야 한다
UPDATE orders o
SET total_amount = (
    SELECT SUM(price * quantity)
    FROM order_items oi
    WHERE oi.order_id = o.order_id
)
WHERE o.order_id = 12345;
```

장점: 매번 SUM 집계를 하지 않아도 된다. 주문 목록 조회 시 JOIN 없이 바로 금액을 보여줄 수 있다.

대가: INSERT/UPDATE/DELETE 시마다 파생 컬럼을 갱신해야 한다. 갱신을 빼먹으면 데이터가 어긋난다. 트리거를 걸거나 애플리케이션 레벨에서 반드시 같이 처리해야 하는데, 이 동기화 로직이 빠지는 버그가 생각보다 자주 발생한다.

**중복 테이블 (요약/집계 테이블)**

```sql
-- 일별 매출 집계 테이블
CREATE TABLE daily_sales_summary (
    summary_date DATE PRIMARY KEY,
    total_orders INT,
    total_revenue DECIMAL(15,2),
    avg_order_amount DECIMAL(10,2),
    updated_at TIMESTAMP
);

-- 배치로 집계 데이터를 갱신
INSERT INTO daily_sales_summary (summary_date, total_orders, total_revenue, avg_order_amount, updated_at)
SELECT
    DATE(created_at),
    COUNT(*),
    SUM(total_amount),
    AVG(total_amount),
    NOW()
FROM orders
WHERE DATE(created_at) = CURDATE() - INTERVAL 1 DAY
ON DUPLICATE KEY UPDATE
    total_orders = VALUES(total_orders),
    total_revenue = VALUES(total_revenue),
    avg_order_amount = VALUES(avg_order_amount),
    updated_at = NOW();
```

대가: 원본 데이터와 집계 데이터 사이에 시차가 발생한다. 실시간 정확성이 필요한 곳에는 쓸 수 없다.

**테이블 병합**

1:1 관계인 테이블을 합치는 경우다. 회원 테이블과 회원 상세 정보 테이블이 분리되어 있는데 항상 함께 조회한다면 합칠 수 있다.

```sql
-- 분리된 상태
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    email VARCHAR(100),
    name VARCHAR(50)
);

CREATE TABLE user_profiles (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
    bio TEXT,
    avatar_url VARCHAR(500),
    birth_date DATE
);

-- 병합
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    email VARCHAR(100),
    name VARCHAR(50),
    bio TEXT,
    avatar_url VARCHAR(500),
    birth_date DATE
);
```

대가: 한 테이블의 컬럼 수가 늘어난다. NULL이 많아지면 저장 공간이 낭비될 수 있고, 테이블 구조가 복잡해진다.

## ERD 설계 시 실수하기 쉬운 부분

### 다대다 관계와 중간 테이블

다대다 관계는 반드시 중간 테이블(연결 테이블)을 만들어야 한다. 이 중간 테이블 설계에서 실수가 많다.

```sql
-- 잘못된 접근: 중간 테이블에 PK가 없거나 복합키만 사용
CREATE TABLE user_role (
    user_id BIGINT REFERENCES users(user_id),
    role_id BIGINT REFERENCES roles(role_id),
    PRIMARY KEY (user_id, role_id)
);

-- 나중에 이 중간 테이블에 속성을 추가해야 하는 경우가 생긴다
-- 예: 역할 부여 일시, 부여한 관리자, 만료일 등
-- 복합키만 있으면 다른 테이블에서 참조하기 불편하다

-- 독립 PK를 추가하는 것이 확장에 유리하다
CREATE TABLE user_role (
    user_role_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    role_id BIGINT NOT NULL REFERENCES roles(role_id),
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    assigned_by BIGINT REFERENCES users(user_id),
    expires_at TIMESTAMP,
    UNIQUE (user_id, role_id)
);
```

중간 테이블에 독립 PK를 넣을지 복합키만 쓸지는 케이스에 따라 다르다. 단순 매핑(태그 연결 등)이면 복합키로 충분하다. 중간 테이블 자체에 속성이 붙거나 다른 테이블에서 참조해야 하면 독립 PK가 낫다.

### 상속 매핑 패턴

엔티티 간에 상속 관계가 있을 때 테이블로 매핑하는 방법이 세 가지 있다.

**단일 테이블 (Single Table Inheritance)**

```sql
CREATE TABLE payments (
    payment_id BIGINT PRIMARY KEY,
    dtype VARCHAR(31) NOT NULL,  -- 구분자
    amount DECIMAL(15,2) NOT NULL,
    -- 카드 결제 전용
    card_number VARCHAR(20),
    installment_months INT,
    -- 계좌이체 전용
    bank_code VARCHAR(10),
    account_number VARCHAR(30),
    -- 가상계좌 전용
    virtual_account_number VARCHAR(30),
    expiry_date TIMESTAMP
);
```

모든 하위 타입을 한 테이블에 넣는다. 조회가 빠르고 JOIN이 없다. 문제는 NULL 컬럼이 많아진다는 점이다. 카드 결제 행에는 bank_code, account_number가 NULL이다. 컬럼이 30~40개 넘어가면 관리가 힘들어진다.

**조인 테이블 (Joined Table / Table Per Class)**

```sql
CREATE TABLE payments (
    payment_id BIGINT PRIMARY KEY,
    amount DECIMAL(15,2) NOT NULL,
    payment_type VARCHAR(20) NOT NULL
);

CREATE TABLE card_payments (
    payment_id BIGINT PRIMARY KEY REFERENCES payments(payment_id),
    card_number VARCHAR(20) NOT NULL,
    installment_months INT
);

CREATE TABLE bank_transfer_payments (
    payment_id BIGINT PRIMARY KEY REFERENCES payments(payment_id),
    bank_code VARCHAR(10) NOT NULL,
    account_number VARCHAR(30) NOT NULL
);
```

NULL 컬럼이 없고 정규화된 구조다. 하위 타입이 추가되면 테이블만 하나 더 만들면 된다. 단점은 조회 시 항상 JOIN이 필요하다는 점이다. 결제 목록을 보여줄 때 모든 하위 테이블을 LEFT JOIN해야 한다.

**구체 테이블 (Table Per Concrete Class)**

```sql
CREATE TABLE card_payments (
    payment_id BIGINT PRIMARY KEY,
    amount DECIMAL(15,2) NOT NULL,
    card_number VARCHAR(20) NOT NULL,
    installment_months INT
);

CREATE TABLE bank_transfer_payments (
    payment_id BIGINT PRIMARY KEY,
    amount DECIMAL(15,2) NOT NULL,
    bank_code VARCHAR(10) NOT NULL,
    account_number VARCHAR(30) NOT NULL
);
```

각 하위 타입별로 독립 테이블을 만든다. 개별 타입 조회는 빠르지만, "전체 결제 목록"처럼 상위 타입 기준 조회를 하려면 UNION ALL을 써야 한다. 공통 컬럼 변경 시 모든 테이블을 수정해야 하는 것도 번거롭다.

**실무 선택 기준:**

- 하위 타입이 2~3개이고 타입별 고유 컬럼이 적으면 → 단일 테이블
- 하위 타입별 고유 컬럼이 많고, 하위 타입이 계속 추가될 가능성이 있으면 → 조인 테이블
- 하위 타입 간 공통 조회가 거의 없으면 → 구체 테이블

### Nullable 외래키 문제

외래키에 NULL을 허용하면 관계가 선택적(Optional)이 된다. 편해 보이지만 문제가 생기는 경우가 있다.

```sql
CREATE TABLE orders (
    order_id BIGINT PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),       -- NOT NULL: 회원만 주문 가능
    coupon_id BIGINT REFERENCES coupons(coupon_id),  -- NULL 허용: 쿠폰 없이 주문 가능
    delivery_id BIGINT REFERENCES deliveries(delivery_id)  -- NULL 허용: 아직 배송 생성 전
);
```

coupon_id처럼 비즈니스적으로 선택적인 관계는 nullable FK가 맞다. 하지만 delivery_id처럼 "아직 생성 전"이라서 NULL인 경우는 주의해야 한다. 주문 생성 후 배송 정보를 나중에 UPDATE하는 플로우가 되는데, 이러면 주문과 배송 사이에 데이터 정합성이 깨질 수 있다. 배송 생성을 빼먹으면 delivery_id가 영원히 NULL인 주문이 남는다.

이런 경우에는 nullable FK 대신 별도 매핑 테이블을 쓰거나, 애플리케이션 레벨에서 상태 검증을 넣는 것이 낫다.

```sql
-- 별도 매핑 테이블로 분리
CREATE TABLE order_deliveries (
    order_id BIGINT PRIMARY KEY REFERENCES orders(order_id),
    delivery_id BIGINT NOT NULL REFERENCES deliveries(delivery_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 테이블 설계 패턴

### 이력 테이블

데이터가 변경된 기록을 남겨야 할 때 사용한다. 가격 변경 이력, 상태 변경 이력, 회원 정보 변경 이력 등이 해당된다.

```sql
-- 상품 가격 이력
CREATE TABLE product_price_history (
    history_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    price DECIMAL(15,2) NOT NULL,
    changed_by BIGINT NOT NULL REFERENCES users(user_id),
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    change_reason VARCHAR(200)
);

-- 현재 가격 조회: 가장 최근 이력
SELECT price
FROM product_price_history
WHERE product_id = 100
ORDER BY changed_at DESC
LIMIT 1;
```

이력 테이블을 설계할 때 흔한 실수가 "현재 값"을 어디서 읽을지 정하지 않는 것이다. 위 예시처럼 이력 테이블에서 최신 값을 가져오면 매번 ORDER BY + LIMIT 쿼리를 해야 한다. 현재 값은 원본 테이블(products.price)에 두고, 이력 테이블은 변경 기록만 쌓는 구조가 낫다.

```sql
-- 원본 테이블에 현재 값 유지
CREATE TABLE products (
    product_id BIGINT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(15,2) NOT NULL  -- 현재 가격
);

-- 이력은 변경 기록만
CREATE TABLE product_price_history (
    history_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    old_price DECIMAL(15,2) NOT NULL,
    new_price DECIMAL(15,2) NOT NULL,
    changed_by BIGINT NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

이력 테이블은 데이터가 빠르게 쌓인다. 파티셔닝(월별, 연도별)을 미리 고려하고, 오래된 이력은 아카이빙 정책을 세워야 한다.

### 소프트 딜리트 (Soft Delete)

물리적으로 데이터를 삭제하지 않고 삭제 여부를 표시하는 패턴이다.

```sql
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    email VARCHAR(100) NOT NULL,
    name VARCHAR(50) NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP NULL
);

-- 삭제 처리
UPDATE users SET is_deleted = TRUE, deleted_at = NOW() WHERE user_id = 100;

-- 조회 시 항상 조건 추가
SELECT * FROM users WHERE is_deleted = FALSE;
```

소프트 딜리트의 문제점:

- **모든 쿼리에 WHERE 조건 추가**: 빠뜨리면 삭제된 데이터가 노출된다. 실수를 방지하려면 뷰를 만들거나 JPA의 `@Where` 어노테이션을 사용한다
- **유니크 제약 충돌**: email에 UNIQUE 제약이 있으면, 탈퇴한 사용자의 email로 재가입이 안 된다. `UNIQUE(email, is_deleted)` 같은 편법을 쓰기도 하는데 is_deleted가 FALSE인 행이 여러 개면 충돌한다

```sql
-- MySQL에서 소프트 딜리트 + 유니크 해결법
-- deleted_at을 유니크 조건에 포함시킨다
-- 활성 사용자는 deleted_at이 NULL이므로 유니크 보장
-- 삭제된 사용자는 deleted_at이 각각 다르므로 충돌 없음
ALTER TABLE users ADD UNIQUE INDEX uq_email_deleted (email, deleted_at);
```

- **데이터 무한 증가**: 삭제된 데이터가 계속 쌓인다. 일정 기간 이후에는 아카이브 테이블로 이동하거나 물리 삭제하는 배치가 필요하다

소프트 딜리트가 적합한 경우: 삭제 후 복구가 필요하거나, 삭제된 데이터를 참조하는 다른 테이블이 있는 경우(주문 내역에서 탈퇴한 회원 정보를 보여줘야 할 때).

필요 없는 경우: 로그 데이터, 임시 데이터처럼 복구할 필요가 없는 데이터는 물리 삭제가 낫다.

### 다형성 연관 (Polymorphic Association)

하나의 테이블이 여러 타입의 부모 테이블을 참조해야 하는 경우다. 댓글 테이블이 게시글, 사진, 동영상 어디에든 달릴 수 있는 구조가 대표적이다.

**안티패턴: 다형성 FK**

```sql
-- 안티패턴
CREATE TABLE comments (
    comment_id BIGINT PRIMARY KEY,
    target_type VARCHAR(20) NOT NULL,  -- 'POST', 'PHOTO', 'VIDEO'
    target_id BIGINT NOT NULL,          -- posts.post_id 또는 photos.photo_id 등
    content TEXT NOT NULL
);
```

target_id에 FK 제약을 걸 수 없다. 어떤 테이블을 참조하는지 DB 레벨에서 보장할 방법이 없다. 존재하지 않는 target_id가 들어가도 DB는 막지 못한다.

**대안 1: 중간 테이블 사용**

```sql
CREATE TABLE commentable (
    commentable_id BIGINT PRIMARY KEY AUTO_INCREMENT
);

CREATE TABLE posts (
    post_id BIGINT PRIMARY KEY,
    commentable_id BIGINT NOT NULL UNIQUE REFERENCES commentable(commentable_id),
    title VARCHAR(200)
);

CREATE TABLE photos (
    photo_id BIGINT PRIMARY KEY,
    commentable_id BIGINT NOT NULL UNIQUE REFERENCES commentable(commentable_id),
    url VARCHAR(500)
);

CREATE TABLE comments (
    comment_id BIGINT PRIMARY KEY,
    commentable_id BIGINT NOT NULL REFERENCES commentable(commentable_id),
    content TEXT NOT NULL
);
```

FK 제약을 유지할 수 있다. 단점은 댓글이 달린 대상이 게시글인지 사진인지 알려면 JOIN을 여러 번 해야 한다는 점이다.

**대안 2: 각 타입별 FK 컬럼**

```sql
CREATE TABLE comments (
    comment_id BIGINT PRIMARY KEY,
    post_id BIGINT REFERENCES posts(post_id),
    photo_id BIGINT REFERENCES photos(photo_id),
    video_id BIGINT REFERENCES videos(video_id),
    content TEXT NOT NULL,
    -- 하나만 NOT NULL이어야 한다
    CONSTRAINT chk_single_parent CHECK (
        (post_id IS NOT NULL)::INT +
        (photo_id IS NOT NULL)::INT +
        (video_id IS NOT NULL)::INT = 1
    )
);
```

FK 제약을 걸 수 있고, 어떤 대상의 댓글인지 바로 알 수 있다. 대상 타입이 추가될 때마다 컬럼을 추가해야 하는 것이 단점이다. 대상 타입이 3~4개 이하이고 자주 늘어나지 않는다면 이 방식이 실무에서 가장 다루기 쉽다.

## JPA/Spring 환경에서 엔티티와 DDL 간 괴리

### JPA가 생성하는 DDL을 그대로 쓰면 안 되는 이유

`spring.jpa.hibernate.ddl-auto=update`는 개발 환경 전용이다. 운영에서 이걸 쓰면 안 된다.

JPA가 자동 생성하는 DDL과 실제 운영 DDL 사이에는 차이가 많다.

```java
@Entity
@Table(name = "products")
public class Product {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal price;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "category_id")
    private Category category;
}
```

JPA가 생성하는 DDL:

```sql
CREATE TABLE products (
    id BIGINT NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(15,2) NOT NULL,
    category_id BIGINT,
    PRIMARY KEY (id)
);

ALTER TABLE products
    ADD CONSTRAINT FKxxx FOREIGN KEY (category_id) REFERENCES categories(id);
```

실제 운영에서 필요한 DDL:

```sql
CREATE TABLE products (
    id BIGINT NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(15,2) NOT NULL,
    category_id BIGINT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_products_category (category_id),
    INDEX idx_products_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 운영에서는 FK 제약을 안 거는 경우도 많다
-- 대량 데이터 삭제/마이그레이션 시 FK가 걸려 있으면 처리가 느려진다
```

차이점 정리:

- **인덱스**: JPA는 `@Index`를 명시하지 않으면 인덱스를 만들지 않는다. 조회 패턴에 맞는 인덱스는 직접 설계해야 한다
- **FK 제약**: 운영 환경에서는 FK 제약 없이 애플리케이션 레벨에서 정합성을 관리하는 곳이 많다. 대규모 데이터 처리 시 FK가 병목이 되기 때문이다
- **문자셋/콜레이션**: JPA가 지정하지 않는다. utf8mb4를 안 쓰면 이모지 저장이 안 된다
- **감사 컬럼**: created_at, updated_at은 JPA의 `@CreatedDate`, `@LastModifiedDate`로 관리할 수 있지만, DB 기본값(DEFAULT CURRENT_TIMESTAMP)도 함께 설정하는 것이 안전하다. 배치나 직접 SQL로 INSERT할 때 감사 컬럼이 NULL이 되는 것을 방지한다

### 엔티티 설계 시 주의할 점

```java
// 양방향 관계를 무분별하게 거는 실수
@Entity
public class Order {
    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL)
    private List<OrderItem> orderItems = new ArrayList<>();
}

@Entity
public class OrderItem {
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "order_id")
    private Order order;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_id")
    private Product product;
}

@Entity
public class Product {
    // 이건 필요 없는 경우가 많다
    // "이 상품으로 주문된 아이템 전체"를 엔티티에서 탐색할 일이 있는가?
    @OneToMany(mappedBy = "product")
    private List<OrderItem> orderItems;  // 불필요한 양방향
}
```

양방향 관계는 정말 필요한 경우에만 건다. "A에서 B 목록을 탐색할 일이 실제로 있는가?"를 기준으로 판단한다. 단방향으로 충분하면 단방향만 쓴다. Product에서 OrderItem 목록을 조회해야 하면 JPQL이나 QueryDSL로 직접 쿼리를 작성하는 것이 낫다.

## 운영 중 스키마 변경 시 주의사항

### 컬럼 추가

```sql
-- MySQL에서 큰 테이블에 컬럼 추가
-- MySQL 8.0부터 INSTANT 알고리즘을 지원한다 (테이블 끝에 추가하는 경우)
ALTER TABLE orders ADD COLUMN memo VARCHAR(500), ALGORITHM=INSTANT;

-- INSTANT가 안 되는 경우 (중간에 컬럼 추가, NOT NULL + DEFAULT 등)
-- INPLACE를 시도하고, 안 되면 pt-online-schema-change 사용
ALTER TABLE orders ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'PENDING', ALGORITHM=INPLACE, LOCK=NONE;
```

대형 테이블(수천만 건 이상)에 ALTER TABLE을 걸면 테이블 락이 걸릴 수 있다. 트래픽이 적은 시간대에 하거나, Percona의 pt-online-schema-change나 GitHub의 gh-ost 같은 온라인 DDL 도구를 사용한다.

### 컬럼 타입 변경

```sql
-- VARCHAR 길이를 늘리는 건 비교적 안전하다
ALTER TABLE users MODIFY COLUMN name VARCHAR(100);  -- 50 → 100

-- 타입 자체를 바꾸는 건 위험하다
-- INT → BIGINT: 테이블 리빌드가 필요할 수 있다
-- 대형 테이블이면 pt-online-schema-change를 사용한다
```

### 컬럼 삭제

운영 DB에서 컬럼 삭제는 단계적으로 한다.

1. 애플리케이션 코드에서 해당 컬럼 사용을 완전히 제거한다
2. 배포 후 일정 기간(1~2주) 모니터링한다
3. 문제가 없으면 그때 ALTER TABLE DROP COLUMN을 실행한다

코드 배포와 DDL을 동시에 하면 롤백이 어렵다. 코드를 먼저 배포해서 해당 컬럼 없이도 동작하는 상태를 만든 뒤에 컬럼을 삭제한다.

### NOT NULL 제약 추가

```sql
-- 기존 데이터에 NULL이 있으면 실패한다
-- 먼저 NULL 데이터를 처리한다
UPDATE orders SET memo = '' WHERE memo IS NULL;

-- 그 다음 NOT NULL 제약 추가
ALTER TABLE orders MODIFY COLUMN memo VARCHAR(500) NOT NULL DEFAULT '';
```

### 테이블/컬럼 이름 변경

이름 변경은 애플리케이션 코드와 동시에 바꿔야 하므로 위험하다. 안전한 방법:

1. 새 컬럼을 추가한다
2. 양쪽 컬럼에 데이터를 동기화하는 코드를 배포한다
3. 새 컬럼을 읽도록 코드를 전환한다
4. 충분히 모니터링한 뒤 이전 컬럼을 삭제한다

이 과정이 번거로워서 실무에서는 컬럼 이름 변경을 최대한 피한다. 처음에 이름을 잘 짓는 것이 중요한 이유다.

### Flyway/Liquibase로 마이그레이션 관리

스키마 변경은 반드시 마이그레이션 도구로 버전 관리한다. 직접 SQL을 실행하면 어떤 환경에 어떤 변경이 적용됐는지 추적이 안 된다.

```sql
-- Flyway 예시: V3__add_memo_to_orders.sql
ALTER TABLE orders ADD COLUMN memo VARCHAR(500);

-- 롤백 스크립트도 함께 작성한다
-- Flyway 유료 버전은 Undo Migration을 지원한다
-- 무료 버전에서는 다음 버전에서 롤백 DDL을 실행하는 식으로 처리한다
```

마이그레이션 파일 이름에 날짜를 포함시키면 충돌을 줄일 수 있다. 팀 규모가 크면 같은 버전 번호로 스크립트를 작성하는 일이 생긴다.

```
-- 버전 번호 대신 타임스탬프 사용
V20260407_001__add_memo_to_orders.sql
V20260407_002__add_index_on_orders_status.sql
```
