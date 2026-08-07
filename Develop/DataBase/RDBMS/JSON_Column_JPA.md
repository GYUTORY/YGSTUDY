---
title: JSON 컬럼 JPA 매핑
tags: [database, jpa, hibernate, spring-boot, json, jackson, typeorm, attribute-converter, usertype]
updated: 2026-08-07
---

# JSON 컬럼 JPA 매핑

Spring Boot + JPA/Hibernate 환경에서 JSON 컬럼을 엔티티 필드에 매핑하는 방법은 Hibernate 버전에 따라 다르다. Hibernate 6부터는 공식 지원이 생겼고, 그 이전 버전에서는 `UserType`이나 `AttributeConverter`로 직접 처리해야 했다.

---

## Hibernate 6: @JdbcTypeCode(SqlTypes.JSON)

Hibernate 6(Spring Boot 3.x 기반)에서는 `@JdbcTypeCode(SqlTypes.JSON)` 하나로 JSON 컬럼을 매핑할 수 있다.

```java
@Entity
@Table(name = "orders")
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata", columnDefinition = "json")
    private OrderMetadata metadata;
}

public class OrderMetadata {
    private String channel;
    private String deviceType;
    private Map<String, String> tags;
    // getter, setter
}
```

`@JdbcTypeCode(SqlTypes.JSON)`을 붙이면 Hibernate가 Jackson을 통해 직렬화/역직렬화를 처리한다. `columnDefinition = "json"`은 DDL 생성 시 컬럼 타입을 명시하는 용도다. 없어도 동작하지만 Hibernate가 컬럼 타입을 `bytea`나 `text`로 만들 수 있다.

내부적으로 Hibernate 6은 classpath에 Jackson이 있으면 자동으로 `JacksonJsonFormatMapper`를 사용한다. `spring-boot-starter-web`이 있으면 Jackson이 포함되므로 별도 설정은 필요 없다.

PostgreSQL에서는 `json` 대신 `jsonb`를 쓰는 경우가 많다. 컬럼 타입만 `jsonb`로 바꾸면 된다.

```java
@JdbcTypeCode(SqlTypes.JSON)
@Column(name = "metadata", columnDefinition = "jsonb")
private OrderMetadata metadata;
```

Hibernate 6에서 `Map<String, Object>` 타입도 매핑된다. 스키마가 고정되지 않은 비정형 JSON을 다룰 때 쓴다.

```java
@JdbcTypeCode(SqlTypes.JSON)
@Column(name = "extra_fields", columnDefinition = "jsonb")
private Map<String, Object> extraFields;
```

---

## Hibernate 5: 커스텀 UserType

Hibernate 5 이하(Spring Boot 2.x)에서는 공식 JSON 타입 지원이 없다. `UserType` 인터페이스를 직접 구현해야 한다.

```java
public class JsonbType implements UserType<Object> {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public int getSqlType() {
        return Types.OTHER;
    }

    @Override
    public Class<Object> returnedClass() {
        return Object.class;
    }

    @Override
    public Object nullSafeGet(ResultSet rs, int position, SharedSessionContractImplementor session, Object owner)
            throws SQLException {
        String value = rs.getString(position);
        if (value == null) {
            return null;
        }
        try {
            return objectMapper.readValue(value, Object.class);
        } catch (JsonProcessingException e) {
            throw new HibernateException("JSON 역직렬화 실패", e);
        }
    }

    @Override
    public void nullSafeSet(PreparedStatement st, Object value, int index, SharedSessionContractImplementor session)
            throws SQLException {
        if (value == null) {
            st.setNull(index, Types.OTHER);
        } else {
            try {
                st.setObject(index, objectMapper.writeValueAsString(value), Types.OTHER);
            } catch (JsonProcessingException e) {
                throw new HibernateException("JSON 직렬화 실패", e);
            }
        }
    }

    @Override
    public boolean equals(Object x, Object y) {
        return Objects.equals(x, y);
    }

    @Override
    public int hashCode(Object x) {
        return Objects.hashCode(x);
    }

    @Override
    public Object deepCopy(Object value) {
        if (value == null) return null;
        try {
            return objectMapper.readValue(objectMapper.writeValueAsString(value), Object.class);
        } catch (JsonProcessingException e) {
            throw new HibernateException("deepCopy 실패", e);
        }
    }

    @Override
    public boolean isMutable() {
        return true;
    }

    @Override
    public Serializable disassemble(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException e) {
            throw new HibernateException("disassemble 실패", e);
        }
    }

    @Override
    public Object assemble(Serializable cached, Object owner) {
        try {
            return objectMapper.readValue((String) cached, Object.class);
        } catch (JsonProcessingException e) {
            throw new HibernateException("assemble 실패", e);
        }
    }
}
```

엔티티에서 사용할 때는 `@TypeDef`와 `@Type`을 조합한다.

```java
@TypeDef(name = "jsonb", typeClass = JsonbType.class)
@Entity
@Table(name = "orders")
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Type(type = "jsonb")
    @Column(name = "metadata", columnDefinition = "jsonb")
    private OrderMetadata metadata;
}
```

Hibernate 5에서 `UserType` 구현 시 `isMutable()`을 `true`로 두면 Hibernate가 dirty checking 시 `deepCopy()` 결과와 현재 값을 비교한다. `deepCopy()`가 제대로 구현되지 않으면 변경이 없어도 UPDATE 쿼리가 나가거나, 반대로 변경됐는데 UPDATE가 안 나가는 경우가 생긴다.

`vlad-mihalcea/hibernate-types` 라이브러리가 이 구현을 대신 제공한다. 직접 구현하는 것보다 이 라이브러리를 쓰는 경우가 더 많다.

```xml
<dependency>
    <groupId>com.vladmihalcea</groupId>
    <artifactId>hibernate-types-55</artifactId>
    <version>2.21.1</version>
</dependency>
```

```java
@TypeDef(name = "jsonb", typeClass = JsonBinaryType.class)
@Entity
public class Order {

    @Type(type = "jsonb")
    @Column(columnDefinition = "jsonb")
    private OrderMetadata metadata;
}
```

---

## AttributeConverter로 String 변환

`AttributeConverter`는 구현이 가장 단순하다. JPA 표준 스펙이라 Hibernate 버전에 무관하게 동작한다.

```java
@Converter
public class OrderMetadataConverter implements AttributeConverter<OrderMetadata, String> {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public String convertToDatabaseColumn(OrderMetadata attribute) {
        if (attribute == null) return null;
        try {
            return objectMapper.writeValueAsString(attribute);
        } catch (JsonProcessingException e) {
            throw new IllegalArgumentException("OrderMetadata 직렬화 실패", e);
        }
    }

    @Override
    public OrderMetadata convertToEntityAttribute(String dbData) {
        if (dbData == null) return null;
        try {
            return objectMapper.readValue(dbData, OrderMetadata.class);
        } catch (JsonProcessingException e) {
            throw new IllegalArgumentException("OrderMetadata 역직렬화 실패", e);
        }
    }
}
```

엔티티에서 `@Convert`로 지정한다.

```java
@Entity
public class Order {

    @Convert(converter = OrderMetadataConverter.class)
    @Column(name = "metadata", columnDefinition = "text")
    private OrderMetadata metadata;
}
```

`AttributeConverter`의 DB 컬럼 타입은 `text`나 `varchar`가 된다. PostgreSQL의 `json`/`jsonb` 타입이 아니라는 의미다. 따라서 PostgreSQL에서 `@>` 같은 JSON 연산자를 쓰거나 GIN 인덱스를 거는 게 불가능하다. DB에서 JSON 조건 검색이 필요 없고 단순히 직렬화/역직렬화만 필요하다면 `AttributeConverter`로 충분하다.

Converter 안에서 `new ObjectMapper()`로 매번 인스턴스를 만드는 경우가 있는데, ObjectMapper 생성 비용이 작지 않다. 인스턴스를 필드 레벨 상수로 두거나, Spring Bean으로 주입받아서 쓴다.

```java
@Converter
@Component
public class OrderMetadataConverter implements AttributeConverter<OrderMetadata, String> {

    @Autowired
    private ObjectMapper objectMapper;  // Spring 관리 ObjectMapper 주입

    // ...
}
```

`@Converter(autoApply = true)`를 붙이면 `@Convert` 없이도 해당 타입에 자동 적용된다. 타입이 명확하게 하나의 컨버터와 매핑될 때만 쓴다. 여러 컨버터가 같은 타입을 대상으로 하면 충돌이 난다.

---

## Jackson ObjectMapper 설정과 역직렬화 실패

### 알 수 없는 필드 처리

기본 ObjectMapper는 `FAIL_ON_UNKNOWN_PROPERTIES`가 `true`다. JSON에 클래스에 없는 필드가 있으면 역직렬화 시 `UnrecognizedPropertyException`이 발생한다.

배포 중 새 필드를 JSON에 추가하면, 그 JSON을 읽는 구버전 클래스가 예외를 던진다. 롤링 업데이트 환경에서 신버전 서버가 먼저 뜨면서 DB에 새 필드가 포함된 JSON을 쓰고, 아직 살아있는 구버전 서버가 그 JSON을 읽다가 터지는 상황이다.

```java
@JsonIgnoreProperties(ignoreUnknown = true)
public class OrderMetadata {
    private String channel;
    private String deviceType;
    // 새 버전에서 추가된 필드 - 구버전에서는 이 필드가 없음
    // private String couponCode;
}
```

`@JsonIgnoreProperties(ignoreUnknown = true)`를 DTO 클래스에 붙이거나, ObjectMapper 레벨에서 비활성화한다.

```java
@Bean
public ObjectMapper objectMapper() {
    return JsonMapper.builder()
        .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
        .build();
}
```

### 롤링 업데이트 시나리오

v1 → v2 배포를 롤링으로 진행할 때 JSON 스키마 변경이 문제가 된다.

상황 1: 필드 추가. v2가 쓴 JSON(새 필드 포함)을 v1이 읽는다. `@JsonIgnoreProperties(ignoreUnknown = true)` 없으면 v1이 터진다.

상황 2: 필드 제거. v2가 특정 필드를 제거한 상태로 JSON을 쓰면, 그 필드를 기대하는 v1이 null을 받는다. v1 로직에서 null 처리가 안 돼 있으면 NPE가 난다.

상황 3: 필드 타입 변경. `"count": 5`에서 `"count": "five"`로 바뀌면 타입 불일치로 역직렬화 자체가 실패한다. 이건 `@JsonIgnoreProperties`로 막을 수 없다.

롤링 업데이트 기간 동안 구버전과 신버전이 같은 DB를 공유한다는 전제를 항상 의식해야 한다. JSON 스키마 변경은 필드 추가만 허용하고, 삭제나 타입 변경은 두 버전에 걸쳐 단계적으로 처리한다.

필드를 제거하는 순서는 다음과 같다.

1. v2 배포: 코드에서 해당 필드 사용을 제거하되, 클래스에는 남긴다 (`@JsonIgnoreProperties`로 무시).
2. 구버전 서버 완전 종료 확인.
3. v3 배포: 클래스에서 필드를 완전히 제거.

### LocalDateTime 직렬화 문제

Java 8 날짜 타입을 JSON에 담으면 ObjectMapper 설정에 따라 배열로 직렬화되는 경우가 있다.

```json
// JavaTimeModule 없이 직렬화
{ "createdAt": [2026, 8, 7, 15, 30, 0] }

// JavaTimeModule 추가 후
{ "createdAt": "2026-08-07T15:30:00" }
```

`WRITE_DATES_AS_TIMESTAMPS` 비활성화와 `JavaTimeModule` 등록이 빠지면 DB에 배열 형태로 저장된다. 나중에 설정을 바꾸면 기존 데이터를 읽지 못한다.

```java
@Bean
public ObjectMapper objectMapper() {
    return JsonMapper.builder()
        .addModule(new JavaTimeModule())
        .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)
        .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
        .build();
}
```

---

## JPQL에서 JSON 컬럼 조건 쿼리의 한계

JPQL은 JSON 내부 필드를 조건으로 쓰는 문법이 없다. `metadata.channel = 'app'` 같은 경로 표현식은 JPQL에서 지원하지 않는다.

Spring Data JPA의 `@Query`에서 JPQL로 JSON 필드 조건을 쓰려고 하면 파싱 오류가 난다.

```java
// 이렇게 하면 안 된다
@Query("SELECT o FROM Order o WHERE o.metadata.channel = :channel")
List<Order> findByChannel(String channel);
```

### Native Query로 우회

Native Query를 써야 한다.

```java
@Query(value = "SELECT * FROM orders WHERE metadata->>'channel' = :channel", nativeQuery = true)
List<Order> findByChannel(@Param("channel") String channel);

@Query(value = "SELECT * FROM orders WHERE metadata @> :filter::jsonb", nativeQuery = true)
List<Order> findByMetadataContains(@Param("filter") String filter);
```

`nativeQuery = true`로 PostgreSQL JSON 연산자를 직접 쓴다. `::jsonb` 캐스팅을 빠뜨리면 PostgreSQL이 파라미터 타입을 `text`로 처리해서 `@>` 연산자를 못 쓴다.

```java
// 서비스에서 호출
String filter = "{\"channel\": \"app\"}";
List<Order> orders = orderRepository.findByMetadataContains(filter);
```

`EntityManager`로 직접 Native Query를 쓰는 방식도 있다.

```java
@Repository
@RequiredArgsConstructor
public class OrderJsonQueryRepository {

    @PersistenceContext
    private final EntityManager entityManager;

    public List<Order> findByChannel(String channel) {
        String sql = "SELECT * FROM orders WHERE metadata->>'channel' = :channel";
        return entityManager.createNativeQuery(sql, Order.class)
            .setParameter("channel", channel)
            .getResultList();
    }

    public List<Order> findByTagContains(String tagValue) {
        String sql = "SELECT * FROM orders WHERE metadata @> CAST(:filter AS jsonb)";
        String filter = String.format("{\"tags\": [\"%s\"]}", tagValue);
        return entityManager.createNativeQuery(sql, Order.class)
            .setParameter("filter", filter)
            .getResultList();
    }
}
```

Native Query의 결과를 `Order.class`로 매핑할 때, JSON 컬럼이 `@JdbcTypeCode(SqlTypes.JSON)`으로 매핑돼 있으면 Hibernate가 자동으로 역직렬화한다. `AttributeConverter`를 쓴 경우에도 마찬가지다.

### Querydsl에서 JSON 조건

Querydsl JPQL은 Native SQL로 내려가지 않는 한 JSON 경로 표현식을 지원하지 않는다. `JPASQLQuery`를 쓰면 Native SQL을 Querydsl 방식으로 작성할 수 있다.

```java
public List<Order> findByChannel(String channel) {
    QOrder order = QOrder.order;

    // JPQL 기반 JPAQuery로는 JSON 조건 불가
    // Native SQL 기반 JPASQLQuery를 써야 한다
    return queryFactory
        .selectFrom(order)
        .fetch()
        .stream()
        .filter(o -> channel.equals(
            o.getMetadata() != null ? o.getMetadata().getChannel() : null
        ))
        .toList();  // 전체 조회 후 애플리케이션 레벨 필터 - 대용량에서 쓰면 안 된다
}
```

JSON 조건 검색이 자주 필요하다면 Native Query가 현실적인 방법이다. JSON 내 특정 필드를 자주 검색한다면 해당 필드를 별도 컬럼으로 추출해서 B-Tree 인덱스를 거는 편이 낫다.

---

## TypeORM에서 JSON 컬럼 매핑

TypeORM에서는 `@Column({ type: 'json' })`이나 `@Column({ type: 'jsonb' })`으로 JSON 컬럼을 선언한다.

```typescript
@Entity()
export class Order {
    @PrimaryGeneratedColumn()
    id: number;

    @Column({ type: 'jsonb', nullable: true })
    metadata: OrderMetadata;
}

export interface OrderMetadata {
    channel: string;
    deviceType: string;
    tags?: string[];
}
```

TypeORM은 JavaScript/TypeScript 객체를 그대로 직렬화/역직렬화한다. JPA + Hibernate처럼 별도 타입 등록이나 컨버터가 필요 없다. 단, 타입 안전성은 TypeScript 컴파일 타임에만 보장된다. 실제 DB 값이 `OrderMetadata` 인터페이스와 다른 형태로 저장돼 있어도 TypeORM은 오류를 내지 않는다.

### JSON 조건 쿼리

TypeORM QueryBuilder에서 JSON 조건을 쓸 때는 파라미터를 직접 JSON 경로 표현식에 넣어야 한다.

```typescript
// 단순 키-값 조건
const orders = await dataSource
    .getRepository(Order)
    .createQueryBuilder('order')
    .where("order.metadata->>'channel' = :channel", { channel: 'app' })
    .getMany();

// containment 연산자
const orders = await dataSource
    .getRepository(Order)
    .createQueryBuilder('order')
    .where('order.metadata @> :filter::jsonb', {
        filter: JSON.stringify({ channel: 'app' })
    })
    .getMany();
```

TypeORM에서 `::jsonb` 캐스팅이 필요한 이유는 JPA와 동일하다. 바인딩 파라미터를 `text`로 처리하기 때문에 `@>` 연산자가 타입 불일치로 실패한다.

### JPA와의 동작 차이

| 항목 | JPA/Hibernate | TypeORM |
|---|---|---|
| 직렬화 | Jackson ObjectMapper | JSON.stringify |
| 역직렬화 | Jackson ObjectMapper | JSON.parse |
| 알 수 없는 필드 | `FAIL_ON_UNKNOWN_PROPERTIES` 설정에 따라 | 무시 (기본) |
| 날짜 타입 | `JavaTimeModule` 설정 필요 | Date 객체 직렬화 시 ISO 문자열 |
| JSON 조건 쿼리 | Native Query 필요 | QueryBuilder에서 Raw SQL 필요 |
| 타입 검증 | 역직렬화 시 타입 불일치 예외 가능 | 런타임 타입 검증 없음 |

TypeORM에서 `null`과 `undefined`의 처리 방식이 JPA와 다르다. TypeScript에서 `undefined` 필드는 `JSON.stringify` 시 키 자체가 제거된다. JPA에서는 `null` 필드가 JSON에 `"field": null`로 남거나, `@JsonInclude(NON_NULL)` 설정에 따라 제거된다. 두 시스템이 같은 DB를 공유한다면 이 차이가 역직렬화 결과에 영향을 준다.

---

## 실제로 겪은 문제

### Hibernate 캐시와 JSON 변경 감지

`isMutable()`을 `true`로 설정한 `UserType`에서 JSON 객체의 내부 상태를 변경하면 Hibernate dirty checking이 감지하지 못하는 경우가 있다. `deepCopy()` 구현이 올바르게 복사본을 만들지 않으면, Hibernate 1차 캐시에 저장된 스냅샷과 현재 객체가 같은 참조를 가리켜서 변경 감지가 작동하지 않는다.

```java
Order order = orderRepository.findById(id).orElseThrow();
order.getMetadata().setChannel("web");  // 내부 상태 변경
// transaction commit 시 UPDATE가 안 나갈 수 있다
```

이 경우 새 객체를 할당하면 dirty checking이 정상 동작한다.

```java
OrderMetadata updated = new OrderMetadata();
updated.setChannel("web");
updated.setDeviceType(order.getMetadata().getDeviceType());
order.setMetadata(updated);
```

Hibernate 6의 `@JdbcTypeCode(SqlTypes.JSON)`은 이 문제가 없다. Hibernate 6이 객체 동등성 비교를 Jackson으로 처리하기 때문이다.

### Native Query 결과 매핑 실패

Native Query에서 JSON 컬럼을 포함한 엔티티를 반환할 때, `AttributeConverter`가 동작하지 않는 경우가 있다. 특히 `createNativeQuery(sql, Object[].class)`처럼 raw 형태로 받으면 컨버터가 적용되지 않는다.

```java
// 이렇게 하면 metadata가 String으로 반환된다
List<Object[]> rows = entityManager
    .createNativeQuery("SELECT id, metadata FROM orders")
    .getResultList();

// 엔티티 클래스를 명시해야 컨버터가 적용된다
List<Order> orders = entityManager
    .createNativeQuery("SELECT * FROM orders WHERE ...", Order.class)
    .getResultList();
```

`resultClass`로 엔티티 타입을 명시해야 Hibernate가 컬럼 매핑 과정에서 컨버터를 적용한다.

---

## 관련 문서

- Postgre_SQL_JSONB.md — PostgreSQL JSONB 연산자, GIN 인덱스, jsonpath 쿼리
- Tenant_Column_JPA.md — 테넌트 컬럼 기반 멀티테넌시 JPA 구현
