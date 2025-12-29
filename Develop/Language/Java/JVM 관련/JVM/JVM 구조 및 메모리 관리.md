---
title: JVM
tags: [language, java, jvm-관련, jvm, jvm-구조-및-메모리-관리]
updated: 2025-12-29
---
# JVM 구조 및 메모리 관리

## 1. JVM(Java Virtual Machine)이란? 🤔

**JVM(Java Virtual Machine)**은 **Java 프로그램을 실행하기 위한 가상 머신**입니다.  
즉, **Java 코드(.java)를 바이트코드(.class)로 변환하여 실행할 수 있도록 해주는 역할**을 합니다.

> **✨ JVM의 핵심 기능**
> - **플랫폼 독립성 보장** → 한 번 작성한 코드(Java)는 어디서나 실행 가능 (Write Once, Run Anywhere)
> - **바이트코드(.class) 실행** → `javac` 컴파일 후 생성된 `.class` 파일을 실행
> - **메모리 관리 (Garbage Collection)** → 자동으로 불필요한 객체를 정리하여 메모리 최적화
> - **런타임 환경 제공** → Java 프로그램 실행을 위한 환경 구성

✅ **즉, JVM은 Java 프로그램을 실행하고, 메모리를 관리하며, GC(Garbage Collection)를 통해 최적화합니다.**

---

## 2. JVM의 구조 🏗

JVM은 **Class Loader, Runtime Data Area, Execution Engine, Native Interface** 등으로 구성됩니다.

### JVM의 주요 구성 요소

| 구성 요소 | 설명 |
|-----------|-----------------|
| **Class Loader** | `.class` 파일을 메모리에 로드 (동적 로딩 지원) |
| **Runtime Data Area** | JVM에서 프로그램이 실행되는 동안 데이터를 저장하는 영역 |
| **Execution Engine** | 바이트코드를 실행하는 엔진 (인터프리터 + JIT 컴파일러) |
| **Native Interface (JNI)** | Java와 외부 네이티브 코드(C, C++) 간 인터페이스 제공 |

📌 **JVM 구조 개요**
```
+-----------------------+
|   Execution Engine    |  → 바이트코드 실행 (인터프리터, JIT)
+-----------------------+
|   Runtime Data Area   |  → JVM 메모리 구조 (Heap, Stack, Method Area 등)
+-----------------------+
|   Class Loader        |  → 클래스 로딩 (로딩, 링크, 초기화)
+-----------------------+
|   Native Interface    |  → 네이티브 라이브러리 (JNI)
+-----------------------+
```  

✅ **즉, JVM은 Java 코드를 실행하기 위해 다양한 컴포넌트를 사용하여 관리됩니다.**

---

## 3. JVM의 메모리 구조

JVM의 메모리는 크게 **Heap, Stack, Method Area, PC Register, Native Method Stack**으로 구성됩니다.

📌 **JVM 메모리 구조**
```
+-----------------------> Method Area (클래스 메타데이터, static 변수, 상수)
|   Runtime Data Area  
+-----------------------> Heap (객체, 인스턴스 변수 저장)
|
+-----------------------> Stack (메서드 호출, 지역 변수, 프레임 관리)
|
+-----------------------> PC Register (현재 실행 중인 명령어 저장)
|
+-----------------------> Native Method Stack (JNI 호출 시 사용)
```  

### 3.1 **Heap 영역**

✔ **객체와 인스턴스 변수가 저장되는 공간**  
✔ GC(Garbage Collector)에 의해 관리됨  
✔ JVM의 가장 큰 메모리 영역

📌 **예제 (Heap 메모리 사용)**
```java
class Person {
    String name;  // Heap 영역에 저장됨
    int age;      // Heap 영역에 저장됨
}

public class HeapExample {
    public static void main(String[] args) {
        Person p1 = new Person();  // Heap에 객체 생성
        p1.name = "홍길동";
        p1.age = 30;
    }
}
```
> **📌 `new Person()`을 호출하면 `Heap` 영역에 객체가 생성됨!**

---

### 3.2 **Stack 영역**

✔ **메서드 호출 시 생성되는 지역 변수 및 메서드 실행 프레임을 저장**  
✔ **메서드 실행이 끝나면 자동으로 제거됨 (LIFO - Last In First Out)**  
✔ Heap 영역의 객체를 참조할 수도 있음

📌 **예제 (Stack 메모리 사용)**
```java
public class StackExample {
    public static void main(String[] args) {
        int x = 10; // Stack에 저장됨
        int y = 20; // Stack에 저장됨

        int result = add(x, y); // add() 호출 → 새로운 Stack Frame 생성
        System.out.println(result);
    }

    public static int add(int a, int b) {
        return a + b; // add() 실행이 끝나면 Stack에서 제거됨
    }
}
```
> **📌 `Stack` 영역은 메서드 호출 시 생성되며, 메서드가 종료되면 자동으로 제거됨!**

---

### 3.3 **Method Area (메서드 영역, 메타데이터 저장)** 🔒

✔ **클래스의 메타데이터(클래스 정보, static 변수, 상수 풀)를 저장하는 공간**  
✔ **JVM이 시작될 때 로드되며, 프로그램 종료 시까지 유지됨**

📌 **예제 (Method Area 사용)**
```java
class Example {
    static int count = 0; // Method Area에 저장됨

    public static void increment() {
        count++; // 모든 객체가 공유
    }
}
```
> **📌 `static` 변수는 `Method Area`에 저장되며, 프로그램 종료까지 유지됨!**

---

### 3.4 **PC Register (현재 실행 중인 명령어 저장)** 🏁

✔ **각 스레드가 현재 실행 중인 JVM 명령어 주소를 저장하는 공간**  
✔ **멀티스레드 환경에서 각 스레드는 개별적인 PC Register를 가짐**

📌 **예제 (멀티스레드에서 PC Register)**
```java
class Task extends Thread {
    public void run() {
        System.out.println("Thread 실행 중");
    }
}

public class PCRegisterExample {
    public static void main(String[] args) {
        Task t1 = new Task();
        Task t2 = new Task();
        t1.start(); // 개별 PC Register에서 실행
        t2.start(); // 개별 PC Register에서 실행
    }
}
```
> **📌 각 스레드는 개별적인 `PC Register`를 가지며, 실행할 명령어를 관리함!**

---

## 4. Garbage Collection (GC)

JVM의 **Garbage Collector(GC)**는 **Heap 영역에서 더 이상 사용되지 않는 객체를 자동으로 제거하는 역할**을 합니다.

✔ **GC는 개발자가 직접 객체를 해제할 필요 없이 자동으로 동작**  
✔ **Stop-The-World 이벤트 발생 (GC 실행 시 모든 스레드가 일시 정지됨)**  
✔ **GC 알고리즘 (Serial GC, Parallel GC, G1 GC 등)이 존재**

📌 **예제 (GC 확인하기)**
```java
public class GCExample {
    public static void main(String[] args) {
        for (int i = 0; i < 10000; i++) {
            new Person(); // 불필요한 객체 생성 (GC가 자동 정리)
        }
        System.gc(); // 명시적으로 GC 호출 (필수는 아님)
    }
}
```
> **📌 `System.gc()`는 GC 요청을 보낼 뿐, 즉시 실행되는 것은 보장되지 않음!**

---

## 배경

- **JVM은 Java 프로그램을 실행하는 가상 머신으로, 메모리 관리와 실행 환경을 제공**
- **JVM 메모리는 Heap, Stack, Method Area 등으로 구성되며, Garbage Collector(GC)가 자동 관리**
- **Heap은 객체가 저장되는 공간, Stack은 메서드 실행을 위한 지역 변수 저장**
- **Garbage Collection을 통해 불필요한 객체를 자동으로 제거하여 메모리를 최적화**

> **👉🏻 JVM 구조와 메모리 관리를 이해하면, Java 애플리케이션의 성능 최적화에 도움이 됨!**  










