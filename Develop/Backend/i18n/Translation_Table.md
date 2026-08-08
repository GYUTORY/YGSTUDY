---
title: 번역 테이블(EAV) 심화
tags: [backend, database, architecture, microservices]
updated: 2026-08-07
---

# 번역 테이블(EAV) 심화

번역 테이블 패턴의 기본 구조와 ORM 매핑, N+1 해결법은 [i18n DB 스키마 설계](i18n_Schema_Design.md)에서 다룬다. EAV 패턴 자체의 구조, 타입 처리 문제, 인덱스 설계, JSONB 대안 비교는 [EAV 패턴](../../DataBase/RDBMS/EAV.md)에서 다룬다. 이 문서는 그 내용과 겹치지 않는 영역을 다룬다. 단일 공유 번역 테이블 vs 엔티티별 분리 설계 비교, 데이터 규모 확장 시의 파티셔닝·아카이빙, 번역 워크플로우 상태 관리 스키마 상세 구현, 번역팀과의 CSV/Excel 일괄 작업 패턴, 번역 메모리와 중복 번역 제거, 마이크로서비스 환경에서 번역 테이블 위치 결정이 이 문서의 범위다.

## 일반 EAV와 번역 특화 EAV

[EAV 패턴](../../DataBase/RDBMS/EAV.md)의 핵심 문제는 `attribute_name`이 런타임에 결정된다는 것이다. 어떤 속성이 들어올지 미리 알 수 없어서 정의 테이블을 별도로 두고, `value` 타입을 애플리케이션이 전담해서 처리한다. 숫자 비교를 TEXT로 돌릴 때의 문자열 정렬 함정, 타입별 컬럼 분리 시의 관리 복잡도, 허용되지 않은 `field_name` 입력을 막기 위한 컴파운드 FK 설계가 모두 `attribute_name`이 동적이기 때문에 생기는 문제다.

번역 테이블에서 EAV를 쓸 때는 이 동적성의 범위가 다르다. 단일 공유 번역 테이블 `(entity_type, entity_id, locale, field_name, content)`에서 실제로 변동하는 축은 `locale` 하나다. `field_name`은 엔티티 타입마다 고정된다. 상품이라면 항상 name·description·short_desc 중 하나고, 카테고리라면 name뿐이다. `content`는 언제나 TEXT라서 타입 처리 문제 자체가 없다.

엔티티별 번역 테이블로 분리하면 `field_name`이 아예 컬럼이 되므로 일반 EAV의 `field_name` 오입력 문제도 사라진다. `color`와 `colour`가 다른 속성으로 쌓이는 상황이 스키마 레벨에서 차단된다.

공유 번역 테이블을 쓸 때는 달라지지 않는 문제가 있다. FK 보장 불가와 orphan 데이터가 그렇다. `entity_id`가 어느 테이블을 참조하는지 DB가 모르므로 삭제된 엔티티의 번역 행이 orphan으로 남는다. 이 부분은 번역 특화 설계라고 해서 해결되지 않는다.

---

## 단일 공유 번역 테이블 vs 엔티티별 분리

서비스 초기 번역 테이블 설계에서 첫 번째 결정이다. 상품(product), 카테고리(category), 브랜드(brand)처럼 번역이 필요한 엔티티가 여러 개일 때, 하나의 번역 테이블을 공유할지 엔티티별로 따로 둘지를 정해야 한다.

### 단일 공유 번역 테이블

EAV 구조를 한 단계 더 일반화한 형태다. `entity_type` 컬럼으로 어떤 엔티티의 번역인지 구분한다.

```sql
CREATE TABLE translations (
    id          BIGINT       PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    entity_type VARCHAR(50)  NOT NULL,
    entity_id   BIGINT       NOT NULL,
    locale      VARCHAR(10)  NOT NULL,
    field_name  VARCHAR(100) NOT NULL,
    content     TEXT         NOT NULL,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (entity_type, entity_id, locale, field_name)
);

CREATE INDEX idx_translations_entity
    ON translations (entity_type, entity_id, locale);
```

저장 예시:

```
entity_type | entity_id | locale | field_name  | content
------------|-----------|--------|-------------|-------------------
product     | 1         | ko     | name        | 무선 이어폰
product     | 1         | ko     | description | 고음질 블루투스 이어폰
product     | 1         | en     | name        | Wireless Earphone
category    | 5         | ko     | name        | 음향기기
brand       | 2         | ko     | name        | 삼성
```

전체 번역 현황을 단일 쿼리로 뽑을 수 있다는 것이 이 방식의 실질적인 장점이다.

```sql
-- 엔티티 타입별, 언어별 번역 현황
SELECT
    entity_type,
    locale,
    COUNT(*) AS field_count
FROM translations
GROUP BY entity_type, locale
ORDER BY entity_type, locale;

-- 특정 언어로 번역되지 않은 상품 목록
SELECT p.id, p.sku
FROM products p
WHERE NOT EXISTS (
    SELECT 1 FROM translations t
    WHERE t.entity_type = 'product'
      AND t.entity_id = p.id
      AND t.locale = 'ko'
);
```

이 방식의 핵심 문제는 FK 보장이 DB 레벨에서 불가능하다는 점이다. `entity_id`가 products 테이블의 FK인지, categories 테이블의 FK인지 DB가 모른다. 상품이 삭제되어도 번역 행이 orphan으로 남는다. 애플리케이션 레이어에서 삭제 이벤트를 받아 번역 행을 수동으로 정리해야 한다.

쿼리에 항상 `entity_type` 조건이 붙는다는 것도 문제다. 인덱스 설계가 복합 4컬럼(`entity_type, entity_id, locale, field_name`)이 되어 관리가 복잡해진다. 번역 가능한 필드가 엔티티마다 다른데(상품은 name·description·short_desc, 카테고리는 name만) 이 정보를 스키마에서 강제할 방법이 없다. 잘못된 `field_name` 값이 들어와도 DB 레벨에서 막을 수 없다.

### 엔티티별 번역 테이블 분리

각 엔티티마다 전용 번역 테이블을 만든다.

```sql
CREATE TABLE product_translations (
    product_id  BIGINT       NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    locale      VARCHAR(10)  NOT NULL,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    short_desc  VARCHAR(500),
    PRIMARY KEY (product_id, locale)
);

CREATE TABLE category_translations (
    category_id BIGINT       NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    locale      VARCHAR(10)  NOT NULL,
    name        VARCHAR(100) NOT NULL,
    PRIMARY KEY (category_id, locale)
);
```

FK로 참조 무결성이 보장된다. `ON DELETE CASCADE`를 걸면 상품 삭제 시 번역 행이 자동으로 삭제된다. 번역 가능한 필드가 테이블 컬럼으로 고정되어 있어서 `field_name` 오입력 같은 문제가 없다. 쿼리도 단순하다.

단점은 엔티티 수가 많아지면 테이블 수가 늘어난다는 것이다. 전체 번역 현황을 집계하려면 `UNION ALL`이 필요하다.

```sql
-- 전체 번역 현황 (엔티티별 분리 방식)
SELECT 'product'  AS entity_type, locale, COUNT(*) AS cnt
FROM product_translations
GROUP BY locale
UNION ALL
SELECT 'category', locale, COUNT(*)
FROM category_translations
GROUP BY locale
UNION ALL
SELECT 'brand',    locale, COUNT(*)
FROM brand_translations
GROUP BY locale;
```

### 선택 기준

| 기준 | 단일 공유 테이블 | 엔티티별 분리 |
|---|---|---|
| FK 보장 | 불가 | ON DELETE CASCADE 가능 |
| 번역 가능 필드 강제 | 불가 | 컬럼으로 강제 |
| 전체 현황 집계 | 단일 쿼리 | UNION ALL 필요 |
| 엔티티별 조회 | WHERE entity_type 조건 필수 | 단순 |
| 스키마 관리 | 테이블 1개 | 엔티티당 1개 |
| ORM 매핑 | 복잡 | 자연스러움 |

번역 가능한 엔티티가 2~5개 수준이면 엔티티별 분리가 맞다. FK 보장과 컬럼 강제라는 장점이 테이블 수 증가 단점보다 크다.

엔티티 종류가 10개가 넘고 각 엔티티의 번역 필드가 단순하며 전체 번역 현황 집계가 핵심 요구사항이면 단일 공유 테이블이 유리하다. CMS나 설정 값 번역처럼 엔티티 종류가 동적으로 늘어나는 경우도 여기에 해당한다. orphan 데이터 정리를 애플리케이션 레이어에서 책임져야 한다는 전제를 팀 전체가 인식하고 있어야 한다.

---

## 번역 테이블 규모 확장

번역 테이블은 생각보다 빠르게 커진다. 상품 10만 개에 지원 언어 10개, 번역 가능 필드 5개면 최대 500만 행이다. 이 규모에서 파티셔닝과 아카이빙을 고려하게 된다.

### 파티셔닝

`locale`을 파티션 키로 쓰는 방식이 직관적으로 보이지만, locale 카디널리티가 낮아서 파티션 수가 10~20개를 넘기 어렵다. 파티션 기준으로는 `locale`보다 `product_id`의 범위가 낫다.

PostgreSQL에서 범위 파티셔닝:

```sql
CREATE TABLE product_translations (
    product_id  BIGINT      NOT NULL,
    locale      VARCHAR(10) NOT NULL,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
) PARTITION BY RANGE (product_id);

CREATE TABLE product_translations_p0
    PARTITION OF product_translations
    FOR VALUES FROM (MINVALUE) TO (1000001);

CREATE TABLE product_translations_p1
    PARTITION OF product_translations
    FOR VALUES FROM (1000001) TO (2000001);

CREATE TABLE product_translations_p2
    PARTITION OF product_translations
    FOR VALUES FROM (2000001) TO (MAXVALUE);

-- 각 파티션에 UNIQUE 인덱스
CREATE UNIQUE INDEX ON product_translations_p0 (product_id, locale);
CREATE UNIQUE INDEX ON product_translations_p1 (product_id, locale);
CREATE UNIQUE INDEX ON product_translations_p2 (product_id, locale);
```

파티션 프루닝이 동작하려면 쿼리의 WHERE 절에 파티션 키 조건이 있어야 한다. `WHERE product_id = ?` 조건이 있으면 해당 파티션만 스캔한다. `WHERE locale = 'ko'` 조건만 있으면 전체 파티션을 스캔해서 파티셔닝 효과가 없다.

단일 공유 번역 테이블에서는 `entity_type`을 파티션 키로 리스트 파티셔닝하면 엔티티 종류별로 물리적으로 분리된다.

```sql
CREATE TABLE translations (
    entity_type VARCHAR(50)  NOT NULL,
    entity_id   BIGINT       NOT NULL,
    locale      VARCHAR(10)  NOT NULL,
    field_name  VARCHAR(100) NOT NULL,
    content     TEXT         NOT NULL
) PARTITION BY LIST (entity_type);

CREATE TABLE translations_product
    PARTITION OF translations FOR VALUES IN ('product');

CREATE TABLE translations_category
    PARTITION OF translations FOR VALUES IN ('category');

CREATE TABLE translations_brand
    PARTITION OF translations FOR VALUES IN ('brand');
```

MySQL에서 파티셔닝은 UNIQUE 제약과의 충돌 문제가 있다. MySQL은 UNIQUE 인덱스의 모든 컬럼이 파티션 키를 포함해야 한다는 제약이 있어서, 파티션 키가 `product_id`면 UNIQUE 제약도 `(product_id, locale)`로 이미 포함하고 있어 문제가 없다.

```sql
-- MySQL: product_id 범위 기반 파티셔닝
CREATE TABLE product_translations (
    product_id  BIGINT      NOT NULL,
    locale      VARCHAR(10) NOT NULL,
    name        VARCHAR(255) NOT NULL,
    UNIQUE KEY uq_product_locale (product_id, locale)
) PARTITION BY RANGE (product_id) (
    PARTITION p0 VALUES LESS THAN (1000001),
    PARTITION p1 VALUES LESS THAN (2000001),
    PARTITION p2 VALUES LESS THAN MAXVALUE
);
```

파티션 수는 처음부터 많이 만들지 않는다. 나중에 파티션을 추가하거나 분할하는 작업이 기존 파티션을 많이 만들어두는 것보다 낫다.

### 아카이빙

삭제된 엔티티의 번역 행을 `ON DELETE CASCADE`로 실시간 삭제하는 방식이 운영상 가장 단순하다. 번역 작업 이력을 감사 목적으로 보존해야 하는 경우에는 아카이브 테이블로 이동하는 방식이 필요하다.

```sql
CREATE TABLE product_translations_archive (
    LIKE product_translations INCLUDING ALL,
    archived_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    archive_reason VARCHAR(100)
);

-- 삭제 전 아카이브 트리거 (PostgreSQL)
CREATE OR REPLACE FUNCTION archive_product_translation()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO product_translations_archive
    SELECT OLD.*, now(), 'product_deleted';
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_archive_translation
BEFORE DELETE ON product_translations
FOR EACH ROW EXECUTE FUNCTION archive_product_translation();
```

아카이브 테이블은 별도 테이블스페이스나 느린 디스크에 두고 정기적으로 오래된 데이터를 삭제하는 배치를 돌린다. `DELETE FROM product_translations_archive WHERE archived_at < NOW() - INTERVAL '2 years'`를 한 번에 실행하면 삭제 대상이 수백만 행일 수 있다. 배치 크기를 제한하고 나눠서 실행해야 한다.

```sql
-- 배치 삭제 (PostgreSQL)
DO $$
DECLARE
    deleted_count INT;
BEGIN
    LOOP
        DELETE FROM product_translations_archive
        WHERE id IN (
            SELECT id FROM product_translations_archive
            WHERE archived_at < now() - INTERVAL '2 years'
            LIMIT 1000
        );

        GET DIAGNOSTICS deleted_count = ROW_COUNT;
        EXIT WHEN deleted_count = 0;

        PERFORM pg_sleep(0.05);
    END LOOP;
END;
$$;
```

---

## 번역 워크플로우 상태 관리

번역팀이 개입하는 서비스에서는 번역 텍스트가 곧바로 실서비스에 노출되면 안 된다. 기계 번역 초안, 번역가 수정, 검토자 승인, 발행 단계가 필요하다.

### 스키마 설계

```sql
CREATE TABLE product_translations (
    product_id    BIGINT       NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    locale        VARCHAR(10)  NOT NULL,

    -- 번역 데이터
    name          VARCHAR(255) NOT NULL,
    description   TEXT,

    -- 워크플로우 상태
    status        VARCHAR(20)  NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft', 'review', 'approved', 'published', 'rejected')),

    -- 담당자 추적
    created_by    VARCHAR(100),
    reviewed_by   VARCHAR(100),
    published_by  VARCHAR(100),

    -- 타임스탬프
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    reviewed_at   TIMESTAMPTZ,
    published_at  TIMESTAMPTZ,
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),

    -- 검토 메모
    reviewer_note TEXT,

    PRIMARY KEY (product_id, locale)
);

-- 상태별 조회 성능을 위한 인덱스
CREATE INDEX idx_pt_locale_status
    ON product_translations (locale, status);

-- 번역 담당자별 처리 대기 목록 조회용
CREATE INDEX idx_pt_status_updated
    ON product_translations (status, updated_at DESC);
```

`status` 컬럼에 CHECK 제약을 걸어두면 잘못된 상태 값이 들어오는 걸 DB 레벨에서 막는다. 애플리케이션에서 상태를 검증해도 DB 레벨 제약이 마지막 방어선이다.

### 상태 전이 규칙

허용되는 전이:

```
draft     → review
review    → approved
review    → rejected
approved  → published
rejected  → draft     (수정 후 재제출)
published → draft     (수정 시 새 버전 시작)
```

상태 전이를 애플리케이션 레이어에서 강제하는 방법:

```java
@Service
@Transactional
public class TranslationWorkflowService {

    public void submitForReview(Long productId, String locale, String reviewer) {
        ProductTranslation t = repo.findByProductIdAndLocale(productId, locale)
            .orElseThrow(() -> new TranslationNotFoundException(productId, locale));

        if (!"draft".equals(t.getStatus())) {
            throw new InvalidStatusTransitionException(
                "submit_for_review requires draft, current: " + t.getStatus()
            );
        }

        t.setStatus("review");
        t.setReviewedBy(reviewer);
        t.setReviewedAt(Instant.now());
        repo.save(t);
    }

    public void approve(Long productId, String locale, String reviewer, String note) {
        ProductTranslation t = repo.findByProductIdAndLocale(productId, locale)
            .orElseThrow(() -> new TranslationNotFoundException(productId, locale));

        if (!"review".equals(t.getStatus())) {
            throw new InvalidStatusTransitionException(
                "approve requires review status, current: " + t.getStatus()
            );
        }

        t.setStatus("approved");
        t.setReviewedBy(reviewer);
        t.setReviewedAt(Instant.now());
        t.setReviewerNote(note);
        repo.save(t);
    }

    public void publish(Long productId, String locale, String publisher) {
        ProductTranslation t = repo.findByProductIdAndLocale(productId, locale)
            .orElseThrow(() -> new TranslationNotFoundException(productId, locale));

        if (!"approved".equals(t.getStatus())) {
            throw new InvalidStatusTransitionException(
                "publish requires approved status, current: " + t.getStatus()
            );
        }

        t.setStatus("published");
        t.setPublishedBy(publisher);
        t.setPublishedAt(Instant.now());
        repo.save(t);
    }

    public void reject(Long productId, String locale, String reviewer, String reason) {
        ProductTranslation t = repo.findByProductIdAndLocale(productId, locale)
            .orElseThrow(() -> new TranslationNotFoundException(productId, locale));

        if (!Set.of("review", "approved").contains(t.getStatus())) {
            throw new InvalidStatusTransitionException(
                "reject requires review or approved status, current: " + t.getStatus()
            );
        }

        t.setStatus("rejected");
        t.setReviewerNote(reason);
        t.setReviewedBy(reviewer);
        t.setReviewedAt(Instant.now());
        repo.save(t);
    }
}
```

### 발행 전 서비스 격리

draft 또는 review 상태의 번역이 실서비스에 노출되면 안 된다. 서비스 조회 쿼리에 항상 `status = 'published'` 조건을 붙인다.

```sql
-- 서비스 조회: published 상태만
SELECT p.id, p.sku, t.name, t.description
FROM products p
JOIN product_translations t ON t.product_id = p.id
WHERE t.locale = 'ko'
  AND t.status = 'published';
```

`idx_pt_locale_status` 인덱스가 `(locale, status)` 순서로 잡혀 있어서 이 쿼리에서 사용된다.

번역을 수정할 때 published 상태 행을 직접 수정하면 수정 중인 텍스트가 실서비스에 노출된다. 버전 관리가 필요한 경우 현재 번역을 별도 히스토리 테이블에 보관하고 새 버전을 draft로 시작하는 방식을 쓴다.

```sql
CREATE TABLE product_translation_versions (
    id            BIGINT      PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    product_id    BIGINT      NOT NULL,
    locale        VARCHAR(10) NOT NULL,
    name          VARCHAR(255),
    description   TEXT,
    published_by  VARCHAR(100),
    published_at  TIMESTAMPTZ NOT NULL,
    superseded_at TIMESTAMPTZ,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
```

현재 번역은 `product_translations`에서 관리하고, 발행할 때마다 이전 버전을 `product_translation_versions`에 INSERT한다. 롤백이 필요하면 버전 테이블에서 이전 행을 가져와 현재 테이블에 다시 쓴다.

### 번역 대기 현황 집계

```sql
-- 상태별, 언어별 번역 처리 대기 현황
SELECT
    locale,
    COUNT(*) FILTER (WHERE status = 'draft')     AS draft_count,
    COUNT(*) FILTER (WHERE status = 'review')    AS review_count,
    COUNT(*) FILTER (WHERE status = 'approved')  AS approved_count,
    COUNT(*) FILTER (WHERE status = 'published') AS published_count,
    COUNT(*) FILTER (WHERE status = 'rejected')  AS rejected_count
FROM product_translations
GROUP BY locale
ORDER BY locale;
```

MySQL은 `FILTER` 절이 없으므로:

```sql
SELECT
    locale,
    SUM(status = 'draft')     AS draft_count,
    SUM(status = 'review')    AS review_count,
    SUM(status = 'approved')  AS approved_count,
    SUM(status = 'published') AS published_count,
    SUM(status = 'rejected')  AS rejected_count
FROM product_translations
GROUP BY locale;
```

---

## 번역팀 대상 CSV/Excel 일괄 import/export

번역 작업에서 번역가가 직접 시스템에 접근하는 경우는 드물다. 번역 담당자가 미완성 번역 목록을 파일로 내보내고, 번역가가 번역을 채워 돌려주면 시스템에 일괄 임포트하는 흐름이 실무에서 일반적이다.

### Export 설계

번역이 필요한 항목을 CSV로 내보낸다.

```sql
-- 한국어 번역이 없거나 draft/rejected 상태인 상품 Export 쿼리
SELECT
    p.id                              AS product_id,
    p.sku,
    p.internal_name,                  -- 번역가 맥락 파악용 원어 이름
    COALESCE(t.name, '')              AS name_ko,
    COALESCE(t.description, '')       AS description_ko,
    COALESCE(t.status, 'missing')     AS status,
    t.reviewer_note
FROM products p
LEFT JOIN product_translations t
    ON t.product_id = p.id AND t.locale = 'ko'
WHERE t.product_id IS NULL
   OR t.status IN ('draft', 'rejected')
ORDER BY p.id;
```

CSV 파일 형식:

```
product_id,sku,internal_name,name_ko,description_ko,status,reviewer_note
1,SKU-001,Wireless Earphone,,,missing,
2,SKU-002,Bluetooth Speaker,블루투스 스피커,,draft,
3,SKU-003,USB-C Hub,USB-C 허브,잘못된 번역,rejected,원어 발음 그대로 사용 금지
```

`product_id`와 `sku`는 임포트 시 식별자로 쓰이므로 반드시 포함해야 한다. 번역가가 행을 삭제하거나 순서를 바꿔도 식별자로 매핑할 수 있어야 한다.

Java에서 OpenCSV로 Export 구현:

```java
@Service
public class TranslationExportService {

    public byte[] exportToCsv(String locale) throws IOException {
        List<TranslationExportRow> rows = translationRepo.findMissingOrDraft(locale);

        StringWriter sw = new StringWriter();
        try (CSVWriter writer = new CSVWriter(sw)) {
            writer.writeNext(new String[]{
                "product_id", "sku", "internal_name",
                "name_" + locale, "description_" + locale,
                "status", "reviewer_note"
            });

            for (TranslationExportRow row : rows) {
                writer.writeNext(new String[]{
                    String.valueOf(row.getProductId()),
                    row.getSku(),
                    row.getInternalName(),
                    nullToEmpty(row.getName()),
                    nullToEmpty(row.getDescription()),
                    row.getStatus(),
                    nullToEmpty(row.getReviewerNote())
                });
            }
        }

        // BOM 포함 UTF-8 — Excel에서 한글 깨짐 방지
        byte[] bom = {(byte) 0xEF, (byte) 0xBB, (byte) 0xBF};
        byte[] content = sw.toString().getBytes(StandardCharsets.UTF_8);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        out.write(bom);
        out.write(content);
        return out.toByteArray();
    }

    private String nullToEmpty(String value) {
        return value != null ? value : "";
    }
}
```

Excel 2016 이전 버전에서 UTF-8 CSV를 열면 한글이 깨지는 경우가 많다. BOM을 붙이거나 xlsx 포맷으로 직접 내보내야 한다. xlsx로 내보낼 경우 Apache POI를 쓴다.

### Import 설계

번역가가 파일을 채워 돌려주면 임포트를 실행한다. 임포트 과정에서 데이터 검증, 중복 처리, 실패 행 보고가 필요하다.

```java
@Service
@Transactional
public class TranslationImportService {

    public ImportResult importFromCsv(byte[] csvBytes, String locale, String importedBy) {
        List<TranslationImportRow> rows = parseCsv(csvBytes);
        List<ImportError> errors = new ArrayList<>();
        int successCount = 0;

        for (int i = 0; i < rows.size(); i++) {
            int lineNumber = i + 2; // 헤더 포함 1-indexed
            TranslationImportRow row = rows.get(i);
            try {
                validateRow(row, lineNumber);
                upsertTranslation(row, locale, importedBy);
                successCount++;
            } catch (ValidationException e) {
                errors.add(new ImportError(lineNumber, row.getSku(), e.getMessage()));
            }
        }

        return new ImportResult(successCount, errors);
    }

    private void validateRow(TranslationImportRow row, int lineNumber) {
        if (row.getProductId() == null) {
            throw new ValidationException("product_id 누락");
        }
        if (row.getName() == null || row.getName().isBlank()) {
            throw new ValidationException("name 필드가 비어 있음");
        }
        if (!productRepo.existsById(row.getProductId())) {
            throw new ValidationException("존재하지 않는 product_id: " + row.getProductId());
        }
    }

    private void upsertTranslation(TranslationImportRow row, String locale, String importedBy) {
        translationRepo.upsert(
            row.getProductId(), locale,
            row.getName(), row.getDescription(),
            "draft", importedBy, Instant.now()
        );
    }
}
```

DB 레벨에서 UPSERT 처리:

```sql
-- PostgreSQL
INSERT INTO product_translations
    (product_id, locale, name, description, status, created_by, updated_at)
VALUES
    (:productId, :locale, :name, :description, 'draft', :importedBy, now())
ON CONFLICT (product_id, locale)
DO UPDATE SET
    name        = EXCLUDED.name,
    description = EXCLUDED.description,
    status      = CASE
                      WHEN product_translations.status = 'published' THEN 'draft'
                      ELSE product_translations.status
                  END,
    updated_at  = now();
```

`ON CONFLICT DO UPDATE`에서 `status` 처리가 중요하다. 이미 발행된 번역을 임포트로 덮어쓸 때 자동으로 `draft`로 되돌리면 검토 없이 서비스에 반영되는 것을 막는다.

MySQL:

```sql
INSERT INTO product_translations
    (product_id, locale, name, description, status, created_by, updated_at)
VALUES
    (:productId, :locale, :name, :description, 'draft', :importedBy, now())
ON DUPLICATE KEY UPDATE
    name        = VALUES(name),
    description = VALUES(description),
    status      = IF(status = 'published', 'draft', status),
    updated_at  = now();
```

임포트 결과 리포트를 번역 담당자에게 돌려줘야 한다. 성공 건수, 실패 행 번호와 이유, 발행된 번역을 덮어써서 draft로 되돌린 건수 정보가 있어야 한다.

---

## 번역 메모리와 중복 번역 제거

같은 텍스트가 여러 엔티티에 반복 등장하는 경우가 생각보다 많다. 상품 설명의 공통 문구, 약관 문장, UI 레이블 등이 그렇다. 이미 한 번 번역된 텍스트를 다시 번역하면 비용이 이중으로 든다. 번역 메모리(Translation Memory)는 원문 텍스트의 해시를 키로 기존 번역을 재사용 제안으로 보여주는 방식이다.

### 번역 메모리 테이블 설계

```sql
CREATE TABLE translation_memory (
    id            BIGINT      PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    source_locale VARCHAR(10) NOT NULL DEFAULT 'en',
    target_locale VARCHAR(10) NOT NULL,
    source_text   TEXT        NOT NULL,
    source_hash   CHAR(64)    NOT NULL,  -- SHA-256 hex
    target_text   TEXT        NOT NULL,
    usage_count   INT         NOT NULL DEFAULT 1,
    last_used_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_locale, target_locale, source_hash)
);

CREATE INDEX idx_tm_lookup
    ON translation_memory (source_locale, target_locale, source_hash);
```

새 번역을 저장할 때 원문의 SHA-256 해시를 번역 메모리에 기록한다. 이후 같은 원문이 들어오면 기존 번역을 재사용 제안으로 보여준다.

```java
@Service
public class TranslationMemoryService {

    public String computeHash(String text) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(text.trim().getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }

    public Optional<String> findExisting(
            String sourceText, String sourceLang, String targetLang) {
        String hash = computeHash(sourceText);
        return tmRepo.findBySourceHashAndLocales(hash, sourceLang, targetLang)
            .map(tm -> {
                tm.incrementUsageCount();
                tm.setLastUsedAt(Instant.now());
                tmRepo.save(tm);
                return tm.getTargetText();
            });
    }

    public void record(
            String sourceText, String targetText,
            String sourceLang, String targetLang) {
        String hash = computeHash(sourceText);
        tmRepo.upsert(sourceLang, targetLang, sourceText, hash, targetText);
    }
}
```

번역 메모리는 100% 일치(exact match)와 유사도 기반 매칭(fuzzy match)으로 나뉜다. 해시 기반은 100% 일치만 탐지한다. 유사도 기반 매칭이 필요하면 PostgreSQL의 `pg_trgm` 확장을 쓰거나 Elasticsearch 같은 외부 시스템과 연계해야 한다. 대부분의 경우 정확히 일치하는 텍스트 재사용만으로 충분한 효과를 낸다.

### 중복 번역 탐지

단일 공유 번역 테이블에서는 같은 텍스트가 여러 엔티티에 중복 저장되어 있는지 집계하기 쉽다.

```sql
-- 같은 번역 텍스트가 여러 번 등장하는 항목 탐지
SELECT
    locale,
    field_name,
    content AS target_text,
    COUNT(*) AS duplicate_count
FROM translations
GROUP BY locale, field_name, content
HAVING COUNT(*) > 3
ORDER BY duplicate_count DESC
LIMIT 50;
```

엔티티별 번역 테이블에서는 `UNION ALL`로 모아야 한다.

중복이 많이 탐지되면 번역 메모리 활용도가 낮다는 신호다. 번역 워크플로우에 메모리 조회 단계가 빠져 있거나, 번역가가 제안을 무시하고 직접 입력하는 경우가 많다는 뜻이다.

### 공통 번역 테이블

자주 반복되는 UI 레이블이나 공통 문구는 별도 공통 번역 테이블로 분리하는 방식도 있다.

```sql
CREATE TABLE common_translations (
    key     VARCHAR(200) NOT NULL,
    locale  VARCHAR(10)  NOT NULL,
    value   TEXT         NOT NULL,
    PRIMARY KEY (key, locale)
);

-- 점 표기로 계층 구조를 표현한다
INSERT INTO common_translations (key, locale, value)
VALUES
    ('product.status.out_of_stock', 'ko', '품절'),
    ('product.status.out_of_stock', 'en', 'Out of Stock'),
    ('product.status.out_of_stock', 'ja', '品切れ'),
    ('product.status.discontinued', 'ko', '단종'),
    ('product.status.discontinued', 'en', 'Discontinued');
```

공통 번역과 엔티티별 번역을 섞어 쓰면 클라이언트에서 두 종류의 번역을 다 처리해야 해서 복잡해진다. 처음부터 분리 전략을 정해두지 않으면 나중에 정리하기 어렵다. 공통 번역 테이블은 조회 빈도가 매우 높아서 애플리케이션 시작 시 전량 로드해서 메모리에 올려두는 방식을 쓰는 경우가 많다.

---

## 마이크로서비스 환경에서 번역 테이블 위치 결정

마이크로서비스 아키텍처에서 번역 데이터를 어디에 둘지는 서비스 경계 설계와 맞닿아 있다. 크게 세 가지 방식이 있다.

### 전담 번역 서비스 (공유 DB)

번역 데이터를 하나의 전담 서비스(Translation Service)가 관리하고, 다른 서비스는 API로 번역을 요청한다.

```
Product Service  ──→  Translation Service  ──→  translation_db
Article Service  ──→  Translation Service
Category Service ──→  Translation Service
```

번역 관련 로직이 한 곳에 집중된다. 번역 워크플로우, 번역 메모리, 통계 집계가 단일 서비스에서 처리된다.

문제는 번역 조회가 모든 서비스의 응답 경로에 들어간다는 점이다. Translation Service가 느리거나 장애가 나면 Product Service의 조회도 느려진다. 각 서비스에서 번역 데이터를 캐싱하는 구조가 필수다.

번역이 수정되면 Translation Service가 이벤트를 발행해서 구독 서비스들이 캐시를 무효화하게 해야 한다.

```
Translation Service → "translation.updated" 이벤트 발행 (Kafka/RabbitMQ)
    Product Service → 구독 → 로컬 캐시 무효화
    Article Service → 구독 → 로컬 캐시 무효화
```

캐시 무효화 이벤트가 유실되면 오래된 번역이 계속 서빙된다. 이벤트 유실에 대한 대비책(TTL 기반 만료, 주기적 동기화)이 있어야 한다.

### 서비스별 로컬 번역 테이블

각 서비스가 자신의 DB에 번역 테이블을 갖는다.

```
Product Service DB:  products, product_translations
Article Service DB:  articles, article_translations
```

서비스 간 의존성이 없다. Product Service는 자기 DB에서 번역을 직접 조회한다. 운영이 단순하고 장애 격리가 된다.

번역 현황 집계가 어렵다는 점이 단점이다. "전체 서비스에서 한국어 번역 완료율이 몇 퍼센트인가"를 알려면 각 서비스 API를 호출해서 합쳐야 한다. 번역 워크플로우도 각 서비스마다 구현해야 한다. 공통 번역 문구도 각 서비스가 복사해서 갖고 있어야 하므로 동기화 문제가 생긴다.

### 혼합 방식

공통 번역(UI 레이블, 에러 메시지)은 전담 서비스가 관리하고, 엔티티별 번역은 각 서비스의 로컬 DB에 둔다.

```
Translation Service: common_translations (UI 레이블, 공통 문구)
Product Service DB:  product_translations
Article Service DB:  article_translations
```

각 서비스는 시작 시 공통 번역을 Translation Service에서 읽어 로컬 메모리에 캐싱한다. 업데이트는 Translation Service가 이벤트를 발행해 반영한다. 엔티티별 번역은 자기 DB에서 직접 처리한다.

### 선택 기준

| 기준 | 전담 Translation Service | 서비스별 로컬 | 혼합 |
|---|---|---|---|
| 서비스 간 의존성 | 높음 | 없음 | 중간 |
| 번역 현황 집계 | 쉬움 | 어려움 | 중간 |
| 공통 번역 관리 | 쉬움 | 중복 발생 | 쉬움 |
| 장애 격리 | 약함 | 강함 | 중간 |
| 번역 워크플로우 구현 | 1회 | 서비스마다 | 1회 (공통만) |

서비스가 3개 이하이고 번역 현황 집계가 중요하면 전담 Translation Service가 낫다. 서비스가 많아질수록 전담 서비스의 의존 관계가 부담이 된다.

번역 데이터가 각 서비스의 핵심 데이터와 강하게 결합되어 있고 서비스 자율성이 더 중요하면 서비스별 로컬 번역 테이블이 맞다. 번역 현황은 각 서비스의 어드민 API를 합쳐서 보는 방식으로 타협한다.

공통 번역이 많고 엔티티별 번역도 상당량 있는 경우가 혼합 방식을 쓸 때다. 두 가지를 다 운영해야 해서 팀 인원이 충분할 때 선택하는 것이 맞다.

마이크로서비스 환경에서 번역 캐싱은 선택이 아니다. 번역 테이블이 어디에 있든 자주 읽히는 번역 데이터는 Redis나 인메모리 캐시로 서빙한다. 번역 수정 빈도는 낮고 조회 빈도는 높아서 캐시 적중률이 높다. TTL을 길게(1시간~24시간) 잡아도 대부분의 서비스에서 문제가 없다.
