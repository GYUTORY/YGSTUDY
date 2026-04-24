---
title: Java String 불변 객체 (Immutable String)
tags: [language, java, java-기본-개념, string, immutable, string-pool, stringbuilder]
updated: 2026-04-24
---

# Java String 불변 객체

Java를 처음 배울 때 `String`이 불변(Immutable)이라는 말을 듣지만, 그게 정확히 어떤 의미고 왜 그렇게 만들었는지는 잘 설명되지 않는 경우가 많다. 실무에서 흔히 만나는 문제는 거의 다 이 불변성과 관련이 있다. 문자열 비교를 `==`로 하다가 멀쩡히 돌던 코드가 운영 환경에서 갑자기 `false`를 뱉는다거나, 반복문 안에서 `+=`로 문자열을 이어붙이다가 GC 로그가 폭발하는 식이다.

이 문서는 입문 수준의 정리에 가깝다. 불변 객체가 무엇이고 `String`이 어떤 구조로 그 성질을 보장하는지, String Pool이 왜 존재하는지, 리터럴과 `new String()`의 차이가 어떤 결과를 만드는지, 변경이 잦을 때 `StringBuilder`나 `StringBuffer`를 어떤 기준으로 골라야 하는지까지를 다룬다. 더 깊은 주제 — `intern()`의 함정, Compact String 내부 구조, 문자열 연결의 invokedynamic 변환, StringTable 내부 자료구조, 실무 트러블슈팅 — 은 같은 디렉토리의 [String 불변 객체 심화](String_Immutable_Deep_Dive.md) 문서에서 별도로 다룬다.

---

## 1. 불변 객체가 뭔가

불변 객체는 한 번 만들어지면 그 상태를 다시는 바꿀 수 없는 객체를 말한다. `String`이 대표적인 예다. 다음 코드를 보자.

```java
String s = "hello";
s.toUpperCase();
System.out.println(s); // "hello" - 바뀌지 않는다
```

`toUpperCase()`를 호출했지만 `s`는 그대로 "hello"다. 메서드가 작동하지 않은 게 아니라, 새로운 `String` 객체를 만들어서 반환한 것이고 원본은 손대지 않았다. 결과를 쓰려면 다시 받아야 한다.

```java
String s = "hello";
String upper = s.toUpperCase();
System.out.println(s);     // "hello"
System.out.println(upper); // "HELLO"
```

이 패턴이 `String`의 모든 메서드에 적용된다. `replace`, `substring`, `trim`, `concat` 전부 새 객체를 돌려준다. 처음 자바를 만지면 `s.trim()`만 호출해 놓고 왜 공백이 그대로 있냐고 헤매는 경우가 많다.

불변 객체에는 몇 가지 실용적인 이점이 있다. 멀티스레드 환경에서 동기화 없이 공유할 수 있다. 상태가 안 바뀌니까 여러 스레드가 동시에 읽어도 데이터 일관성이 깨질 일이 없다. `HashMap`의 키로 안전하게 쓸 수 있다는 점도 같은 맥락이다. 키의 `hashCode`가 도중에 바뀌면 맵 안에서 영영 못 찾는 객체가 되는데, 불변이면 이런 사고가 안 난다.

대신 비용이 있다. 값이 조금이라도 달라질 때마다 새 객체를 만들어야 하니 메모리와 GC 부담이 커진다. 이걸 줄이기 위한 장치가 String Pool이고, 변경이 잦은 경우를 위한 우회로가 `StringBuilder`다. 둘 다 뒤에서 다룬다.

---

## 2. String 클래스가 불변성을 어떻게 보장하나

JDK 9 이후의 `String` 클래스 선언은 대략 이렇게 생겼다.

```java
public final class String
    implements java.io.Serializable, Comparable<String>, CharSequence {

    @Stable
    private final byte[] value;
    private final byte coder;
    private int hash;
    // ...
}
```

두 가지 장치가 같이 작동한다.

첫째, 클래스 자체가 `final`이다. 누구도 `String`을 상속해서 내부 동작을 바꾸는 서브클래스를 만들 수 없다. 만약 상속이 가능했다면 어디선가 `MutableString extends String` 같은 걸 만들어서 `setValue` 메서드를 추가할 수도 있고, 그 객체가 표준 라이브러리에 키로 들어가면 시스템 전체가 신뢰할 수 없는 상태가 된다. 보안 관점에서 매우 중요한 결정이다.

둘째, 실제 문자열 데이터를 담는 `value` 필드가 `private final byte[]`다. `final`이라 한번 할당된 배열 참조를 다른 배열로 교체할 수 없고, `private`이라 외부에서 직접 건드릴 수도 없다. 메서드도 모두 새 배열을 만들어서 새 `String`을 돌려주는 방식으로만 구현되어 있다.

JDK 9 이전에는 `char[]`였는데 9부터 `byte[]`로 바뀐 이유는 메모리 절감이다 (Compact String). 대부분의 문자열이 ASCII 범위에 들어가는데 `char`는 항상 2바이트라 낭비가 컸기 때문이다. 이 변경의 디테일은 심화 문서에서 다룬다.

엄밀히 말하면 자바의 불변성은 언어 수준 약속이지 물리적 강제가 아니다. 리플렉션으로 `value` 필드의 접근 제한을 풀면 내부 바이트를 바꿀 수도 있다. 하지만 그건 일부러 깨려고 했을 때의 얘기고, 정상적인 코드 경로에서는 절대 변하지 않는다.

---

## 3. String Pool이란

자바 프로그램에는 `"hello"` 같은 문자열 리터럴이 어마어마하게 많이 등장한다. 같은 문자열이 코드 곳곳에 반복되는데 매번 새 객체를 만들면 메모리 낭비가 심하다. JVM은 이걸 줄이려고 String Pool(문자열 상수 풀)이라는 별도 영역을 둔다. 같은 내용의 리터럴은 한 번만 만들어 두고 재사용한다.

```java
String a = "hello";
String b = "hello";
System.out.println(a == b); // true - 같은 객체를 가리킨다
```

`a`와 `b`가 같은 객체를 참조한다. 둘 다 컴파일 타임에 String Pool에 등록된 "hello"를 가리키도록 처리되기 때문이다. JDK 7 이후 String Pool은 Heap 영역 안에 있다 (그 전에는 Permanent Generation에 있었다).

반면 `new String("hello")`는 다르다.

```java
String a = "hello";              // String Pool의 "hello"
String b = new String("hello");  // Heap에 새 객체
System.out.println(a == b);      // false
System.out.println(a.equals(b)); // true
```

`new` 키워드는 Heap에 무조건 새 객체를 만든다. 내용은 같아도 객체로서는 다른 존재다. `==`는 참조 비교라 `false`고, `equals`는 내용 비교라 `true`다. 이 차이가 뒤에서 다룰 비교 실수의 핵심 원인이다.

실무에서는 `new String("...")`을 쓸 일이 거의 없다. 의도적으로 새 객체를 만들어야 하는 경우가 드물기 때문이다. 그런데 외부 입력이나 파싱 결과로 만들어진 `String`은 String Pool에 자동으로 등록되지 않는다. 예를 들어 `BufferedReader`에서 읽은 줄, JSON 파서가 돌려준 값, 데이터베이스에서 가져온 컬럼 값은 전부 Heap에 있는 별개의 객체다. 이걸 풀에 넣고 싶으면 `intern()`을 호출해야 하는데, 이건 함정이 많아서 심화 문서에서 따로 다룬다.

---

## 4. 리터럴과 new String의 차이

3절에서 짧게 봤지만, 운영에서 사고가 나는 지점이라 좀 더 짚는다.

```java
public class StringIdentity {
    public static void main(String[] args) {
        String literal1 = "java";
        String literal2 = "java";
        String built1 = "ja" + "va";          // 컴파일 타임 상수 결합
        String built2 = "ja";
        String built3 = built2 + "va";        // 런타임 결합
        String newOne = new String("java");

        System.out.println(literal1 == literal2); // true
        System.out.println(literal1 == built1);   // true  (컴파일러가 풀의 "java"로 합쳐 둠)
        System.out.println(literal1 == built3);   // false (런타임에 새 객체가 만들어짐)
        System.out.println(literal1 == newOne);   // false (Heap의 새 객체)
        System.out.println(literal1.equals(newOne)); // true
    }
}
```

여기서 헷갈리기 쉬운 게 `built1`과 `built3`의 차이다. `"ja" + "va"`처럼 양쪽이 모두 컴파일 타임에 알 수 있는 상수면 컴파일러가 미리 합쳐서 `"java"` 리터럴 하나로 만든다. 결과적으로 String Pool의 같은 객체를 가리킨다. 반면 변수가 하나라도 끼면 런타임에 결합 연산이 실행되어 Heap에 새 객체가 생긴다. 이때는 풀과 무관하다.

이런 차이를 모른 채 `==`로 문자열을 비교하면, 개발 환경에서는 우연히 잘 돌다가 운영에서 깨지는 일이 생긴다. 환경설정에서 읽어온 값은 런타임에 만들어진 객체라 풀에 없을 가능성이 높기 때문이다. 그래서 다음 절의 규칙이 나온다.

---

## 5. == 와 equals 실수 사례

다음 코드는 신입 코드 리뷰에서 거의 한 번씩은 나오는 문제다.

```java
public class CompareMistake {
    public boolean isAdmin(String role) {
        return role == "ADMIN"; // 잘못된 비교
    }

    public static void main(String[] args) {
        CompareMistake c = new CompareMistake();

        System.out.println(c.isAdmin("ADMIN"));                    // true (우연히)
        System.out.println(c.isAdmin(new String("ADMIN")));        // false
        System.out.println(c.isAdmin(readFromConsole()));          // false (입력값은 풀 밖)
    }

    static String readFromConsole() {
        return new java.util.Scanner(System.in).nextLine();
    }
}
```

리터럴끼리 `==` 비교하면 우연히 통과한다. 그래서 단위 테스트도 통과하고 로컬에서도 잘 돌아간다. 그런데 실제 요청 파라미터, DB에서 읽은 값, 파일에서 읽은 줄로 들어오는 순간 무조건 `false`가 된다. 인증 로직에서 이런 코드가 있으면 권한 체크가 항상 실패해서 모든 사용자가 차단되거나, 반대로 어떤 우회 경로로 통과해서 권한이 잘못 주어진다.

규칙은 단순하다. **문자열 비교는 무조건 `equals` 또는 `equalsIgnoreCase`를 써야 한다.** `==`는 두 변수가 같은 객체를 가리키는지를 묻는 연산이지, 내용이 같은지를 묻는 게 아니다.

null 안전성까지 챙기려면 상수를 왼쪽에 두는 패턴도 흔히 쓴다.

```java
if ("ADMIN".equals(role)) { ... }  // role이 null이어도 NPE 안 남
```

자바 7부터 `switch` 문에서 `String`을 쓸 수 있게 되었는데, 이것도 내부적으로 `hashCode`와 `equals`로 구현되어 있다. `==`가 아니다.

---

## 6. StringBuilder와 StringBuffer 선택 기준

`String`이 불변이라는 건, 변경 작업을 많이 하면 그만큼 객체가 많이 만들어진다는 뜻이다. 다음 코드는 작아 보여도 큰 문제다.

```java
String result = "";
for (int i = 0; i < 100_000; i++) {
    result += i;  // 매번 새 String 생성
}
```

10만 번 반복이면 `String` 객체가 10만 개 만들어지고, 매번 이전 값을 복사해서 새 배열에 채운다. GC 부담은 물론이고 시간 복잡도가 사실상 O(n²)다. 운영 서버에서 이런 패턴이 핫 패스에 있으면 바로 응답 시간이 망가진다.

대안으로 가변 문자열 클래스가 두 개 있다.

```java
StringBuilder sb = new StringBuilder();
for (int i = 0; i < 100_000; i++) {
    sb.append(i);
}
String result = sb.toString();
```

`StringBuilder`는 내부에 `byte[]` 버퍼를 두고 그 안에 문자를 추가한다. 버퍼가 부족하면 두 배 크기로 확장한다. 객체 생성은 처음 한 번 (그리고 확장 시점들) 뿐이라 비용이 훨씬 작다.

`StringBuilder`와 `StringBuffer`의 차이는 동기화 여부 하나다.

| 클래스 | 동기화 | 사용 환경 |
|--------|--------|----------|
| `StringBuilder` | 없음 | 단일 스레드 또는 스레드 간 공유 안 하는 지역 변수 |
| `StringBuffer` | 모든 메서드 `synchronized` | 여러 스레드가 같은 인스턴스를 공유하는 경우 |

실무에서는 거의 다 `StringBuilder`를 쓴다. 동시성이 필요한 경우라도 한 객체를 여러 스레드가 동시에 채워 넣는 패턴 자체가 드물기 때문이다. 보통은 스레드별로 자기 `StringBuilder`를 만들어 쓰고 결과만 합친다. `StringBuffer`는 자바 1.0 시절 유물에 가깝고, 동기화 비용 때문에 `StringBuilder`보다 항상 느리다.

다만 `+` 연산자도 컴파일러가 알아서 `StringBuilder`로 변환해 주는 경우가 있다. JDK 9 이후로는 `invokedynamic` 기반의 `makeConcatWithConstants`로 더 똑똑하게 처리한다. 단순한 결합은 굳이 직접 `StringBuilder`를 쓸 필요가 없다는 뜻이다.

```java
String greet = "Hello, " + name + "!";  // 컴파일러가 효율적인 형태로 바꿔 준다
```

문제는 반복문 안의 `+=`다. 컴파일러가 매 반복마다 새 `StringBuilder`를 만들기 때문에 위에서 본 O(n²) 함정이 그대로 남는다. **반복문 안에서 문자열을 누적할 때만 직접 `StringBuilder`를 만들면 된다.** 그 외엔 `+`로 충분하다.

자바 8부터는 `String.join`, `Stream`의 `Collectors.joining` 같은 API도 있어서 단순한 합치기는 이쪽이 더 읽기 좋다.

```java
List<String> tags = List.of("java", "string", "immutable");
String joined = String.join(", ", tags);
String streamed = tags.stream().collect(java.util.stream.Collectors.joining(", "));
```

내부적으로는 둘 다 `StringJoiner`나 `StringBuilder`를 쓴다. 직접 짤 필요 없이 표준 API에 맡기는 게 정답이다.

---

## 7. 정리

`String`이 불변이라는 건 단순한 규칙이 아니라 자바 언어 설계와 JVM 동작 방식 전체에 얽혀 있는 결정이다. 이 절의 내용을 한 줄씩 정리하면 다음과 같다.

- `String`은 `final` 클래스고 내부 데이터(`byte[] value`)도 `final`이라 한 번 만들어지면 내용이 바뀌지 않는다.
- 같은 내용의 리터럴은 String Pool에 한 번만 저장되어 재사용된다. `new String("...")`은 이 풀을 우회해 Heap에 별도 객체를 만든다.
- 문자열 비교는 `equals`로 한다. `==`는 객체 동일성을 묻는 연산이라 우연히 통과하다 운영에서 사고를 낸다.
- 변경이 잦은 경우 `StringBuilder`를 쓴다. `StringBuffer`는 멀티스레드가 한 인스턴스를 공유하는 드문 상황에서만 의미가 있고 그 외에는 느릴 뿐이다.
- 단순 결합은 `+` 연산자로도 충분하다. 컴파일러가 알아서 효율적인 형태로 바꿔 준다. 반복문 안의 누적만 직접 `StringBuilder`를 쓰면 된다.

더 깊이 파고들고 싶다면 [String 불변 객체 심화](String_Immutable_Deep_Dive.md) 문서를 보면 된다. `intern()`의 동작과 함정, Compact String의 내부 구조, 문자열 결합이 바이트코드 수준에서 어떻게 변환되는지, StringTable의 자료구조와 크기 튜닝, 그리고 실제 운영에서 만난 트러블슈팅 사례까지 다룬다.
