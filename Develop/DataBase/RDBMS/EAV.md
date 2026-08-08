---
title: EAV 패턴
tags: [database, rdbms]
updated: 2026-08-07
---

# EAV 패턴

EAV(Entity-Attribute-Value)는 세 개의 컬럼으로 임의의 속성을 저장하는 테이블 구조다. `entity_id`, `attribute_name`, `value` 형태로 각 속성 하나가 행 하나에 들어간다. 스키마를 미리 확정할 수 없는 데이터를 관계형 DB에 담아야 할 때 선택하는 구조다.

```sql
CREATE TABLE product_attributes (
  entity_id   BIGINT       NOT NULL,
  field_name  VARCHAR(100) NOT NULL,
  value       TEXT,
  PRIMARY KEY (entity_id, field_name)
);

-- 상품 ID 100번의 속성들
INSERT INTO product_attributes VALUES
  (100, 'color',    'red'),
  (100, 'size',     'XL'),
  (100, 'material', 'cotton'),
  (100, 'weight_g', '250');
```

이 구조의 핵심 문제는 SQL이 원래 제공하는 타입 보장, 제약 조건, JOIN 최적화가 모두 무력화된다는 것이다. 편의를 위해 DB가 주는 안전망을 스스로 걷어내는 선택이므로, 쓰기로 결정했다면 그 대가를 명확하게 알고 있어야 한다.

---

## 실제 사용 사례

### e-커머스 동적 속성

의류, 전자제품, 식품을 하나의 products 테이블에서 관리하면 각 카테고리마다 필요한 컬럼이 다르다. 의류는 색상·사이즈·소재가 필요하고, 전자제품은 전압·해상도·배터리 용량이 필요하다. 카테고리마다 테이블을 분리하면 카테고리가 늘어날 때마다 테이블이 추가된다. 단일 products 테이블에 모든 가능한 속성 컬럼을 두면 대부분의 행에서 NULL이 가득 찬 희소(sparse) 테이블이 된다.

이때 EAV를 써서 `product_attributes` 테이블에 속성을 동적으로 추가하는 방식을 선택한다. 카테고리별로 어떤 속성이 유효한지는 별도 메타 테이블에 정의한다.

```sql
CREATE TABLE attribute_definitions (
  category_id  INT          NOT NULL,
  field_name   VARCHAR(100) NOT NULL,
  field_type   VARCHAR(20)  NOT NULL, -- 'text', 'number', 'boolean', 'date'
  is_required  BOOLEAN      NOT NULL DEFAULT FALSE,
  PRIMARY KEY (category_id, field_name)
);
```

Shopify나 Magento 같은 상용 e-커머스 플랫폼 초기 버전이 이 구조를 사용했다. 나중에는 대부분 JSONB나 별도 카테고리 테이블로 전환했다.

### 설정 값 관리

애플리케이션 설정을 DB에 저장할 때 자주 나타나는 패턴이다. 기능 플래그, 결제 한도, 알림 임계값처럼 종류가 계속 늘어나는 설정을 단일 테이블에 담는다.

```sql
CREATE TABLE system_settings (
  setting_key   VARCHAR(200) PRIMARY KEY,
  setting_value TEXT,
  value_type    VARCHAR(20) NOT NULL, -- 'string', 'integer', 'boolean', 'json'
  updated_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT INTO system_settings VALUES
  ('payment.max_amount',      '5000000', 'integer',  NOW()),
  ('feature.dark_mode',       'true',    'boolean',  NOW()),
  ('email.retry_interval_sec','300',     'integer',  NOW());
```

설정 항목이 자주 바뀌고 코드 배포 없이 값만 수정해야 하는 경우에 쓴다. 다만 설정 항목이 수십 개를 넘지 않는다면 단순 key-value 구조가 낫고, 항목이 고정적이라면 일반 컬럼으로 두는 게 더 명확하다.

### 사용자 정의 필드

CRM이나 프로젝트 관리 도구처럼 각 팀이 자신만의 필드를 추가할 수 있어야 하는 경우다. 어떤 필드가 존재할지 서비스가 미리 알 수 없고, 사용자가 런타임에 스키마를 확장한다.

```sql
CREATE TABLE custom_field_definitions (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  tenant_id   BIGINT       NOT NULL,
  entity_type VARCHAR(50)  NOT NULL, -- 'lead', 'contact', 'deal'
  field_name  VARCHAR(100) NOT NULL,
  field_type  VARCHAR(20)  NOT NULL,
  UNIQUE (tenant_id, entity_type, field_name)
);

CREATE TABLE custom_field_values (
  entity_id   BIGINT       NOT NULL,
  field_def_id BIGINT      NOT NULL REFERENCES custom_field_definitions(id),
  value       TEXT,
  PRIMARY KEY (entity_id, field_def_id)
);
```

이 패턴에서는 field_name 직접 참조 대신 `field_def_id`로 정의 테이블을 FK로 연결한다. 필드 이름 변경이나 삭제 시 연관 값 처리를 DB 레벨에서 제어할 수 있다.

---

## value 컬럼 타입 처리

### 단일 TEXT 컬럼

가장 단순한 방법이다. 모든 값을 TEXT로 저장하고 애플리케이션에서 타입을 변환한다.

```sql
ALTER TABLE product_attributes
  ADD COLUMN value TEXT;
```

문제는 타입 불일치를 DB가 잡아주지 않는다는 것이다. `weight_g`에 `'two-fifty'`가 들어와도 DB는 정상 삽입한다. 숫자 비교나 날짜 범위 쿼리를 TEXT로 돌리면 `'9' > '100'`이 참이 되는 문자열 정렬 함정이 생긴다.

```sql
-- 위험한 쿼리: TEXT 컬럼을 숫자로 비교
SELECT entity_id FROM product_attributes
WHERE field_name = 'weight_g'
  AND value > '100';
-- '9', '90', '99' 모두 '100'보다 크다고 판단된다 (문자열 정렬)

-- CAST로 회피
SELECT entity_id FROM product_attributes
WHERE field_name = 'weight_g'
  AND CAST(value AS UNSIGNED) > 100;
```

CAST는 쿼리마다 수동으로 써야 하고, 인덱스를 탈 수 없다. CAST 결과에 인덱스를 걸려면 함수 기반 인덱스(MySQL 8.0+, PostgreSQL)를 써야 한다.

### 타입별 컬럼 분리

타입마다 별도 컬럼을 두는 방식이다. 어떤 타입의 값인지에 따라 해당 컬럼에 채우고 나머지는 NULL로 둔다.

```sql
CREATE TABLE product_attributes (
  entity_id    BIGINT       NOT NULL,
  field_name   VARCHAR(100) NOT NULL,
  value_text   TEXT,
  value_int    BIGINT,
  value_float  DECIMAL(15, 4),
  value_bool   BOOLEAN,
  value_date   DATE,
  PRIMARY KEY (entity_id, field_name)
);
```

타입 정확성은 올라가지만 관리 복잡도도 같이 올라간다. 애플리케이션이 어느 컬럼에 값을 넣고 어느 컬럼에서 읽을지 항상 알고 있어야 한다. `field_type` 메타 정보 없이는 어느 컬럼에 값이 있는지 쿼리만 보고 알 수 없다.

실무에서는 두 방식 모두 장기적으로 유지보수하기 어렵다. value 컬럼 구조가 복잡해질수록 JSONB 또는 문서 DB로의 이전이 현실적인 선택이 된다.

---

## FK 보장 불가와 orphan 데이터

EAV 구조에서 `entity_id`가 참조하는 부모 엔티티(예: `products.id`)에 FK를 거는 것이 정석이다.

```sql
ALTER TABLE product_attributes
  ADD CONSTRAINT fk_pa_product
  FOREIGN KEY (entity_id) REFERENCES products(id) ON DELETE CASCADE;
```

`ON DELETE CASCADE`를 걸면 상품이 삭제될 때 속성도 같이 삭제된다. 이 FK는 관리 가능하다.

문제는 `field_name`과 `attribute_definitions.field_name` 사이의 관계다. 정의 테이블에 없는 field_name이 값 테이블에 들어오는 것을 DB 레벨 FK로는 막을 수 없다. field_name은 문자열이고, 외래키는 동일 테이블의 같은 컬럼 타입을 참조해야 한다. 정의와 값이 다른 테이블에 분리돼 있으면 compound FK로 처리할 수 있지만, 정의 테이블 자체가 없는 경우(단순 key-value)에는 방법이 없다.

```sql
-- compound FK로 정의 테이블 연결
ALTER TABLE product_attributes
  ADD CONSTRAINT fk_pa_field_def
  FOREIGN KEY (category_id, field_name)
  REFERENCES attribute_definitions(category_id, field_name);
```

이 FK를 걸면 정의에 없는 field_name 삽입을 차단할 수 있다. 단, `category_id` 컬럼을 `product_attributes`에 함께 두어야 한다.

정의 테이블을 쓰지 않거나, field_name을 자유 텍스트로 허용하는 경우에는 FK로 orphan을 막을 수 없다. 잘못된 field_name 입력이 조용히 쌓인다. 이 경우 정기 배치로 정의에 없는 field_name을 탐지하고 알림을 보내는 방식으로 보완한다.

```sql
-- 정의에 없는 field_name 탐지
SELECT DISTINCT pa.field_name
FROM product_attributes pa
LEFT JOIN attribute_definitions ad
  ON pa.field_name = ad.field_name AND pa.category_id = ad.category_id
WHERE ad.field_name IS NULL;
```

부모 엔티티(`products`) 삭제 시 FK CASCADE 없이 방치하면 entity_id orphan이 쌓인다. `products.id = 100`이 사라져도 `product_attributes.entity_id = 100` 행은 남는다. FK를 걸거나 삭제 이벤트에 연동해서 함께 정리해야 한다.

---

## 쿼리 복잡도와 성능 저하

### 행-열 전환(Pivot)

일반 테이블에서 한 행으로 가져올 데이터를 EAV에서는 여러 행에서 모아야 한다. 상품의 색상, 사이즈, 소재를 한 번에 조회하려면 self-join이나 조건부 집계가 필요하다.

```sql
-- 방법 1: self-join (속성 개수만큼 JOIN)
SELECT
  p.id,
  color_attr.value   AS color,
  size_attr.value    AS size,
  material_attr.value AS material
FROM products p
LEFT JOIN product_attributes color_attr
  ON p.id = color_attr.entity_id AND color_attr.field_name = 'color'
LEFT JOIN product_attributes size_attr
  ON p.id = size_attr.entity_id AND size_attr.field_name = 'size'
LEFT JOIN product_attributes material_attr
  ON p.id = material_attr.entity_id AND material_attr.field_name = 'material'
WHERE p.id = 100;

-- 방법 2: 조건부 집계 (한 번 스캔, 속성 개수와 무관)
SELECT
  entity_id,
  MAX(CASE WHEN field_name = 'color'    THEN value END) AS color,
  MAX(CASE WHEN field_name = 'size'     THEN value END) AS size,
  MAX(CASE WHEN field_name = 'material' THEN value END) AS material
FROM product_attributes
WHERE entity_id = 100
GROUP BY entity_id;
```

속성 개수가 5개 이하라면 self-join이 읽기 쉽다. 속성이 많으면 조건부 집계가 낫다. 어느 방법이든 일반 컬럼 조회보다 쿼리가 복잡하고, 실행 계획도 단순하지 않다.

### 필터 쿼리

"색상이 빨간색이고 사이즈가 XL인 상품"을 찾으려면 조건마다 서브쿼리나 JOIN이 추가된다.

```sql
-- 두 속성을 동시에 만족하는 entity_id 조회
SELECT p.id, p.name
FROM products p
WHERE EXISTS (
  SELECT 1 FROM product_attributes
  WHERE entity_id = p.id AND field_name = 'color' AND value = 'red'
)
AND EXISTS (
  SELECT 1 FROM product_attributes
  WHERE entity_id = p.id AND field_name = 'size' AND value = 'XL'
);
```

필터 조건이 늘어날수록 EXISTS 절이 늘어난다. 각 EXISTS가 `product_attributes`를 별도로 스캔한다. 조건이 3~4개 이상이면 실행 시간이 크게 늘어난다.

`(entity_id, field_name, value)` 복합 인덱스가 있으면 각 EXISTS 내부 조회는 인덱스를 탄다. 하지만 가장 선별력이 높은 조건부터 필터링할 수 없으므로 옵티마이저가 최적 순서를 잡기 어렵다.

### 집계 쿼리 한계

속성 값의 합계나 평균을 구하는 것은 일반 컬럼보다 훨씬 복잡하다.

```sql
-- 카테고리별 평균 무게 계산
SELECT
  p.category_id,
  AVG(CAST(pa.value AS DECIMAL(10, 2))) AS avg_weight
FROM products p
JOIN product_attributes pa ON p.id = pa.entity_id
WHERE pa.field_name = 'weight_g'
  AND pa.value REGEXP '^[0-9]+(\.[0-9]+)?$'  -- 숫자 형식 검증
GROUP BY p.category_id;
```

숫자 형식이 아닌 값이 섞여 있으면 CAST 오류가 발생하므로 형식 검증 조건을 추가해야 한다. 이 쿼리는 `product_attributes` 전체에서 `weight_g`를 필터링 후 집계하므로, 해당 속성을 가진 상품이 많을수록 부담이 커진다.

---

## 인덱스 설계

기본 인덱스는 PK인 `(entity_id, field_name)`이다. 이 인덱스는 특정 엔티티의 모든 속성을 가져오거나 특정 엔티티의 특정 속성을 가져오는 조회에 효과적이다.

속성 값으로 엔티티를 검색하는 패턴(예: "color = 'red'인 상품 모두")에는 다른 인덱스가 필요하다.

```sql
-- field_name + value 검색 인덱스
CREATE INDEX idx_pa_field_value ON product_attributes (field_name, value(50));

-- 이 쿼리는 위 인덱스를 탄다
SELECT entity_id FROM product_attributes
WHERE field_name = 'color' AND value = 'red';
```

`value` 컬럼이 TEXT라면 전체 컬럼에 인덱스를 걸 수 없다. prefix 인덱스(`value(50)`)를 써야 하는데, 값이 50자를 넘어가면 prefix가 같은 다른 값과 구분이 안 된다. 긴 값 검색에는 인덱스 효과가 줄어든다.

숫자 속성을 범위로 자주 검색한다면 해당 속성만 별도 정규화 테이블로 빼는 것을 고려한다. EAV 전체를 유지하면서 자주 검색되는 속성만 별도 컬럼으로 denormalize하는 하이브리드 방식도 쓴다.

```sql
-- 자주 검색되는 속성을 products 테이블에 직접 컬럼으로 추가
ALTER TABLE products
  ADD COLUMN color VARCHAR(50),
  ADD COLUMN size  VARCHAR(20);

CREATE INDEX idx_products_color ON products(color);
CREATE INDEX idx_products_size ON products(size);

-- 기존 EAV 값에서 채우기
UPDATE products p
JOIN (
  SELECT entity_id, value AS color FROM product_attributes WHERE field_name = 'color'
) c ON p.id = c.entity_id
SET p.color = c.color;
```

이 방식은 쓰기 경로에서 두 곳을 동시에 갱신해야 하는 부담이 생기지만, 읽기 성능을 대폭 개선한다.

---

## 대안과 선택 기준

### PostgreSQL JSONB

스키마를 미리 정의할 수 없다는 점에서 JSONB는 EAV의 직접적인 대안이다. 한 컬럼에 임의의 구조를 저장하면서도 GIN 인덱스를 통한 빠른 조회, JSON 연산자를 통한 값 추출이 가능하다.

```sql
ALTER TABLE products ADD COLUMN attributes JSONB;

-- 값 삽입
UPDATE products SET attributes = '{"color": "red", "size": "XL", "weight_g": 250}'
WHERE id = 100;

-- 특정 속성 조회
SELECT id, attributes->>'color' AS color FROM products WHERE id = 100;

-- 속성으로 필터링 (GIN 인덱스 활용)
CREATE INDEX idx_products_attributes ON products USING GIN (attributes);

SELECT id FROM products WHERE attributes @> '{"color": "red", "size": "XL"}';
```

EAV와 비교하면 쿼리가 단순하고, 피벗 변환 없이 행 단위로 데이터를 다룬다. GIN 인덱스 덕에 JSON 내부 값 검색도 인덱스를 탄다.

JSONB의 단점은 컬럼 단위 타입 보장이 없고, 스키마 유효성 검증이 JSON Schema나 `CHECK` 제약으로만 가능하다는 것이다. 중첩 구조가 복잡해지면 쿼리 가독성도 나빠진다.

MySQL 5.7+ JSON 타입도 비슷한 기능을 제공하지만, PostgreSQL JSONB만큼 성숙한 인덱싱 지원은 없다. MySQL JSON 컬럼의 경우 생성 컬럼(generated column)으로 특정 경로 값을 추출해 인덱스를 거는 방식을 쓴다.

```sql
-- MySQL: JSON 경로에 인덱스 걸기
ALTER TABLE products
  ADD COLUMN color_extracted VARCHAR(50)
  GENERATED ALWAYS AS (attributes->>'$.color') STORED;

CREATE INDEX idx_products_color ON products(color_extracted);
```

### 문서 DB

MongoDB, DynamoDB처럼 스키마 없이 문서를 저장하는 DB는 동적 속성에 특화돼 있다. 각 문서가 자체 구조를 가지므로 EAV 변환 없이 자연스럽게 저장한다.

관계형 DB를 이미 쓰고 있는데 일부 엔티티만 동적 속성이 필요한 경우, 전체 아키텍처를 바꾸는 비용 대신 JSONB나 EAV로 해결하는 게 현실적이다. 동적 속성이 시스템의 핵심 패턴이고, 관계형 특성(복잡한 조인, 트랜잭션 의존)이 없다면 문서 DB가 더 자연스럽다.

### 스파스 컬럼

SQL Server에는 NULL 값 저장을 최적화하는 SPARSE 컬럼 옵션이 있다. NULL이 많은 희소 테이블의 스토리지를 줄여준다. 카테고리마다 컬럼이 다른 문제를 테이블 분리 없이 처리할 수 있다.

MySQL과 PostgreSQL에는 동일한 기능이 없다. 대신 상속 테이블(PostgreSQL TABLE INHERITS) 또는 조인 테이블 방식으로 카테고리별 속성을 분리한다.

### 선택 기준

속성 종류가 고정돼 있고 100개 미만이라면 일반 컬럼이 낫다. NULL이 많아도 스토리지 낭비가 크지 않고 쿼리가 훨씬 단순하다.

속성이 자주 추가·변경되고 배포 없이 스키마를 변경해야 한다면, PostgreSQL 환경에서는 JSONB가 EAV보다 관리하기 쉽다. MySQL 환경에서는 EAV와 JSONB 중 쿼리 패턴에 따라 선택한다. 범위 조건이나 집계가 잦으면 EAV로 타입별 컬럼을 두는 방식이 낫고, 단순 key-value 조회가 주라면 JSON 컬럼이 단순하다.

사용자 정의 필드처럼 테넌트마다 스키마가 달라야 하고 필드 정의를 관리해야 한다면 EAV가 현실적이다. JSONB로도 처리할 수 있지만 필드 메타 정보(라벨, 타입, 필수 여부)를 JSONB 안에 담으면 쿼리가 복잡해진다.

---

## 실무 트러블슈팅

### 잘못된 field_name 입력

애플리케이션이 field_name을 문자열로 받아 그대로 저장하면 타이포가 조용히 쌓인다. `color`와 `colour`, `weight_g`와 `weight_gram`이 다른 속성으로 저장된다. DB는 이 차이를 알 수 없다.

방어 방법은 두 가지다. 허용 field_name 목록을 `attribute_definitions` 테이블에 관리하고, 애플리케이션이 삽입 전에 목록에 있는지 확인하는 것이다. 두 번째는 compound FK를 써서 DB 레벨에서 차단하는 것이다. 두 방법 중 하나를 반드시 적용해야 한다. 아무 것도 없으면 시간이 지날수록 데이터 품질이 나빠지고 정리 비용이 커진다.

```typescript
async setProductAttribute(
  productId: number,
  categoryId: number,
  fieldName: string,
  value: string,
): Promise<void> {
  const definition = await this.attrDefRepo.findOne({
    where: { categoryId, fieldName },
  });

  if (!definition) {
    throw new BadRequestException(`Unknown field: ${fieldName}`);
  }

  await this.productAttrRepo.upsert(
    { entityId: productId, fieldName, value },
    ['entityId', 'fieldName'],
  );
}
```

### 타입 불일치

value TEXT 컬럼에 숫자 형식이 아닌 값이 들어오면 집계나 비교 쿼리에서 오류가 난다. `value_type` 컬럼으로 기대 타입을 관리하고, 삽입 시 타입을 검증한다.

```typescript
function validateValue(value: string, fieldType: string): void {
  switch (fieldType) {
    case 'integer':
      if (!/^-?\d+$/.test(value)) {
        throw new BadRequestException(`${value} is not a valid integer`);
      }
      break;
    case 'decimal':
      if (isNaN(parseFloat(value))) {
        throw new BadRequestException(`${value} is not a valid decimal`);
      }
      break;
    case 'boolean':
      if (value !== 'true' && value !== 'false') {
        throw new BadRequestException(`${value} is not a valid boolean`);
      }
      break;
    case 'date':
      if (isNaN(Date.parse(value))) {
        throw new BadRequestException(`${value} is not a valid date`);
      }
      break;
  }
}
```

DB 레벨 CHECK 제약으로도 일부 유효성 검사를 걸 수 있다. 단, TEXT 컬럼에 숫자 형식인지 확인하는 정규식 CHECK를 DB별로 지원 여부가 다르므로 확인이 필요하다.

### 인덱스 미스

`product_attributes` 테이블에 데이터가 수백만 건 쌓인 후 특정 속성값으로 검색하는 쿼리가 느려지는 상황이 생긴다. `(entity_id, field_name)` PK만 있고 `(field_name, value)` 인덱스가 없으면 field_name 조건이 있는 쿼리도 인덱스를 제대로 타지 않는다.

```sql
-- 실행 계획 확인
EXPLAIN SELECT entity_id FROM product_attributes
WHERE field_name = 'color' AND value = 'red';

-- type이 ALL(풀스캔)이면 인덱스 추가
CREATE INDEX idx_pa_field_value ON product_attributes (field_name, value(50));

-- 인덱스 추가 후 다시 확인
EXPLAIN SELECT entity_id FROM product_attributes
WHERE field_name = 'color' AND value = 'red';
```

전체 테이블 크기가 크면 인덱스 추가 자체가 운영 중 부하를 줄 수 있다. MySQL은 `pt-online-schema-change`나 `gh-ost`, PostgreSQL은 `CREATE INDEX CONCURRENTLY`를 써서 락 없이 인덱스를 추가한다.

속성 값이 분포가 고른 경우(예: 색상이 30가지)에는 `(field_name, value)` 인덱스가 잘 동작한다. 값 분포가 치우쳐 있거나(예: 99%가 NULL) 카디널리티가 낮으면 인덱스를 타도 풀스캔과 성능 차이가 크지 않다. 부분 인덱스를 써서 특정 field_name에 한정한 인덱스를 거는 방법도 있다.

```sql
-- color 속성만 대상으로 한 부분 인덱스
CREATE INDEX idx_pa_color ON product_attributes (value)
WHERE field_name = 'color';
```

이 인덱스는 `field_name = 'color'` 조건을 포함한 쿼리에서만 동작하고, 크기가 전체 인덱스보다 훨씬 작아서 메모리에 올라가기 쉽다.
