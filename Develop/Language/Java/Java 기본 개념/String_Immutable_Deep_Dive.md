---
title: String 불변 객체 심화 (String Pool, intern(), StringBuilder/StringBuffer)
tags: [language, java, java-기본-개념, string, string-pool, intern, stringbuilder, stringbuffer, compact-string]
updated: 2026-04-17
---

# String 불변 객체 심화

`String`이 불변이라는 사실은 누구나 알고 있지만, 왜 그렇게 설계됐고 JVM 내부에서 어떻게 관리되는지까지 이해하는 경우는 드물다. 이 문서에서는 String Pool의 실제 자료구조, `intern()`의 동작 방식과 함정, StringBuilder/StringBuffer 내부 구현, 문자열 연결 연산의 바이트코드 수준 차이, 그리고 실무에서 자주 만나는 트러블슈팅 사례를 다룬다.

대부분의 내용은 Oracle JDK 17 소스 기준이고, JDK 9에서 도입된 Compact String도 포함한다. JDK 8 이하의 동작이 다른 부분은 별도로 표시한다.

---

## 1. String이 불변인 구조적 이유

### 1.1 final class

```java
public final class String
    implements java.io.Serializable, Comparable<String>, CharSequence,
               Constable, ConstantDesc {
    ...
}
```

`String`은 `final` 클래스다. 상속을 막아서 서브클래스가 내부 상태를 변경하는 메서드를 추가하는 경로를 원천적으로 차단한다. 만약 상속이 가능했다면 `MutableString extends String` 같은 클래스를 만들어서 String Pool에 들어갈 객체의 내부 값을 바꿀 수 있게 된다. 이는 SecurityManager 우회, 파일 경로 조작 같은 보안 문제로 직결된다.

### 1.2 final byte[] value

JDK 9 이전에는 내부 저장소가 `private final char[] value`였다. JDK 9부터는 Compact String 도입으로 `byte[]`로 바뀌었다.

```java
// JDK 9+ 소스 일부
public final class String {
    @Stable
    private final byte[] value;
    private final byte coder;
    private int hash;
    private boolean hashIsZero;
    ...
}
```

`value` 필드는 `final`이라 한 번 할당된 참조를 다른 배열로 바꿀 수 없다. 단, 배열 자체의 원소는 `final`로도 막을 수 없다는 점은 주의해야 한다. 리플렉션으로 `value` 필드의 접근 제한을 풀면 내부 바이트를 바꿀 수 있다. JDK 내부에서도 이런 트릭은 존재한다 (예: `String.substring`이 JDK 6까지는 같은 배열을 공유했던 이유).

```java
String s = "hello";
Field valueField = String.class.getDeclaredField("value");
valueField.setAccessible(true);
byte[] value = (byte[]) valueField.get(s);
value[0] = 'H';
System.out.println(s); // "Hello" - 내부 상태가 바뀐다
```

이런 코드는 보안 관리자가 없는 환경에서 실제로 작동한다. 불변성은 언어 수준의 약속일 뿐, 물리적으로 강제되지 않는다. 그래서 `String`을 키로 쓰는 `HashMap`에 이런 트릭이 섞이면 `hashCode`가 캐시된 값과 달라져서 조회가 실패하는 기묘한 버그가 생긴다.

### 1.3 Compact String (JDK 9+)

JDK 9에서 `char[]`가 `byte[]`로 바뀐 이유는 메모리 절감이다. 대부분의 문자열이 ISO-8859-1(Latin-1) 범위에 들어가는데, `char`는 항상 2바이트를 사용해서 낭비가 컸다.

`coder` 필드가 인코딩 플래그다.

```java
static final byte LATIN1 = 0;  // 1바이트/문자
static final byte UTF16  = 1;  // 2바이트/문자
```

문자열을 만들 때 모든 문자가 Latin-1 범위(0x00 ~ 0xFF)에 들어가면 `coder = LATIN1`로 설정되고 `byte[]`에 1바이트씩 저장된다. 한 글자라도 범위를 벗어나면 `coder = UTF16`이 되고 `byte[]`에 2바이트씩 little-endian으로 저장된다.

```java
String ascii  = "Hello World";     // coder=0, value.length=11
String korean = "안녕하세요";        // coder=1, value.length=10 (5글자 * 2바이트)
String mixed  = "Hello 안녕";       // coder=1 - 한 글자만 벗어나도 전체가 UTF16
```

이 때문에 한글 문자열 끝에 ASCII를 아무리 붙여도 Latin-1로 내려가지 않는다. 애플리케이션 로그에 이모지가 하나라도 섞이면 `coder`가 UTF16이 되어서 메모리 사용량이 두 배가 된다. 대용량 로그를 메모리에 적재하는 배치 작업에서 이런 차이가 GC 압박으로 드러난다.

`-XX:-CompactStrings` JVM 옵션으로 Compact String을 끄면 JDK 8처럼 항상 UTF16으로 저장된다. 하위 호환성 문제로 끄는 경우가 드물게 있다.

### 1.4 불변성이 주는 실용적 이득

- **해시 캐싱**: `hashCode()`가 `hash` 필드에 결과를 저장한다. 값이 바뀌지 않으니 한 번 계산하면 재사용할 수 있다. `HashMap`의 키로 `String`이 자주 쓰이는 이유 중 하나다.
- **String Pool 공유 안전**: 여러 코드가 같은 리터럴을 참조해도 누구도 내용을 바꿀 수 없으니 공유가 안전하다.
- **스레드 안전**: 동기화 없이 공유할 수 있다.
- **방어적 복사 불필요**: 메서드 파라미터로 받은 `String`을 그대로 보관해도 외부에서 바꿀 수 없다.

---

## 2. String Pool 내부 동작

### 2.1 String Pool의 위치 변경사

String Pool은 JVM 내부에서 문자열 리터럴을 캐시하는 저장소다. 이 저장소의 위치는 JDK 버전마다 달랐다.

- **JDK 6까지**: PermGen(Permanent Generation)에 있었다. PermGen은 크기가 고정되어서 `intern()`을 과도하게 호출하면 `OutOfMemoryError: PermGen space`가 났다.
- **JDK 7부터**: Heap으로 이동했다. 이유는 PermGen의 고정 크기 한계를 벗어나고, GC 대상이 되도록 하기 위해서다. Heap에 있으니 일반 객체처럼 GC가 수거할 수 있다.
- **JDK 8**: PermGen 자체가 Metaspace로 대체됐지만 String Pool은 여전히 Heap에 있다.

이 변경은 실무에 꽤 큰 영향을 줬다. JDK 6 환경에서 대량의 동적 문자열을 `intern()`하던 코드가 JDK 7로 업그레이드하면서 OOM 패턴이 바뀌었다. PermGen 고갈은 사라졌지만, 대신 Heap의 Old 영역을 잠식하는 문제로 넘어왔다.

### 2.2 String Pool의 자료구조

String Pool의 실제 구현은 `StringTable`이라는 JVM 내부 자료구조다. HotSpot 소스에서 `src/hotspot/share/classfile/stringTable.cpp`를 보면 해시 테이블 기반이다.

```
StringTable
├── bucket[0] → entry → entry → ...
├── bucket[1] → entry → entry → ...
└── bucket[N] → entry → entry → ...
```

JDK 7까지는 기본 버킷 수가 `1,009`개로 매우 적었다. 리터럴이 많은 애플리케이션에서는 한 버킷에 수백 개의 엔트리가 매달려서 `intern()` 호출이 O(n)에 가까워지는 성능 문제가 있었다.

JDK 7u40부터 `-XX:StringTableSize` 옵션이 추가되고 기본값이 `60,013`으로 늘어났다. 현재 JDK 17은 기본값이 `65,536`이다. 대규모 문자열을 다루는 애플리케이션이라면 이 값을 소수로 지정하는 게 관례였지만, 최근 JDK는 해시 충돌 저항성이 좋아져서 건드릴 일이 거의 없다.

```
-XX:StringTableSize=1000003
-XX:+PrintStringTableStatistics  // 통계 출력
```

`jcmd <pid> VM.stringtable` 명령으로 현재 StringTable 상태를 조회할 수 있다. 이 출력에서 버킷당 평균 엔트리 수가 10을 넘으면 테이블 크기를 늘리는 것을 고려한다.

### 2.3 리터럴 등록 시점

문자열 리터럴은 클래스 로딩 시점이 아니라 해당 리터럴이 있는 바이트코드 명령(`ldc`)이 처음 실행되는 순간 Pool에 들어간다. 정확히는 클래스가 resolve될 때 상수 풀의 `CONSTANT_String_info`가 `StringTable::intern`을 호출해서 등록한다.

```java
public class StringPoolTimingExample {
    public static void main(String[] args) {
        // 이 시점에는 "late-binding"이 Pool에 없다
        
        someMethod(); // 이 안의 ldc가 실행되면 Pool에 등록된다
    }
    
    static void someMethod() {
        String s = "late-binding";
    }
}
```

### 2.4 `new String("...")`과 Pool

```java
String a = "hello";
String b = "hello";
String c = new String("hello");

System.out.println(a == b); // true
System.out.println(a == c); // false
System.out.println(a == c.intern()); // true
```

`new String("hello")`는 두 개의 객체를 만든다. 리터럴 `"hello"`가 Pool에 등록되고(이미 있으면 재사용), 그 값을 복사한 새 `String` 객체가 Heap에 별도로 생성된다. `c`는 Heap의 별도 객체를 가리키므로 `a == c`는 false다.

면접 단골 질문이지만 실무에서 `new String(String)`을 쓸 일은 거의 없다. 유일한 예외는 JDK 6 이하에서 `substring`의 배열 공유 문제를 피하기 위해서였고, JDK 7u6 이후로는 그 필요도 사라졌다.

---

## 3. intern() 동작 원리와 함정

### 3.1 동작 방식

`String.intern()`의 명세는 단순하다. Pool에 같은 내용의 문자열이 있으면 그것의 참조를 반환하고, 없으면 현재 문자열을 Pool에 넣고 반환한다.

```java
public native String intern();
```

네이티브 메서드로 `StringTable::intern`을 호출한다. 내부적으로는 해시 계산 → 버킷 탐색 → equals 비교 → 없으면 삽입 흐름이다.

```java
String a = new String("heavy-key-" + userId);
String b = a.intern();
// b는 Pool의 정규화된 참조
```

### 3.2 왜 intern을 쓰는가

같은 문자열이 수만 개의 인스턴스로 존재하는 상황에서 메모리를 절감하려는 용도다. 대표적인 예가 파싱된 XML의 엘리먼트 이름, 데이터베이스에서 읽은 카테고리 코드 같은 고-카디널리티가 아닌 반복 문자열이다.

```java
// 100만 행을 읽는데 카테고리는 20종류뿐
while (rs.next()) {
    String category = rs.getString("category").intern();
    rows.add(new Row(category, ...));
}
```

이렇게 하면 `category` 필드가 참조하는 String 객체가 20개로 수렴한다. 단순히 `getString` 결과를 쓰면 매 행마다 새 String 객체가 만들어진다.

### 3.3 함정 1: 무한정 intern하면 메모리 누수

Pool은 기본적으로 GC 대상이지만, Pool에 들어간 String에 대한 참조가 Pool 자체에 남아있는 한 GC되지 않는다. 즉 `intern()`으로 등록한 문자열은 **동일 문자열이 다시는 등록되지 않을 때까지** Pool에 남는다.

```java
// 안티 패턴
for (long i = 0; i < Long.MAX_VALUE; i++) {
    String unique = ("session-" + UUID.randomUUID()).intern();
    // 매번 유일한 문자열이라 Pool이 계속 커진다
}
```

이 코드는 실제로 Old 영역 고갈로 OOM을 낸다. `intern()`은 **카디널리티가 작고 유한한 문자열**에만 써야 한다. 사용자 ID, UUID, 세션 토큰 같은 것에 쓰면 Pool이 리크한다.

### 3.4 함정 2: Pool의 GC는 Full GC 시점에 일어난다

String Pool의 엔트리 정리는 Young GC가 아니라 Full GC(또는 그와 유사한 stop-the-world 작업) 때 일어난다. 짧은 주기의 문자열을 intern하면 Young GC로는 수거되지 않고 Old에 남아서 결국 Full GC를 유발한다.

`-XX:+PrintStringTableStatistics`를 붙여서 애플리케이션 종료 시 StringTable의 크기와 버킷당 평균 엔트리 수를 확인할 수 있다.

### 3.5 함정 3: 해시 충돌로 인한 성능 저하

`StringTable`의 해시 함수는 `String.hashCode()`와 다른 자체 해시를 사용하지만, 결국 문자열 내용 기반이다. 의도적으로 해시가 같은 문자열을 대량 intern하면 한 버킷에 몰려서 조회 성능이 떨어진다. 일반적인 애플리케이션에서는 거의 발생하지 않지만, 사용자 입력을 그대로 `intern()`하는 코드는 악의적 입력에 취약해질 수 있다.

### 3.6 intern을 써야 할지 판단하는 기준

보통은 `intern()` 대신 애플리케이션 레벨의 `ConcurrentHashMap<String, String>` 캐시를 쓰는 게 낫다. Pool의 전역성과 GC 간섭을 피할 수 있고, 캐시 크기를 제어할 수 있다.

```java
private static final ConcurrentHashMap<String, String> cache = new ConcurrentHashMap<>();

public static String canonicalize(String s) {
    String existing = cache.get(s);
    if (existing != null) return existing;
    cache.putIfAbsent(s, s);
    return cache.get(s);
}
```

크기 제한이 필요하면 Caffeine이나 Guava Cache의 weak-value 캐시를 쓴다. 이렇게 하면 참조가 없어진 문자열을 자동으로 수거한다.

---

## 4. StringBuilder vs StringBuffer

### 4.1 공통 조상: AbstractStringBuilder

둘 다 `AbstractStringBuilder`를 상속한다. 실제 버퍼 관리, `append`, `insert`, `delete` 로직은 이 추상 클래스에 구현되어 있다.

```
AbstractStringBuilder
├── StringBuilder   (final, 비동기, JDK 5)
└── StringBuffer    (final, synchronized, JDK 1.0)
```

`AbstractStringBuilder`의 내부 필드:

```java
abstract class AbstractStringBuilder implements Appendable, CharSequence {
    byte[] value;   // 현재 버퍼 (JDK 9+ byte[], 이전엔 char[])
    byte coder;     // Compact String 인코딩 플래그
    int count;      // 실제 사용 길이
    ...
}
```

`value`가 `final`이 아니다. 즉, 용량이 부족해지면 더 큰 배열로 교체할 수 있다. 이것이 가변성의 핵심이다.

### 4.2 용량 확장 로직

```java
private int newCapacity(int minCapacity) {
    int oldCapacity = value.length >> coder;
    int newCapacity = (oldCapacity << 1) + 2;
    if (newCapacity - minCapacity < 0) {
        newCapacity = minCapacity;
    }
    return (newCapacity <= 0 || SAFE_BOUND - newCapacity < 0)
        ? hugeCapacity(minCapacity)
        : newCapacity;
}
```

용량이 부족하면 `(현재 용량 * 2) + 2`로 늘린다. 초기 용량은 기본 생성자 기준 16이다. 긴 문자열을 만들 예정이면 생성자에 초기 용량을 지정하는 편이 배열 재할당 횟수를 줄인다.

```java
// 예상 길이가 1만자라면
StringBuilder sb = new StringBuilder(10_000);
```

### 4.3 synchronized 차이

`StringBuffer`의 핵심 메서드는 `synchronized`가 붙어 있다.

```java
public final class StringBuffer extends AbstractStringBuilder ... {
    @Override
    public synchronized StringBuffer append(String str) {
        toStringCache = null;
        super.append(str);
        return this;
    }

    @Override
    public synchronized String toString() {
        if (toStringCache == null) {
            return toStringCache = isLatin1() 
                ? StringLatin1.newString(value, 0, count)
                : StringUTF16.newString(value, 0, count);
        }
        return new String(toStringCache);
    }
    ...
}
```

반면 `StringBuilder`는 동기화 없이 같은 `super.append`를 호출한다.

```java
public final class StringBuilder extends AbstractStringBuilder ... {
    @Override
    public StringBuilder append(String str) {
        super.append(str);
        return this;
    }
    ...
}
```

`toStringCache`도 `StringBuffer`에만 있는 최적화다. `append` 호출로 상태가 변하면 캐시를 무효화하고, `toString`이 여러 번 호출돼도 `String` 객체를 한 번만 만든다.

### 4.4 어느 쪽을 쓸 것인가

**대부분의 경우 `StringBuilder`를 쓴다.** 단일 스레드에서 문자열을 조립하는 것이 일반적인 패턴이다. 동기화 오버헤드가 없다.

`StringBuffer`는 JDK 1.0부터 있던 레거시이고, 여러 스레드가 같은 버퍼에 동시에 쓰는 시나리오 자체가 드물다. 그런 시나리오가 있다면 보통 설계가 잘못된 경우다. 멀티스레드 로깅 같은 것도 각 스레드가 자기 `StringBuilder`로 조립한 뒤 최종 결과만 공유하는 게 맞다.

현대 JVM의 biased locking과 락 축소(lock coarsening) 최적화로 `StringBuffer`의 성능 페널티가 과거만큼 크지는 않지만, 이득도 없다.

---

## 5. 문자열 연결 방식의 바이트코드 비교

### 5.1 `+` 연산자의 컴파일러 변환

Java 소스 레벨에서 `+`로 문자열을 연결하면, 컴파일러가 내부적으로 다른 코드로 변환한다. JDK 8까지는 `StringBuilder`로 변환됐고, JDK 9부터는 `invokedynamic` + `StringConcatFactory`로 바뀌었다.

```java
String result = "Hello " + name + ", age: " + age;
```

**JDK 8의 바이트코드 (javap -c)**
```
new           java/lang/StringBuilder
invokespecial StringBuilder."<init>":()V
ldc           "Hello "
invokevirtual StringBuilder.append:(Ljava/lang/String;)Ljava/lang/StringBuilder;
aload_1       // name
invokevirtual StringBuilder.append:...
ldc           ", age: "
invokevirtual StringBuilder.append:...
iload_2       // age
invokevirtual StringBuilder.append:(I)Ljava/lang/StringBuilder;
invokevirtual StringBuilder.toString:()Ljava/lang/String;
```

**JDK 9+의 바이트코드**
```
aload_1       // name
iload_2       // age
invokedynamic makeConcatWithConstants, "Hello \u0001, age: \u0001"
```

JDK 9+는 `invokedynamic`으로 런타임에 최적 구현을 결정한다. `StringConcatFactory`가 부트스트랩 메서드로 `MethodHandle`을 생성하는데, 내부적으로 최소한의 버퍼 크기 계산 후 단일 배열 복사로 처리한다. 여러 벤치마크에서 `StringBuilder` 방식보다 10~30% 빠르다.

### 5.2 반복문 안의 `+`는 여전히 덫이다

```java
String result = "";
for (int i = 0; i < 10000; i++) {
    result = result + i; // 매 반복마다 새 StringBuilder/concat 호출
}
```

`+` 연산자 최적화는 **단일 표현식 내부**에만 적용된다. 반복문 안의 `+=`는 매 반복마다 새 임시 버퍼를 만들고 기존 문자열을 복사한다. 시간 복잡도가 O(n²)이 된다.

```
iter 0: ""          + "0" → "0"         (복사 1)
iter 1: "0"         + "1" → "01"        (복사 2)
iter 2: "01"        + "2" → "012"       (복사 3)
...
iter n: 길이 n인 문자열 복사
총 복사 비용: 1 + 2 + ... + n = O(n²)
```

반복 횟수가 1만을 넘으면 체감 가능한 수준으로 느려진다. 10만을 넘으면 초 단위 지연이 생긴다.

```java
// 올바른 방식
StringBuilder sb = new StringBuilder();
for (int i = 0; i < 10000; i++) {
    sb.append(i);
}
String result = sb.toString();
```

예상 최종 길이를 알 수 있다면 초기 용량 지정이 추가 이득을 준다.

### 5.3 `concat()` 메서드

```java
public String concat(String str) {
    if (str.isEmpty()) {
        return this;
    }
    ...
    byte[] buf = StringConcatHelper.newArray(Math.addExact(len, otherLen));
    ...
    return new String(buf, coder);
}
```

`String.concat(String)`은 두 문자열을 이어서 새 `String`을 만든다. 단일 연결이라면 `+`보다 빠르다는 오래된 속설이 있었지만 현대 JVM에서는 차이가 거의 없다. 특히 JDK 9+ 의 `invokedynamic` 기반 `+`가 더 빠른 경우도 많다.

### 5.4 간단한 성능 비교 (참고용)

n회 반복해서 n길이 문자열 만들기 (JMH 기준 대략적인 경향, JDK 17):

```
n = 10000
+ 연산자 (반복문):          600 ms
concat (반복문):            550 ms
StringBuilder:              0.3 ms
StringBuilder(초기용량):     0.2 ms
```

반복 횟수가 작으면 어떤 방식이든 차이를 체감할 수 없다. n이 커질수록 차이가 기하급수적으로 벌어진다.

### 5.5 Stream과 String.join

```java
String csv = list.stream().collect(Collectors.joining(","));
String csv2 = String.join(",", list);
```

둘 다 내부적으로 `StringJoiner`를 쓰고 `StringJoiner`는 `StringBuilder` 기반이다. 가독성과 성능 둘 다 괜찮다. 구분자 있는 조립은 이 방식이 제일 깔끔하다.

---

## 6. 실무 트러블슈팅

### 6.1 대용량 문자열 처리 시 OOM

대용량 파일을 한 번에 `String`으로 읽는 코드는 거의 모든 경우 잘못된 선택이다.

```java
// 3GB 파일 → 힙에 6GB (UTF16) 필요
String content = Files.readString(Paths.get("huge.log"));
```

이때 발생하는 문제:

1. **`String.length()`는 `int`라 최대 2^31-1 (약 21억) 문자**까지만 담을 수 있다. 그 이상이면 아예 생성이 안 된다.
2. **Compact String이 꺼지는 순간 메모리가 두 배**가 된다. 한 글자만 비-Latin-1이어도 전체가 UTF16.
3. **GC 압박**: 거대한 배열은 Old 영역으로 직행하고, Full GC 시 정지 시간이 길어진다.

대안은 `BufferedReader`로 라인 단위 처리거나, `Stream<String>`이다.

```java
try (Stream<String> lines = Files.lines(Paths.get("huge.log"))) {
    lines.filter(l -> l.contains("ERROR"))
         .forEach(System.out::println);
}
```

메모리에 들고 있어야 한다면 `ByteBuffer`로 바이트 수준에서 다루는 것을 검토한다.

### 6.2 `==` vs `equals()`의 함정

```java
String a = "hello";
String b = "hello";
String c = new String("hello");
String d = c.intern();
String e = "hel" + "lo";          // 컴파일 타임 상수 → Pool
String f = "hel" + new String("lo"); // 런타임 연결 → 새 객체

a == b // true (둘 다 Pool)
a == c // false (c는 Heap)
a == d // true (intern 결과)
a == e // true (컴파일 타임 상수 폴딩)
a == f // false (런타임 연결)
```

`==`는 참조 비교다. 애플리케이션 코드에서 문자열 비교는 항상 `equals()`를 써야 한다. 유일한 예외는 성능이 극단적으로 중요한 내부 자료구조에서 의도적으로 `intern()`된 값을 비교하는 경우다 (예: XML 파서의 엘리먼트 이름).

IDE 정적 분석(IntelliJ, SonarQube)이 `String` 비교에 `==`를 쓰면 경고를 띄운다. 경고를 무시하고 넘어간 코드가 1년 뒤 누군가가 리팩토링하면서 `intern()`을 빼먹으면 터진다. 애초에 `equals`를 쓰는 게 안전하다.

### 6.3 switch문과 String 해시 충돌

Java 7부터 `switch`에 `String`을 쓸 수 있다. 컴파일러는 이를 해시 기반 분기로 변환한다.

```java
switch (key) {
    case "alpha": return 1;
    case "beta":  return 2;
    case "gamma": return 3;
}
```

**컴파일러가 생성하는 코드 (개념)**
```java
switch (key.hashCode()) {
    case 92909918:  // "alpha".hashCode()
        if (key.equals("alpha")) return 1;
        break;
    case 3020272:   // "beta".hashCode()
        if (key.equals("beta")) return 2;
        break;
    case 98120615:  // "gamma".hashCode()
        if (key.equals("gamma")) return 3;
        break;
}
```

해시 충돌이 생기면 같은 `case` 아래 여러 `if`가 들어간다. 악의적 입력으로 `hashCode`가 같은 케이스를 몰아넣어서 조회 성능을 떨어뜨리는 공격이 이론적으로 가능하지만, 보통은 실무에서 드문 이슈다.

실제로 더 자주 보는 문제는 `hashCode`가 충돌하는 두 문자열을 같은 `switch`에 넣었을 때 발생한다. 해시가 같아도 `equals`로 구분되니 기능적으로는 문제가 없지만, 이상한 성능 프로파일이 나올 수 있다. 예를 들어 `"FB"`와 `"Ea"`는 `hashCode`가 같다.

### 6.4 Locale 관련 함정

`String.toLowerCase()`는 기본적으로 플랫폼의 기본 Locale을 사용한다. 터키어 Locale에서는 `"TITLE".toLowerCase()`가 `"tıtle"` (점 없는 ı)이 나온다.

```java
// 안전하지 않다
if (path.toLowerCase().endsWith(".jpg")) { ... }

// 항상 이렇게 쓴다
if (path.toLowerCase(Locale.ROOT).endsWith(".jpg")) { ... }
```

`equalsIgnoreCase`는 내부적으로 Locale을 타지 않는 간이 비교라 대부분의 경우 안전하지만, 특수한 유니코드 케이스에서는 여전히 문제가 될 수 있다. 비교 기준이 중요한 도메인에서는 `java.text.Collator`를 검토한다.

### 6.5 substring과 메모리

JDK 6까지 `substring`은 원본 배열을 공유했다. 1GB 문자열에서 10자만 `substring`하면 10자짜리 `String`이 1GB 배열 참조를 붙잡고 있어서 GC가 원본을 못 지우는 리크가 있었다. 이를 피하려고 `new String(huge.substring(0, 10))`처럼 명시적으로 복사하는 관례가 있었다.

JDK 7u6부터 `substring`이 항상 새 배열을 할당하도록 바뀌었고, 이 관례는 불필요해졌다. 오래된 블로그 글이나 책을 보고 `new String(...)` 래핑을 하는 코드를 만나면 JDK 버전을 확인해보고 제거한다.

### 6.6 Collection에서 String을 키로 쓸 때

`HashMap<String, ...>`에서 조회 성능이 이상하게 나오는 경우, 키로 쓰는 문자열이 매번 새로 만들어지고 있는지 본다. `equals`는 O(n)이라 키가 길면 조회 자체가 비싸진다.

```java
Map<String, User> cache = ...;

// 매 호출마다 키 문자열을 새로 만든다
User u = cache.get("user:" + id + ":" + region);
```

호출 빈도가 높다면 키를 미리 `intern()`하거나, 복합 키 객체로 바꾸거나, primitive long 기반 조회로 바꾸는 게 답이다.

### 6.7 JSON 파싱 후 문자열 중복

Jackson, Gson 같은 JSON 파서로 대량 파싱하면 같은 키 이름(`"id"`, `"name"` 등)이 객체마다 새 `String`으로 만들어져서 메모리를 차지한다.

Jackson은 `JsonFactory.Feature.INTERN_FIELD_NAMES` 옵션이 기본적으로 켜져 있어서 필드 이름을 `intern()`한다. 값은 intern하지 않으므로 값 중복이 문제라면 커스텀 `Deserializer`에서 처리해야 한다.

---

## 7. 정리

`String`의 불변성은 `final` 클래스와 `final` 필드로 보장되지만, 리플렉션으로 뚫릴 수 있다는 점을 기억해야 한다. JDK 9의 Compact String은 메모리 절감에 큰 영향을 주지만 한 글자만 비-Latin-1이어도 무력화된다는 주의점이 있다.

String Pool은 JDK 7에서 Heap으로 옮겨진 이후 GC 대상이 됐지만 여전히 Full GC 시점에만 정리된다. `intern()`은 카디널리티가 유한한 문자열에만 써야 하고, 그 외의 경우엔 애플리케이션 레벨 캐시를 쓰는 편이 안전하다.

`StringBuilder`와 `StringBuffer`는 `AbstractStringBuilder`를 공유하며 동기화 여부만 다르다. 멀티스레드 공유 버퍼가 필요한 시나리오 자체가 드물기 때문에 실무에서는 `StringBuilder`를 쓴다.

`+` 연산자는 JDK 9부터 `invokedynamic` 기반으로 바뀌어서 단일 표현식 연결은 빠르지만, 반복문 안에서는 여전히 O(n²)이다. 반복 연결은 `StringBuilder`가 정답이다.

실무에서 만나는 문자열 관련 문제는 대부분 이 문서에서 다룬 함정들의 조합이다. Compact String에 대한 이해가 없으면 메모리 프로파일링을 해도 왜 두 배가 됐는지 모르고, `intern()` 남용의 패턴을 모르면 Old 영역 누수의 원인을 못 찾는다. JDK 버전별 차이를 인지하고 현재 환경에서 실제로 어떤 바이트코드가 생성되는지 확인하는 습관이 중요하다.
