---
title: String Immutable Object
tags: [language, java, java-기본-개념, string-불변-객체]
updated: 2025-08-10
---
# String 불변 객체(Immutable Object) 🚀

## 1. 불변 객체(Immutable Object)란? 🤔

**불변 객체(Immutable Object)**란 **한 번 생성되면 상태가 변경되지 않는 객체**를 의미합니다.  
Java에서 `String` 클래스는 **대표적인 불변 객체**로, **한 번 생성되면 그 값을 변경할 수 없습니다.**

> **✨ 불변 객체의 특징**
> - **객체 생성 이후 상태 변경 불가능**
> - **동기화(Synchronization)가 필요 없음 (Thread-Safe)**
> - **캐싱(Caching)이 가능하여 성능 최적화**
> - **예상치 못한 변경으로 인한 버그 방지**

✅ **즉, `String` 객체는 변경이 불가능하며, 문자열을 변경하려면 새로운 `String` 객체가 생성됩니다.**

---

## 2. `String` 객체가 불변(Immutable)한 이유 🔒

Java의 `String` 클래스는 내부적으로 **`final char[]` 배열을 사용하여 문자열을 저장**합니다.  
`final` 키워드가 사용된 배열은 한 번 할당되면 참조를 변경할 수 없으므로, `String` 객체는 불변성을 가지게 됩니다.

📌 **Java의 `String` 클래스 코드 일부 (JDK 11 기준)**
```java
public final class String implements java.io.Serializable, Comparable<String>, CharSequence {
    private final char value[]; // 문자열을 저장하는 final 배열 (불변성 보장)
}
```  

✅ **즉, `String` 객체의 값은 `final char[]` 배열에 저장되며, 한 번 할당되면 변경할 수 없습니다.**

---

## 3. `String`의 불변성 확인하기 🔄

### 3.1 `String` 객체 변경 시 새로운 객체 생성

## 배경
```java
public class StringImmutableExample {
    public static void main(String[] args) {
        String str1 = "Hello";
        String str2 = str1; // 같은 객체 참조

        str1 = str1 + " World"; // 새로운 객체 생성

        System.out.println("str1: " + str1); // "Hello World"
        System.out.println("str2: " + str2); // "Hello" (변경되지 않음)
    }
}
```
📌 **출력 결과:**
```
str1: Hello World
str2: Hello
```
> **📌 `str1`을 변경해도 `str2`는 여전히 원래 값을 유지 → 불변 객체!**

---

❌ **메모리 사용 증가** → 변경 시마다 새로운 객체 생성  
❌ **문자열 변경이 많을 경우 비효율적** → `StringBuilder` 사용 권장

✅ **즉, 문자열 변경이 많다면 `StringBuilder`를 사용하고, 문자열이 자주 변경되지 않는다면 `String`을 사용하는 것이 좋습니다.**

---


- **`String`은 불변 객체(Immutable)로, 한 번 생성되면 변경 불가능**
- **새로운 문자열이 할당되면 기존 객체를 변경하지 않고 새로운 객체를 생성**
- **불변성을 유지하는 이유는 보안, 안정성, 성능 최적화 때문**
- **문자열 변경이 많다면 `StringBuilder` 또는 `StringBuffer`를 사용하여 성능 최적화 가능**

> **👉🏻 `String`이 불변 객체라는 사실을 이해하면, 메모리 관리 및 성능 최적화에 도움이 됨!**  






### 3.2 `String`을 `new`로 생성할 경우 메모리 비교

#### ✅ 예제 (`new` 연산자 사용)
```java
public class StringMemoryExample {
    public static void main(String[] args) {
        String str1 = "Hello"; // 문자열 리터럴 (String Pool 사용)
        String str2 = "Hello"; // 같은 객체 참조

        String str3 = new String("Hello"); // Heap 영역에 새로운 객체 생성

        System.out.println(str1 == str2); // true (같은 객체)
        System.out.println(str1 == str3); // false (다른 객체)
    }
}
```
📌 **출력 결과:**
```
true
false
```
> **📌 `new String("Hello")`는 새로운 객체를 생성하여 기존 String Pool의 객체와 다름**

---





## 4. `StringBuilder`와 `StringBuffer` (Mutable String) 🔄

불변 객체 `String`과 다르게, **`StringBuilder`와 `StringBuffer`는 문자열을 변경할 수 있습니다.**  
✔ **`StringBuilder` → 싱글 스레드 환경에서 사용 (빠름)**  
✔ **`StringBuffer` → 멀티 스레드 환경에서 사용 (동기화 지원)**

#### ✅ 예제 (`StringBuilder` 활용)
```java
public class MutableStringExample {
    public static void main(String[] args) {
        StringBuilder sb = new StringBuilder("Hello");
        sb.append(" World"); // 원본 문자열을 직접 변경

        System.out.println(sb.toString()); // "Hello World"
    }
}
```
📌 **출력 결과:**
```
Hello World
```
> **📌 `StringBuilder`는 기존 객체를 변경하므로, `String`보다 성능이 좋음!**

---

## 5. 불변 객체의 장점과 단점 ⚖️

### ✅ **불변 객체(Immutable)의 장점**
✔ **안전성 (Thread-Safe)** → 멀티스레드 환경에서 동기화 없이 사용 가능  
✔ **캐싱 가능** → 변경되지 않으므로 재사용 가능  
✔ **예상치 못한 변경 방지** → 객체 공유 시 안전

