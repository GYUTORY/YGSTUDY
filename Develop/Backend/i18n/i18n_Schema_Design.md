---
title: i18n DB 스키마 설계
tags: [backend, i18n, database, schema, postgresql, jsonb, hstore, orm, eav, migration, jpa, hibernate, index, n+1, fallback]
updated: 2026-08-07
---

# i18n DB 스키마 설계

## 스키마 패턴 3가지 비교

### EAV 방식 (Translation Table)

번역 테이블은 [EAV(Entity-Attribute-Value) 패턴](../../DataBase/RDBMS/EAV.md)을 i18n 도메인에 특화한 구조다. 범용 EAV에서 attribute 자리가 locale 코드로 고정되고, value 자리가 단일 TEXT가 아닌 복수 번역 필드(title, body, meta 등)로 구성된 레코드로 대체된다. 속성 집합이 런타임에 무한히 늘어날 수 있는 범용 EAV와 달리, 번역 테이블은 지원 언어 수만큼만 attribute가 존재하고 그 집합이 명시적으로 관리된다. 이 제약 덕분에 범용 EAV에서 피할 수 없는 orphan 데이터 문제나 타입 불일치 문제가 상당 부분 사라진다.

메인 엔티티에는 언어 독립 데이터만, 번역 가능한 필드는 별도 테이블로 분리한다.

```sql
CREATE TABLE articles (
    id         BIGINT       PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    slug       VARCHAR(200) NOT NULL UNIQUE,
    author_id  BIGINT       NOT NULL,
    status     VARCHAR(20)  NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE article_translations (
    article_id BIGINT       NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    locale     VARCHAR(10)  NOT NULL,
    title      VARCHAR(500) NOT NULL,
    body       TEXT         NOT NULL,
    meta_title VARCHAR(200),
    meta_desc  VARCHAR(500),
    PRIMARY KEY (article_id, locale)
);
```

복합 PK `(article_id, locale)`을 쓰면 surrogate key 없이 UNIQUE가 보장된다. FK + UNIQUE 제약을 따로 잡는 것보다 테이블이 단순해진다.

이 패턴의 실질적인 장점은 번역 현황 집계다. 어떤 콘텐츠에 어떤 언어가 빠져 있는지 쿼리 하나로 뽑을 수 있다.

```sql
-- 한국어 번역이 없는 아티클 목록
SELECT a.id, a.slug
FROM articles a
WHERE NOT EXISTS (
    SELECT 1 FROM article_translations t
    WHERE t.article_id = a.id AND t.locale = 'ko'
);
```

단점은 모든 조회에 JOIN이 붙는다는 것이다. 쿼리가 복잡해지고 N+1 발생 지점이 명확하게 생긴다.

### JSON 컬럼 방식

번역 데이터 전체를 JSON으로 메인 테이블에 저장한다. PostgreSQL JSONB가 대표적이다.

```sql
CREATE TABLE articles (
    id           BIGINT         PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    slug         VARCHAR(200)   NOT NULL UNIQUE,
    author_id    BIGINT         NOT NULL,
    status       VARCHAR(20)    NOT NULL DEFAULT 'draft',
    translations JSONB          NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ    NOT NULL DEFAULT now()
);
```

저장 형태:
```json
{
  "ko": {
    "title": "PostgreSQL JSONB 실전 사용법",
    "body": "...",
    "meta_title": "JSONB 활용"
  },
  "en": {
    "title": "PostgreSQL JSONB in Practice",
    "body": "..."
  }
}
```

JOIN 없이 단일 테이블 조회로 끝난다. ORM 레이어 코드도 EAV보다 단순해진다.

MySQL에서는 이 방식이 잘 맞지 않는다. MySQL JSON 타입은 이진 저장은 되지만 GIN 인덱스가 없어서 JSON 내부 키를 필터링하는 쿼리가 느리다. PostgreSQL 전용으로 봐야 한다.

### 인라인 컬럼 방식

지원 언어별로 컬럼을 직접 추가한다.

```sql
CREATE TABLE articles (
    id       BIGINT       PRIMARY KEY,
    slug     VARCHAR(200) NOT NULL,
    title_ko VARCHAR(500),
    title_en VARCHAR(500),
    body_ko  TEXT,
    body_en  TEXT
);
```

지원 언어가 처음부터 2개로 고정되어 앞으로도 바뀌지 않는다고 확신할 때만 고려할 수 있다. 새 언어 추가 시 ALTER TABLE이 필요하고, 운영 중인 대용량 테이블에 컬럼을 추가하면 락 이슈가 생긴다. 실무에서 거의 쓰지 않는 패턴이다.

### 패턴 비교

| 기준 | EAV (Translation Table) | JSON 컬럼 | 인라인 컬럼 |
|---|---|---|---|
| 새 언어 추가 | INSERT만 | UPDATE만 | ALTER TABLE 필요 |
| 조회 쿼리 | JOIN 필수 | 단순 | 단순 |
| N+1 위험 | 높음 | 없음 | 없음 |
| 번역 현황 집계 | 쉬움 | SQL 복잡 | 불가능에 가까움 |
| MySQL 적합성 | 적합 | 비권장 | 적합 |
| PostgreSQL 적합성 | 적합 | 적합 | 비권장 |
| 번역 상태 관리 | 컬럼 추가로 처리 | JSON 내부 필드로 처리 | 불가능에 가까움 |

PostgreSQL을 쓰고 서비스 규모가 작다면 JSON 컬럼이 운영이 편하다. 번역 현황 관리나 번역 상태 워크플로우가 필요하면 EAV가 낫다. MySQL이라면 EAV 외에 선택지가 없다고 봐도 된다.

---

## 언어 추가 시 마이그레이션 절차

### EAV 방식의 언어 추가

EAV 방식에서 새 언어를 추가한다는 건 스키마 변경 없이 번역 데이터를 삽입하는 작업이다. 스키마는 건드리지 않아도 되지만 준비 작업이 있다.

**1단계: 지원 언어 목록 업데이트**

지원 언어를 코드에 하드코딩하고 있다면 먼저 바꾼다. DB로 관리하는 경우:

```sql
CREATE TABLE supported_locales (
    locale     VARCHAR(10)  PRIMARY KEY,
    name_ko    VARCHAR(100) NOT NULL,
    name_en    VARCHAR(100) NOT NULL,
    is_active  BOOLEAN      NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

INSERT INTO supported_locales (locale, name_ko, name_en)
VALUES ('ja', '일본어', 'Japanese');
```

**2단계: 기존 콘텐츠에 번역 데이터 삽입**

번역이 완료된 것부터 넣는다. 전량 준비되기를 기다렸다가 한 번에 활성화하면 번역이 늦는 콘텐츠 때문에 언어 지원 시점이 계속 밀린다.

```sql
INSERT INTO article_translations (article_id, locale, title, body)
SELECT
    a.id,
    'ja'     AS locale,
    j.title,
    j.body
FROM articles a
JOIN japanese_translation_batch j ON j.article_id = a.id;
```

**3단계: 번역 현황 확인**

```sql
SELECT
    COUNT(*)                           AS total_articles,
    COUNT(t.article_id)                AS translated,
    COUNT(*) - COUNT(t.article_id)     AS missing
FROM articles a
LEFT JOIN article_translations t
    ON t.article_id = a.id AND t.locale = 'ja'
WHERE a.status = 'published';
```

**4단계: fallback 체인 업데이트**

`ja` 요청이 들어왔을 때 `ja → en` 순서로 fallback 하도록 체인 로직에 추가한다. 언어 추가 시 fallback 체인이 자동으로 처리되는 구조가 아니라면 코드 변경이 필요하다.

**5단계: 언어 활성화**

번역 완료율이 기준에 도달하면 활성화한다. 핵심 콘텐츠 90% 이상을 기준으로 쓰는 경우가 많다.

### JSON 컬럼 방식의 언어 추가

기존 행의 JSONB를 업데이트하는 작업이다.

```sql
UPDATE articles
SET translations = translations || jsonb_build_object(
    'ja', jsonb_build_object(
        'title', t.title,
        'body',  t.body
    )
)
FROM japanese_translation_batch t
WHERE articles.id = t.article_id;
```

`||` 연산자가 JSONB merge다. 기존 다른 언어 데이터는 그대로 두고 `ja` 키만 추가된다.

대용량 테이블이라면 배치로 나눠서 실행해야 한다. 전체 테이블을 한 번에 업데이트하면 디스크 I/O 폭발과 락 이슈가 생긴다.

```sql
DO $$
DECLARE
    batch_size INT    := 1000;
    max_id     BIGINT;
    current_id BIGINT := 0;
BEGIN
    SELECT MAX(id) INTO max_id FROM articles;

    WHILE current_id < max_id LOOP
        UPDATE articles a
        SET translations = translations || jsonb_build_object(
            'ja', jsonb_build_object('title', t.title, 'body', t.body)
        )
        FROM japanese_translation_batch t
        WHERE a.id = t.article_id
          AND a.id > current_id
          AND a.id <= current_id + batch_size;

        current_id := current_id + batch_size;
        PERFORM pg_sleep(0.1);
    END LOOP;
END;
$$;
```

---

## 다국어 쿼리 인덱스 설계

### EAV 방식 인덱스

복합 PK `(article_id, locale)`은 특정 아티클의 특정 locale 조회에 맞춰진 인덱스다. 가장 빈번한 쿼리 패턴이라 이 인덱스만으로 단건 조회는 충분하다.

```sql
-- PK 인덱스 사용
SELECT title, body FROM article_translations
WHERE article_id = 123 AND locale = 'ko';
```

전체 콘텐츠를 특정 locale로 조회하는 목록 쿼리에서는 `locale`이 선행 컬럼인 인덱스가 필요하다.

```sql
CREATE INDEX idx_article_translations_locale
    ON article_translations (locale, article_id);

-- 이 쿼리에서 위 인덱스 사용
SELECT a.slug, t.title
FROM articles a
JOIN article_translations t ON t.article_id = a.id
WHERE t.locale = 'ko' AND a.status = 'published';
```

번역이 없는 콘텐츠를 찾는 쿼리는 NOT EXISTS를 써야 하는데, 인덱스를 써도 풀 스캔에 가깝다. 번역 현황 확인이 잦다면 별도 테이블로 관리하는 편이 낫다.

### JSONB 인덱스 (PostgreSQL)

GIN 인덱스로 JSON 내부 구조를 인덱싱할 수 있다.

```sql
CREATE INDEX idx_articles_translations_gin
    ON articles USING GIN (translations);

-- 특정 언어 존재 여부 필터 — GIN 인덱스 사용
SELECT id FROM articles WHERE translations ? 'ko';

-- 특정 경로 값 포함 필터
SELECT id FROM articles WHERE translations @> '{"ko": {"title": "PostgreSQL"}}';
```

특정 언어의 타이틀로 검색이 필요하면 함수 인덱스를 추가한다.

```sql
CREATE INDEX idx_articles_ko_title
    ON articles ((translations -> 'ko' ->> 'title'));

-- 위 인덱스 사용
SELECT id FROM articles
WHERE translations -> 'ko' ->> 'title' LIKE '검색어%';
```

GIN 인덱스는 크기가 크다. 번역 데이터가 많아지면 인덱스 자체가 상당한 공간을 차지한다. 실제로 쓰이는 쿼리 패턴에 맞춰 최소한으로 잡아야 한다.

---

## PostgreSQL JSONB vs hstore 실무 비교

### hstore

hstore는 키-값 쌍을 저장하는 PostgreSQL 확장이다. i18n 용도로 쓰면 언어 코드를 키, 번역 텍스트를 값으로 저장한다.

```sql
CREATE EXTENSION IF NOT EXISTS hstore;

CREATE TABLE articles (
    id         BIGINT      PRIMARY KEY,
    slug       VARCHAR(200) NOT NULL,
    title_i18n HSTORE      NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO articles (id, slug, title_i18n)
VALUES (1, 'test', 'ko => "한국어 제목", en => "English Title"');

SELECT title_i18n -> 'ko' AS title FROM articles WHERE id = 1;

CREATE INDEX idx_articles_title_gin ON articles USING GIN (title_i18n);
```

hstore의 한계는 값이 텍스트 단일 타입이라는 것이다. `title`, `body`, `meta_title` 같이 번역 필드가 여러 개면 필드 수만큼 hstore 컬럼을 만들어야 한다.

```sql
-- 번역 필드가 3개면 이렇게 된다
CREATE TABLE articles (
    id          BIGINT  PRIMARY KEY,
    title_i18n  HSTORE  NOT NULL DEFAULT '',
    body_i18n   HSTORE  NOT NULL DEFAULT '',
    meta_i18n   HSTORE  NOT NULL DEFAULT ''
);
```

### JSONB

JSONB는 계층 구조를 지원한다. 언어를 상위 키로, 번역 필드들을 하위 객체로 담을 수 있다.

```sql
CREATE TABLE articles (
    id           BIGINT PRIMARY KEY,
    translations JSONB  NOT NULL DEFAULT '{}'
);

INSERT INTO articles (id, translations)
VALUES (1, '{
    "ko": {"title": "한국어 제목", "body": "본문", "meta_title": "메타"},
    "en": {"title": "English Title", "body": "Body text"}
}');

SELECT
    translations -> 'ko' ->> 'title' AS title,
    translations -> 'ko' ->> 'body'  AS body
FROM articles WHERE id = 1;
```

### 비교

| 기준 | hstore | JSONB |
|---|---|---|
| 다중 필드 처리 | 필드당 컬럼 필요 | 중첩 구조로 처리 |
| 타입 지원 | 텍스트만 | 숫자·불리언·배열·객체 |
| 인덱스 | GIN (키-값 pair) | GIN (계층 구조) |
| 연산자 | `->`, `?`, `@>` | `->`, `->>`, `#>`, `?`, `@>` |
| 저장 크기 | 상대적으로 작음 | 약간 큼 |

i18n 목적으로는 JSONB가 낫다. hstore는 번역 필드가 단 하나인 경우에나 의미 있다. 필드가 두 개 이상이면 JSONB를 써야 한다.

레거시 hstore를 JSONB로 마이그레이션하는 경우:

```sql
ALTER TABLE articles ADD COLUMN translations JSONB NOT NULL DEFAULT '{}';

UPDATE articles
SET translations = (
    SELECT jsonb_object_agg(
        key,
        jsonb_build_object(
            'title', title_i18n -> key,
            'body',  body_i18n  -> key
        )
    )
    FROM skeys(title_i18n) AS key
    WHERE title_i18n -> key IS NOT NULL
);

ALTER TABLE articles DROP COLUMN title_i18n;
ALTER TABLE articles DROP COLUMN body_i18n;
```

---

## ORM 매핑

### JPA/Hibernate — EAV 방식

```java
@Entity
@Table(name = "articles")
public class Article {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String slug;

    @OneToMany(
        mappedBy = "article",
        cascade = CascadeType.ALL,
        orphanRemoval = true,
        fetch = FetchType.LAZY
    )
    @MapKey(name = "locale")
    private Map<String, ArticleTranslation> translations = new HashMap<>();

    public Optional<ArticleTranslation> getTranslation(String locale) {
        return Optional.ofNullable(translations.get(locale));
    }
}

@Entity
@Table(name = "article_translations")
@IdClass(ArticleTranslationId.class)
public class ArticleTranslation {

    @Id
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "article_id")
    private Article article;

    @Id
    private String locale;

    private String title;

    @Column(columnDefinition = "TEXT")
    private String body;
}
```

`@MapKey(name = "locale")`를 쓰면 translations를 Map으로 관리할 수 있다. `article.getTranslations().get("ko")`로 접근한다.

`FetchType.LAZY`로 두면 translations를 처음 접근하는 시점에 쿼리가 나간다. 목록 조회 후 각 Article의 translation에 접근하면 N+1이 된다.

### JPA/Hibernate — JSONB 방식

Hibernate 6.x부터 JSONB 타입을 공식 지원한다.

```java
@Entity
@Table(name = "articles")
public class Article {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private Map<String, ArticleTranslationDto> translations = new HashMap<>();
}

public record ArticleTranslationDto(
    String title,
    String body,
    String metaTitle
) {}
```

Hibernate 5.x 이하라면 hypersistence-utils 라이브러리가 필요하다.

```java
// hypersistence-utils 사용 (Hibernate 5.x)
@Type(JsonType.class)
@Column(columnDefinition = "jsonb")
private Map<String, ArticleTranslationDto> translations;
```

### TypeORM (Node.js)

EAV 방식:

```typescript
@Entity()
export class Article {
    @PrimaryGeneratedColumn()
    id: number;

    @Column()
    slug: string;

    @OneToMany(() => ArticleTranslation, (t) => t.article, { cascade: true })
    translations: ArticleTranslation[];
}

@Entity()
@Unique(['article', 'locale'])
export class ArticleTranslation {
    @PrimaryGeneratedColumn()
    id: number;

    @ManyToOne(() => Article, (a) => a.translations, { onDelete: 'CASCADE' })
    article: Article;

    @Column({ length: 10 })
    locale: string;

    @Column({ length: 500 })
    title: string;

    @Column('text', { nullable: true })
    body: string;
}
```

JSONB 방식 (PostgreSQL):

```typescript
@Entity()
export class Article {
    @PrimaryGeneratedColumn()
    id: number;

    @Column({ type: 'jsonb', default: '{}' })
    translations: Record<string, { title: string; body?: string }>;
}
```

---

## N+1 문제 해결

### 원인

EAV 방식에서 N+1은 목록 조회 후 각 아이템의 번역에 개별 접근할 때 발생한다.

```java
// 이 코드는 N+1을 만든다
List<Article> articles = articleRepository.findAll(pageable).getContent();
articles.forEach(a -> {
    // Article마다 SELECT 쿼리 발생
    ArticleTranslation t = a.getTranslations().get("ko");
    response.add(ArticleResponse.of(a, t));
});
```

100개 목록이라면 101번의 쿼리가 나간다.

### 해결 방법 1: JOIN FETCH

```java
@Query("""
    SELECT a FROM Article a
    LEFT JOIN FETCH a.translations t
    WHERE KEY(t) = :locale
    """)
List<Article> findAllWithTranslation(@Param("locale") String locale);
```

페이징과 함께 쓰면 Hibernate가 `HHH90003004` 경고를 낸다. 메모리에서 페이징 처리하기 때문이다. 데이터 양이 많으면 OOM이 생길 수 있다.

### 해결 방법 2: ID 목록으로 두 번 쿼리

```java
// 1) ID 목록으로 페이징
Page<Long> idPage = articleRepository.findIds(pageable);

// 2) 번역 일괄 조회
List<ArticleTranslation> translations =
    translationRepository.findByArticleIdInAndLocale(idPage.getContent(), locale);

Map<Long, ArticleTranslation> translationMap = translations.stream()
    .collect(Collectors.toMap(
        t -> t.getArticle().getId(),
        t -> t
    ));

// 3) 결합
List<Article> articles = articleRepository.findAllById(idPage.getContent());
return articles.stream()
    .map(a -> ArticleResponse.of(a, translationMap.get(a.getId())))
    .toList();
```

쿼리가 세 번 나가지만 페이징이 DB에서 정확히 처리된다.

### 해결 방법 3: 네이티브 쿼리로 DTO 직접 조회

```java
@Query(value = """
    SELECT a.id, a.slug, t.title, t.body
    FROM articles a
    LEFT JOIN article_translations t
        ON t.article_id = a.id AND t.locale = :locale
    WHERE a.status = 'published'
    ORDER BY a.created_at DESC
    LIMIT :size OFFSET :offset
    """, nativeQuery = true)
List<Object[]> findPublishedWithTranslation(
    @Param("locale") String locale,
    @Param("size") int size,
    @Param("offset") int offset
);
```

엔티티 매핑 오버헤드 없이 필요한 컬럼만 가져오는 방식이라 성능이 가장 좋다. 다만 반환값이 `Object[]`라 가독성이 떨어진다. `@SqlResultSetMapping`이나 `Projections.constructor` 방식으로 DTO에 바로 매핑하는 구조로 개선할 수 있다.

---

## Fallback Chain 구현

### 체인 구성 로직

```java
@Component
public class LocaleFallbackResolver {

    private static final String DEFAULT_LOCALE = "en";

    // ko-KR → ["ko-KR", "ko", "en"]
    // ja    → ["ja", "en"]
    // en-US → ["en-US", "en"]
    public List<String> buildChain(String requestedLocale) {
        if (requestedLocale == null || requestedLocale.isBlank()) {
            return List.of(DEFAULT_LOCALE);
        }

        List<String> chain = new ArrayList<>();
        chain.add(requestedLocale);

        if (requestedLocale.contains("-")) {
            String baseLang = requestedLocale.split("-")[0];
            chain.add(baseLang);
        }

        if (!DEFAULT_LOCALE.equals(requestedLocale) &&
            !requestedLocale.startsWith(DEFAULT_LOCALE + "-")) {
            chain.add(DEFAULT_LOCALE);
        }

        return Collections.unmodifiableList(chain);
    }
}
```

### DB 레벨 Fallback

JSONB 방식에서 fallback을 DB에서 처리하는 방법이다.

```sql
-- ko-KR → ko → en 순서로 fallback
SELECT
    id,
    COALESCE(
        translations -> 'ko-KR' ->> 'title',
        translations -> 'ko'    ->> 'title',
        translations -> 'en'    ->> 'title'
    ) AS title
FROM articles
WHERE status = 'published';
```

EAV 방식에서 DB fallback:

```sql
SELECT
    a.id,
    a.slug,
    COALESCE(t_exact.title, t_lang.title, t_default.title) AS title
FROM articles a
LEFT JOIN article_translations t_exact
    ON t_exact.article_id = a.id AND t_exact.locale = 'ko-KR'
LEFT JOIN article_translations t_lang
    ON t_lang.article_id = a.id AND t_lang.locale = 'ko'
LEFT JOIN article_translations t_default
    ON t_default.article_id = a.id AND t_default.locale = 'en'
WHERE a.status = 'published';
```

목록 조회에서 트리플 조인을 쓰면 실행 계획이 복잡해진다. 단건 조회라면 괜찮지만 목록에는 적용하지 않는 편이 낫다. 목록 조회는 애플리케이션 레이어에서 fallback을 처리하고 결과를 캐싱하는 구조가 현실적이다.

### 캐싱과 Fallback 조합

번역 데이터는 읽기 빈도가 높고 수정 빈도가 낮아서 캐싱과 궁합이 좋다.

```java
@Service
public class TranslationService {

    private final ArticleTranslationRepository repo;
    private final LocaleFallbackResolver fallbackResolver;

    @Cacheable(value = "translations", key = "#articleId + ':' + #locale")
    public Optional<ArticleTranslation> getTranslation(Long articleId, String locale) {
        List<String> chain = fallbackResolver.buildChain(locale);

        Map<String, ArticleTranslation> available =
            repo.findByArticleIdAndLocaleIn(articleId, chain)
                .stream()
                .collect(Collectors.toMap(ArticleTranslation::getLocale, t -> t));

        return chain.stream()
            .map(available::get)
            .filter(Objects::nonNull)
            .findFirst();
    }

    @CacheEvict(value = "translations", key = "#articleId + ':' + #locale")
    public void updateTranslation(Long articleId, String locale, TranslationUpdateDto dto) {
        // 번역 수정 후 해당 locale 캐시 무효화
    }
}
```

캐시 키에 locale을 포함시키면 `ko-KR` 요청 결과와 `ko` 요청 결과가 별도로 캐싱된다. fallback 체인의 결과가 같더라도 캐시 항목이 분리되기 때문에 캐시 TTL과 메모리 용량을 감안해서 설계해야 한다.

번역 수정 시 캐시 무효화 범위를 좁히는 것이 중요하다. `ko` 번역을 수정했을 때 `ko-KR` 캐시도 무효화해야 한다면 fallback 체인을 역방향으로 추적해야 한다.

```java
@CacheEvict(value = "translations", allEntries = false)
public void evictLocaleAndDerivedLocales(Long articleId, String locale) {
    // ko 수정 시 ko-KR, ko-KP 등 파생 locale 캐시도 무효화
    cacheManager.getCache("translations")
        .evictIfPresent(articleId + ":" + locale);

    derivedLocalesOf(locale).forEach(derived ->
        cacheManager.getCache("translations")
            .evictIfPresent(articleId + ":" + derived)
    );
}
```

이 수준의 세밀한 무효화가 필요해지면 Redis의 키 패턴 삭제(`SCAN` + `DEL`)를 쓰거나, 아티클 단위로 전체 무효화하는 방식이 구현이 단순하다.
