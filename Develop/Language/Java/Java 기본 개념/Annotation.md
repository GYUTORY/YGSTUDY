---
title: "Java Annotation"
tags: [java, annotation, reflection, spring, lombok, annotation-processor]
updated: 2026-05-03
---

# Java Annotation

## 어노테이션이란

어노테이션은 코드에 메타데이터를 붙이는 문법이다. 메서드·클래스·필드·파라미터 위에 `@이름` 형태로 적는다. 어노테이션 자체는 코드의 동작을 바꾸지 않는다. 그저 "여기에 이런 표시가 붙어 있다"는 정보를 코드에 새겨 넣을 뿐이다. 의미를 부여하는 건 어노테이션을 읽는 쪽 — 컴파일러, 어노테이션 프로세서, 또는 런타임에 리플렉션으로 읽는 프레임워크 — 의 몫이다.

```java
@Override
public String toString() {
    return "example";
}
```

`@Override`는 컴파일러가 부모 클래스에 같은 시그니처의 메서드가 있는지 확인한다. 없으면 컴파일 에러를 낸다. 즉 `@Override`라는 글자 자체가 뭘 하는 게 아니라, 컴파일러 안에 `@Override`를 보면 부모 메서드를 검사하는 로직이 박혀 있는 것이다. 어노테이션의 동작 모델은 다 이런 식이다.

---

## 어노테이션은 누가 처리하는가

어노테이션은 처리 시점에 따라 두 갈래로 나뉜다. 이 구분을 명확히 잡지 않으면 디버깅할 때 엉뚱한 곳을 뒤지게 된다.

| 처리 주체 | 시점 | RetentionPolicy | 대표 예시 |
|-----------|------|-----------------|-----------|
| 컴파일러 자체 | 컴파일 타임 | SOURCE | `@Override`, `@Deprecated`, `@SuppressWarnings` |
| 어노테이션 프로세서 | 컴파일 타임(javac 단계) | SOURCE 또는 CLASS | Lombok, MapStruct, AutoValue, Dagger, QueryDSL |
| 리플렉션 | 런타임 | RUNTIME | Spring `@Component`, JPA `@Entity`, JUnit `@Test` |

가장 자주 헷갈리는 부분이 Lombok과 Spring의 차이다. 둘 다 "어노테이션 기반"이라고 묶어서 부르지만 동작 시점이 완전히 다르다.

Lombok의 `@Getter`는 javac이 컴파일하는 도중에 끼어들어 AST(추상 구문 트리)에 getter 메서드를 직접 만들어 넣는다. 그래서 컴파일이 끝난 `.class` 파일을 디컴파일하면 실제로 `getXxx()` 메서드가 들어 있다. 런타임에는 `@Getter`라는 어노테이션이 클래스에 남아 있지도 않다(SOURCE 정책).

Spring의 `@Component`는 정반대다. 컴파일 시점에는 아무것도 안 하고 `.class` 파일에 어노테이션 정보만 남아 있다. 애플리케이션이 뜰 때 Spring이 클래스패스를 스캔하면서 리플렉션으로 `@Component`가 붙은 클래스를 찾아 빈으로 등록한다.

이 둘을 구분하는 가장 빠른 방법은 RetentionPolicy를 보는 것이다. `RUNTIME`이면 리플렉션 기반, `SOURCE`나 `CLASS`면 컴파일 시점 처리다.

---

## 메타 어노테이션 — 어노테이션을 위한 어노테이션

커스텀 어노테이션을 만들 때 그 어노테이션 자체에 붙이는 어노테이션을 메타 어노테이션이라고 부른다. JDK가 제공하는 메타 어노테이션은 네 개가 핵심이다.

### @Retention — 어노테이션의 생존 범위

```java
@Retention(RetentionPolicy.SOURCE)   // 소스 코드까지만. 컴파일하면 사라진다.
@Retention(RetentionPolicy.CLASS)    // .class 파일까지. 런타임엔 못 읽는다. (기본값)
@Retention(RetentionPolicy.RUNTIME)  // 런타임까지. 리플렉션으로 읽을 수 있다.
```

`SOURCE`는 컴파일러나 어노테이션 프로세서가 컴파일 도중에만 보고 그 뒤로는 흔적이 사라진다. `@Override`, `@SuppressWarnings`, Lombok의 `@Getter`가 여기 속한다.

`CLASS`는 `.class` 파일에는 기록되지만 JVM이 클래스를 로드할 때 메모리에 올리지 않는다. 그래서 리플렉션으로 읽을 수 없다. 바이트코드 직접 분석 도구(ASM, ByteBuddy)에서 가끔 쓰지만 일반 애플리케이션 코드에서 직접 다룰 일은 거의 없다. 명시적으로 `@Retention`을 안 붙이면 기본값이 이것이다 — 이 점이 함정이다.

`RUNTIME`은 클래스 메타데이터에 살아남아 `Class.getAnnotation()` 같은 리플렉션 API로 읽을 수 있다. Spring, JPA, JUnit, Jackson 같이 런타임에 메타데이터를 보고 동작하는 모든 프레임워크의 어노테이션이 여기에 해당한다. 직접 만드는 커스텀 어노테이션은 십중팔구 `RUNTIME`이다.

### @Target — 붙일 수 있는 위치 제한

```java
@Target(ElementType.METHOD)              // 메서드에만
@Target(ElementType.TYPE)                // 클래스, 인터페이스, enum, 어노테이션
@Target(ElementType.FIELD)               // 필드
@Target(ElementType.PARAMETER)           // 메서드 파라미터
@Target(ElementType.CONSTRUCTOR)         // 생성자
@Target(ElementType.ANNOTATION_TYPE)     // 메타 어노테이션용
@Target(ElementType.PACKAGE)             // package-info.java
@Target(ElementType.TYPE_PARAMETER)      // 제네릭 타입 파라미터 (Java 8+)
@Target(ElementType.TYPE_USE)            // 타입이 쓰이는 모든 위치 (Java 8+)
@Target({ElementType.TYPE, ElementType.METHOD})  // 복수 지정
```

`@Target`을 생략하면 어디든 붙일 수 있다. 그렇다고 편리한 게 아니라 의도가 모호해진다. 메서드에만 의미 있는 어노테이션을 누군가 클래스에 붙여 놓고 "왜 안 먹히지?"라고 물어 보면 답해 주기가 곤란하다. 명시적으로 좁혀 놓는 게 맞다.

`TYPE_USE`는 Java 8에서 추가된 위치인데 자주 쓰지는 않는다. `List<@NonNull String>`처럼 타입이 등장하는 모든 자리에 어노테이션을 붙일 수 있게 해 준다. Checker Framework 같은 정적 분석 도구가 이걸 활용한다.

### @Documented — Javadoc에 포함시키기

```java
@Documented
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface Audited {
}
```

`@Documented`를 붙이면 Javadoc 생성 시 해당 어노테이션이 메서드·클래스 시그니처 옆에 같이 출력된다. 안 붙이면 Javadoc에서는 어노테이션이 보이지 않는다.

내부 구현에는 영향이 없다. 순수하게 문서화 의도만 반영하는 마커다. 라이브러리를 만들어 외부에 공개하는 어노테이션이라면 거의 항상 같이 붙인다. 사용자가 Javadoc만 보고도 "이 메서드는 인증이 필요하다" 같은 정보를 알 수 있어야 하기 때문이다.

사내에서만 쓰는 어노테이션이라면 굳이 안 붙이는 경우가 많다. Javadoc을 따로 빌드하지 않으면 의미가 없으니까.

### @Inherited — 상속 시 자동 전파

```java
@Inherited
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface Auditable {
}

@Auditable
public class BaseEntity { }

public class UserEntity extends BaseEntity { }
// userEntity.getClass().isAnnotationPresent(Auditable.class) == true
```

`@Inherited`가 붙은 어노테이션은 부모 클래스에 적용했을 때 자식 클래스에도 자동으로 전파된다. 정확히 말하면 자식 클래스의 메타데이터에 복사되는 게 아니라, `Class.getAnnotation()`이 부모 클래스를 거슬러 올라가며 찾는 동작이 추가된다.

여기서 중요한 두 가지 제약이 있다.

첫째, **클래스에만 동작한다.** `@Target(ElementType.METHOD)`인 어노테이션에 `@Inherited`를 붙여도 메서드 오버라이딩 시에는 전파되지 않는다. 이건 자바 언어 명세상의 결정이다.

둘째, **인터페이스에는 동작하지 않는다.** 클래스 → 클래스 상속에만 작동한다. `implements`로 인터페이스를 구현하는 경우는 무시된다. Spring 같은 프레임워크가 자체적으로 `AnnotatedElementUtils.findMergedAnnotation()` 같은 유틸리티를 제공하는 건 이 한계를 우회하기 위해서다. Spring 안에서는 인터페이스의 어노테이션도 따라 올라가서 찾는다.

---

## 커스텀 어노테이션 만들기

### 기본 구조

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface LogExecutionTime {
}
```

`@interface`가 어노테이션 선언이다. `interface`가 아니라 `@interface`라는 점에서 처음에 자주 헷갈린다. 컴파일러는 `@interface`로 선언된 타입을 자동으로 `java.lang.annotation.Annotation` 인터페이스를 상속한 것으로 취급한다. 그래서 `Annotation`을 직접 `extends`할 수는 없고 `@interface` 문법으로만 만들 수 있다.

### 속성(elements) 정의

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface RateLimit {
    int maxRequests() default 100;
    long windowSeconds() default 60;
    String key() default "";
}
```

```java
@RateLimit(maxRequests = 10, windowSeconds = 30, key = "send-verification")
public ResponseEntity<?> sendVerification() {
    // ...
}
```

속성은 메서드처럼 선언하지만 실제로는 어노테이션이 가진 값에 접근하는 통로다. 사용 시점에 값을 지정하지 않으려면 `default`를 줘야 한다. `default`가 없는 속성은 어노테이션을 사용할 때 반드시 값을 지정해야 한다.

속성 타입은 다음 중 하나여야 한다.

- 기본형(`int`, `long`, `boolean`, `double` 등)
- `String`
- `Class` 또는 `Class<? extends X>`
- enum
- 다른 어노테이션 타입
- 위 타입들의 1차원 배열

`List`, `Map`, 일반 객체는 안 된다. 컴파일러가 어노테이션 값을 클래스 파일의 상수 풀에 인라인으로 박아 넣어야 하는데, 임의의 객체는 직렬화 형태가 정해져 있지 않아서다. 배열은 1차원만 허용된다. 2차원 배열이 필요하면 다른 어노테이션을 한 단계 감싸는 식으로 우회해야 한다.

### value 속성 — 단축 표기

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.FIELD)
public @interface Column {
    String value();
}
```

```java
@Column("user_name")          // value = "user_name"과 동일
private String userName;
```

속성 이름이 정확히 `value`이고 다른 속성이 모두 `default`를 갖고 있을 때만 이 단축 표기가 가능하다. 한 가지 값만 받는 어노테이션이면 거의 관행적으로 `value`로 짓는다. JPA의 `@Column`, Spring의 `@Qualifier`, JUnit 4의 `@RunWith`이 다 이 패턴이다.

### 배열 속성

```java
public @interface Roles {
    String[] value();
}
```

```java
@Roles({"ADMIN", "USER"})    // 여러 개
@Roles("ADMIN")              // 한 개일 때는 배열 표기 생략 가능
```

원소가 하나일 때 중괄호를 생략할 수 있다는 문법 설탕도 있다.

---

## 리플렉션으로 어노테이션 읽기

`RUNTIME` 보존 정책이어야 리플렉션 API로 읽을 수 있다. `CLASS`나 `SOURCE`로 만든 어노테이션은 런타임에 존재하지 않으므로 `getAnnotation()`이 항상 `null`을 반환한다.

```java
public class AnnotationReader {

    public static void main(String[] args) throws Exception {
        Method method = OrderService.class.getMethod("createOrder", OrderRequest.class);

        if (method.isAnnotationPresent(RateLimit.class)) {
            RateLimit rateLimit = method.getAnnotation(RateLimit.class);
            System.out.println("maxRequests: " + rateLimit.maxRequests());
            System.out.println("windowSeconds: " + rateLimit.windowSeconds());
        }
    }
}
```

`getAnnotation()`이 반환하는 `RateLimit` 객체는 JVM이 동적으로 만든 프록시 객체다. `Proxy.newProxyInstance()`로 만든 것과 비슷한 동적 프록시이며, 메서드 호출이 들어오면 컴파일 시점에 박아 둔 상수 값을 돌려준다. 그래서 `rateLimit.maxRequests()`는 100이라는 값을 매번 새로 계산하지 않고 그냥 반환한다.

```java
for (Field field : clazz.getDeclaredFields()) {
    Column column = field.getAnnotation(Column.class);
    if (column != null) {
        String columnName = column.value();
        // 매핑 처리
    }
}
```

`getDeclaredFields()`는 그 클래스에 직접 선언된 필드만 본다. 부모 클래스에서 상속받은 필드는 포함하지 않는다. 상속 구조까지 훑으려면 `clazz = clazz.getSuperclass()`를 따라가며 반복해야 한다.

---

## 어노테이션 프로세서 동작 원리

리플렉션 기반 처리는 단순하다. 클래스가 로드된 뒤 `Class` 객체를 얻고 메타데이터를 꺼내 보면 끝이다. 어노테이션 프로세서는 이야기가 완전히 다르다. 컴파일이 진행되는 동안 javac 안에 끼어들어 동작한다.

### JSR 269 — javac의 확장 포인트

자바 6부터 정식으로 들어온 JSR 269 명세에 따라, javac은 컴파일 도중 다음 순서로 동작한다.

```
1. 소스 파일 파싱 → AST 생성
2. 어노테이션 프로세서 실행 (이 단계에서 새 소스 파일을 만들 수 있음)
3. 새로 생성된 소스가 있으면 다시 1번부터 — 이 사이클을 "라운드"라고 부른다
4. 더 생성될 게 없으면 타입 체크 → 바이트코드 생성
```

어노테이션 프로세서는 이 사이클의 2번 단계에 끼어드는 javac 플러그인이다. 자바로 작성하지만 javac이 컴파일하는 코드를 들여다보고 새 코드를 만들어 낼 수 있다.

### 프로세서 골격

```java
@SupportedAnnotationTypes("com.example.GenerateBuilder")
@SupportedSourceVersion(SourceVersion.RELEASE_17)
public class BuilderProcessor extends AbstractProcessor {

    @Override
    public boolean process(Set<? extends TypeElement> annotations,
                           RoundEnvironment roundEnv) {
        for (Element element : roundEnv.getElementsAnnotatedWith(GenerateBuilder.class)) {
            if (element.getKind() != ElementKind.CLASS) continue;
            TypeElement classElement = (TypeElement) element;
            generateBuilderClass(classElement);
        }
        return true;  // 다른 프로세서가 이 어노테이션을 또 처리할 필요가 없음
    }

    private void generateBuilderClass(TypeElement classElement) {
        String packageName = processingEnv.getElementUtils()
                .getPackageOf(classElement).toString();
        String builderName = classElement.getSimpleName() + "Builder";

        try {
            JavaFileObject file = processingEnv.getFiler()
                    .createSourceFile(packageName + "." + builderName);
            try (Writer writer = file.openWriter()) {
                writer.write("package " + packageName + ";\n");
                writer.write("public class " + builderName + " { /* ... */ }\n");
            }
        } catch (IOException e) {
            processingEnv.getMessager()
                    .printMessage(Kind.ERROR, e.getMessage());
        }
    }
}
```

여기서 등장하는 핵심 객체 세 개가 있다.

**ProcessingEnvironment**는 프로세서가 javac과 대화하는 통로다. 새 파일을 만들고(`Filer`), 메시지를 출력하고(`Messager`), 타입 정보를 조회하는(`Elements`, `Types`) 도구를 제공한다.

**RoundEnvironment**는 한 라운드 동안의 작업 공간이다. 이번 라운드에서 처리할 어노테이션이 붙은 요소들을 들고 있다.

**Element**는 컴파일 중인 코드의 추상화된 표현이다. `Class`가 아니라 `Element`인 이유는, 프로세서가 동작하는 시점에 클래스가 아직 메모리에 로드되지 않았기 때문이다. 컴파일 중인 소스 코드는 `TypeElement`(클래스), `ExecutableElement`(메서드), `VariableElement`(필드/파라미터) 같은 인터페이스로 표현된다. `getKind()`로 종류를 확인하고 다운캐스트해서 쓴다.

### 라운드 개념

프로세서가 새 소스 파일을 만들면 javac은 다시 컴파일 사이클을 돌려야 한다. 새로 생긴 코드에도 처리할 어노테이션이 있을 수 있기 때문이다. 이 반복 단위를 "라운드"라고 부른다. 새 파일이 더 안 만들어지면 마지막 "verification round"가 한 번 돌고 끝난다.

이 구조 때문에 프로세서를 짜다가 `Attempt to recreate a file for type X` 같은 에러를 자주 만난다. 같은 라운드에서 같은 이름의 파일을 두 번 만들려고 할 때 발생한다. 보통 `processingOver()`로 마지막 라운드를 체크하거나, 상태 플래그를 둬서 한 번만 생성하도록 막는다.

### 프로세서 등록 방식

```
src/main/resources/META-INF/services/javax.annotation.processing.Processor
```

이 파일에 프로세서의 FQCN을 한 줄씩 적는다. javac이 클래스패스에서 이 SPI 파일을 읽고 등록된 프로세서를 자동으로 실행한다. 빌드 도구마다 이 등록을 자동화하는 방법이 다르다. Gradle은 `annotationProcessor` 의존성으로, Maven은 `<annotationProcessorPaths>`로 지정한다. 일반 `implementation`이나 `compile`로 넣으면 동작은 하지만 클래스패스에 의존성이 같이 섞여 들어가는 부작용이 있다.

수동으로 SPI 파일을 만들기 귀찮으면 Google의 `auto-service` 라이브러리에 있는 `@AutoService(Processor.class)`를 붙여 두면 된다. 이 어노테이션 자체가 또 다른 프로세서가 되어 `META-INF/services` 파일을 자동 생성한다. 어노테이션 프로세서로 어노테이션 프로세서 등록을 자동화하는 셈이다.

---

## Lombok 내부 구조

Lombok은 표준 어노테이션 프로세서가 아니다. 정확히는 표준 SPI를 통해 등록되긴 하지만, 안에서 하는 일이 명세를 벗어난다.

표준 프로세서는 새 파일을 "만드는" 것만 허용된다. 이미 컴파일 중인 클래스의 본문에 메서드를 추가하는 것은 명세상 불가능하다. `Filer.createSourceFile()`은 새 파일을 만들 뿐이고, 기존 클래스를 수정하는 API는 제공되지 않는다. 그런데 Lombok의 `@Getter`는 분명히 기존 클래스에 getter를 끼워 넣는다. 어떻게 가능한가.

답은 javac 내부 구조에 직접 손을 댄다는 것이다. javac은 내부적으로 컴파일 중인 코드를 `JCTree`라는 자체 AST 클래스로 들고 있다. 이건 표준 API가 아니라 OpenJDK 구현체의 내부 클래스다. Lombok은 이 `JCTree`에 직접 접근해서 노드를 추가·수정한다.

```
표준 프로세서 (MapStruct, AutoValue)
    ↓
JavaFileObject.createSourceFile()로 새 .java 파일 생성
    ↓
javac이 다음 라운드에서 이 파일도 같이 컴파일

Lombok
    ↓
JavacAnnotationHandler가 javac의 JCTree에 직접 메서드 노드 추가
    ↓
같은 클래스의 AST가 변형된 채로 컴파일 진행
```

Lombok 소스 코드를 보면 `JavacAnnotationHandler`(javac용), `EclipseAnnotationHandler`(이클립스 컴파일러용)가 컴파일러별로 따로 구현돼 있다. 각 컴파일러의 내부 AST가 다르기 때문이다. 그래서 Lombok은 사실상 컴파일러마다 별도의 어댑터를 들고 있는 셈이다.

이런 구조 때문에 Lombok에는 몇 가지 특유의 문제가 있다.

JDK 메이저 버전이 올라갈 때마다 javac의 내부 구현이 바뀌어 Lombok이 깨진다. JDK 9에서 모듈 시스템(Jigsaw)이 들어오면서 내부 패키지 접근이 막혀 Lombok이 한참 깨졌다가, `--add-opens` 플래그로 내부 패키지를 강제로 열어 주는 식으로 우회하고 있다.

IDE는 javac으로 빌드하지 않고 자체 컴파일러를 쓴다. 그래서 Lombok 플러그인을 따로 깔지 않으면 IDE에서 getter가 빨갛게 보인다. IDE 컴파일러용 핸들러가 별도로 끼어들어야 동작한다.

Lombok 어노테이션의 RetentionPolicy가 모두 `SOURCE`인 것도 이 구조에서 나온다. 컴파일이 끝난 시점에는 이미 AST에 메서드가 박혀 있으니, `.class` 파일에 `@Getter` 어노테이션 자체를 남길 이유가 없다. 그래서 런타임에 `field.isAnnotationPresent(Getter.class)` 같은 코드를 짜도 절대로 `true`가 나오지 않는다.

---

## Spring 어노테이션 내부 구조

Spring 어노테이션은 거의 전부 `RUNTIME` 보존이다. 컨테이너 초기화 시점에 리플렉션으로 클래스를 훑어 어노테이션을 읽고, 그에 따라 빈 등록·AOP 프록시 생성·트랜잭션 처리 등을 결정한다. 다만 표준 리플렉션 API만 쓰지는 않는다. Spring 자체적인 어노테이션 처리 계층을 한 겹 더 쌓아 두었다.

### 메타 어노테이션 재귀 탐색

표준 자바 리플렉션의 `getAnnotation(Service.class)`은 클래스에 `@Service`가 직접 붙어 있을 때만 반환한다. `@Service`를 메타 어노테이션으로 가진 다른 어노테이션이 붙어 있어도 모른다.

Spring은 이걸 `AnnotatedElementUtils.findMergedAnnotation()` 같은 유틸리티로 우회한다. 어노테이션의 어노테이션의 어노테이션까지 재귀적으로 탐색한다.

```java
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Service
@Transactional(readOnly = true)
public @interface ReadOnlyService {
}

@ReadOnlyService
public class ProductQueryService {
    public Product findById(Long id) {
        return productRepository.findById(id).orElseThrow();
    }
}
```

`@ReadOnlyService`에는 `@Service`가 메타 어노테이션으로 붙어 있다. Spring 컨테이너는 클래스패스 스캔 도중 `ProductQueryService`를 만나면 `@ReadOnlyService` → `@Service`까지 따라 올라가 빈으로 등록한다. `@SpringBootApplication`이 안에 `@Configuration`, `@EnableAutoConfiguration`, `@ComponentScan`을 품고 있는 것도 같은 메커니즘이다.

### MergedAnnotations와 @AliasFor

Spring 5부터는 `MergedAnnotations` API로 메타 어노테이션 처리를 통일했다. 이전에는 어노테이션을 종류별로 따로 처리하는 코드가 여기저기 흩어져 있었지만, 이제는 한 군데로 모았다.

`@AliasFor`는 메타 어노테이션의 속성을 자식 어노테이션에서 별칭으로 노출하는 장치다.

```java
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Component
public @interface MyService {

    @AliasFor(annotation = Component.class, attribute = "value")
    String name() default "";
}

@MyService(name = "userService")
public class UserService { }
```

`@MyService(name = "userService")`로 적은 값이 내부적으로 `@Component(value = "userService")`와 동일하게 처리된다. Spring 코어 어노테이션은 이 패턴을 광범위하게 쓴다. `@RestController`의 `value` 속성이 `@Controller`의 `value`로 매핑되는 식이다.

### AnnotationMetadata — Class 없이 메타데이터만 읽기

Spring Boot의 자동 설정은 클래스를 직접 로드하지 않고 어노테이션 정보만 읽어야 할 때가 있다. 클래스를 무조건 로드하면 의존성 클래스가 클래스패스에 없을 때 `NoClassDefFoundError`가 터진다. `@ConditionalOnClass`가 동작할 수가 없다.

이 때문에 Spring은 ASM 라이브러리로 `.class` 파일의 바이트코드만 읽어 어노테이션 정보를 추출한다. 그 결과가 `AnnotationMetadata` 객체다. 클래스를 JVM에 로드하지 않은 채로 "이 클래스에 `@Component`가 붙어 있는가"를 답할 수 있다. `ClassPathScanningCandidateComponentProvider`가 클래스패스를 훑을 때 이 방식으로 후보 클래스를 추려 낸다.

### Spring AOP는 동적 프록시다

`@Transactional`이나 직접 만든 AOP 어노테이션이 동작하는 원리도 짚어 둘 가치가 있다. Spring은 `@Transactional`이 붙은 빈을 발견하면 그 빈을 감싼 동적 프록시를 만들어 빈으로 등록한다. 호출자가 받는 건 원본 객체가 아니라 프록시다.

```java
@Service
public class OrderService {

    public void process() {
        this.createOrder();   // self-invocation: 프록시를 거치지 않는다
    }

    @Transactional
    public void createOrder() { ... }
}
```

여기서 외부 호출자가 `orderService.process()`를 부르면 프록시를 통과한다. 그런데 `process()` 내부의 `this.createOrder()`는 프록시가 아니라 원본 객체의 `this`를 가리킨다. 어노테이션이 분명히 붙어 있는데 트랜잭션이 안 걸린다는 신고가 들어오면 거의 100% 이 자기 호출 문제다.

해결책은 자기 자신을 빈으로 다시 주입받아서 부르거나, AspectJ로 컴파일 타임 위빙(weaving)을 쓰는 것이다. AspectJ를 쓰면 프록시가 아니라 바이트코드 자체에 부가 로직이 박히기 때문에 self-invocation도 정상 동작한다. 단 빌드 설정이 복잡해져서 대부분은 그냥 코드 패턴으로 우회한다.

---

## AOP 어노테이션 실전 패턴

실무에서 가장 많이 쓰는 패턴이 메서드 실행 시간 로깅이다. 메서드마다 `long start = System.currentTimeMillis()`를 박는 짓을 어노테이션 하나로 끝낸다.

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface LogExecutionTime {
    String description() default "";
}
```

```java
@Aspect
@Component
public class LogExecutionTimeAspect {

    private static final Logger log = LoggerFactory.getLogger(LogExecutionTimeAspect.class);

    @Around("@annotation(logExecutionTime)")
    public Object logTime(ProceedingJoinPoint joinPoint,
                          LogExecutionTime logExecutionTime) throws Throwable {
        long start = System.currentTimeMillis();
        try {
            return joinPoint.proceed();
        } finally {
            long elapsed = System.currentTimeMillis() - start;
            String desc = logExecutionTime.description().isEmpty()
                    ? joinPoint.getSignature().toShortString()
                    : logExecutionTime.description();
            log.info("{} 실행 시간: {}ms", desc, elapsed);
        }
    }
}
```

```java
@Service
public class OrderService {

    @LogExecutionTime(description = "주문 생성")
    public Order createOrder(OrderRequest request) {
        // 주문 처리
    }
}
```

`@Around("@annotation(logExecutionTime)")`에서 소문자로 시작하는 `logExecutionTime`은 어드바이스 메서드의 파라미터 이름과 정확히 일치해야 한다. 대문자로 시작하는 타입 이름과 헷갈려서 자주 틀린다. 이름이 안 맞으면 빈 등록 시점에 `IllegalArgumentException: error at ::0 formal unbound in pointcut`이 터진다.

### 컨트롤러 파라미터 바인딩

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.PARAMETER)
public @interface CurrentUser {
}
```

```java
@Component
public class CurrentUserArgumentResolver implements HandlerMethodArgumentResolver {

    @Override
    public boolean supportsParameter(MethodParameter parameter) {
        return parameter.hasParameterAnnotation(CurrentUser.class)
                && parameter.getParameterType().equals(User.class);
    }

    @Override
    public Object resolveArgument(MethodParameter parameter,
                                  ModelAndViewContainer mavContainer,
                                  NativeWebRequest webRequest,
                                  WebDataBinderFactory binderFactory) {
        HttpServletRequest request = webRequest.getNativeRequest(HttpServletRequest.class);
        String token = request.getHeader("Authorization");
        return userService.findByToken(token);
    }
}
```

```java
@Configuration
public class WebConfig implements WebMvcConfigurer {

    private final CurrentUserArgumentResolver resolver;

    public WebConfig(CurrentUserArgumentResolver resolver) {
        this.resolver = resolver;
    }

    @Override
    public void addArgumentResolvers(List<HandlerMethodArgumentResolver> resolvers) {
        resolvers.add(this.resolver);
    }
}
```

```java
@GetMapping("/me")
public ResponseEntity<UserResponse> getMyInfo(@CurrentUser User user) {
    return ResponseEntity.ok(UserResponse.from(user));
}
```

`WebMvcConfigurer`에 resolver 등록을 빠뜨리는 실수가 잦다. 컨트롤러 메서드에 `@CurrentUser` 파라미터가 들어가 있는데 항상 `null`이 들어오거나, "Failed to resolve argument" 예외가 뜬다면 거의 이 등록이 빠진 경우다.

---

## 자주 겪는 실수

**RetentionPolicy를 빠뜨리면 기본값이 CLASS다.** 리플렉션으로 읽으려고 만든 어노테이션인데 `@Retention(RUNTIME)`을 안 붙이면 런타임에 `getAnnotation()`이 항상 `null`을 반환한다. 어노테이션이 분명히 붙어 있는데 안 읽힌다는 증상이라 한참을 헤맨다. 커스텀 어노테이션을 만들 때는 거의 자동으로 `@Retention(RUNTIME)`을 같이 박는 습관을 들이는 게 낫다.

**Lombok 어노테이션을 런타임에 읽으려 한다.** `@Getter`, `@Setter`, `@Builder` 모두 SOURCE 정책이라 런타임에는 존재하지 않는다. "이 필드에 `@Getter`가 붙었는지 확인해서…" 같은 발상은 출발부터 틀렸다. 컴파일된 결과(getter 메서드 자체)를 보고 판단해야 한다.

**AOP 어노테이션이 자기 호출에서 안 먹힌다.** `@Transactional`이든 직접 만든 AOP 어노테이션이든 같은 클래스 내부에서 `this.method()`로 부르면 프록시를 거치지 않으니 어노테이션 처리가 모두 무시된다. 단위 테스트에서는 멀쩡히 동작하다가 실제 호출 경로가 꼬였을 때만 문제가 드러나기 때문에 진단이 까다롭다.

**메타 어노테이션을 활용한 커스텀 어노테이션이 표준 리플렉션으로 안 잡힌다.** `@MyService`라는 커스텀 어노테이션 안에 `@Component`를 메타 어노테이션으로 박아 두면, Spring 컨테이너는 잘 인식한다. 하지만 직접 짠 코드에서 `clazz.getAnnotation(Component.class)`로 읽으려 하면 `null`이 나온다. 표준 리플렉션은 메타 어노테이션을 따라 올라가지 않는다. 같은 동작이 필요하면 `AnnotatedElementUtils.findMergedAnnotation()`을 쓰거나 직접 재귀 탐색을 구현해야 한다.

**어노테이션 프로세서에서 라운드 개념을 무시하고 무조건 파일을 만든다.** `Attempt to recreate a file for type X` 에러의 정체가 이것이다. 같은 라운드에서 같은 이름의 파일을 두 번 만들거나, 프로세서가 라운드마다 반복 실행되면서 같은 파일을 계속 만들려 할 때 터진다. `processingOver()` 체크나 상태 플래그로 방어해야 한다.
