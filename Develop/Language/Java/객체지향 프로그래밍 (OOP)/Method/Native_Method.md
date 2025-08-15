---
title: Native Method
tags: [language, java, 객체지향-프로그래밍-oop, method, nativemethod]
updated: 2025-08-10
---
# 네이티브 메서드(Native Method) 개념 및 활용 🚀

## 1. 네이티브 메서드(Native Method)란? 🤔

**네이티브 메서드(Native Method)**란 **Java가 아닌 다른 언어(주로 C, C++)로 작성된 메서드**를 의미합니다.  
즉, **JNI(Java Native Interface)**를 이용하여 **Java에서 C/C++ 코드와 상호 작용**할 수 있도록 합니다.

> **✨ 네이티브 메서드의 특징**
> - Java가 직접 실행할 수 없는 **플랫폼 종속적인 기능(C/C++ API 등)을 호출할 때 사용**
> - **JNI(Java Native Interface)**를 사용하여 네이티브 코드와 통신
> - Java의 메모리 관리(GC)를 우회하여 **고성능 연산 수행 가능**
> - **운영체제(OS) 기능을 활용**하는 데 유용 (예: 하드웨어 제어, 시스템 호출)

---

## 2. 네이티브 메서드가 필요한 이유 🔍

✔ **성능 최적화** → C/C++의 네이티브 코드 실행 속도가 Java보다 빠름  
✔ **플랫폼 종속적인 기능 활용** → OS별 API 호출 가능  
✔ **기존 라이브러리와 연동** → Java에서 C/C++ 기반의 기존 코드를 재사용 가능

## 배경
```java
class SystemCall {
    public native void printNativeMessage(); // 네이티브 메서드 선언

    static {
        System.loadLibrary("NativeLib"); // 네이티브 라이브러리 로드
    }

    public static void main(String[] args) {
        new SystemCall().printNativeMessage(); // 네이티브 메서드 호출
    }
}
```
> **📌 `native` 키워드가 붙은 메서드는 Java가 아닌 다른 언어에서 구현됨!**

---


- **네이티브 메서드(Native Method)**는 Java가 아닌 C/C++로 구현된 메서드를 호출하는 기능
- **JNI(Java Native Interface)**를 통해 네이티브 코드와 Java 간 상호작용 가능
- **고성능 연산, OS API 호출, 하드웨어 제어 등에 유용하게 사용**
- **플랫폼 종속성이 있으므로 필요한 경우에만 사용해야 함**

> **👉🏻 네이티브 메서드는 Java만으로 해결할 수 없는 고성능 작업이 필요할 때 유용함!**










## 3. 네이티브 메서드 구현 과정 🛠️

네이티브 메서드는 다음 과정을 통해 구현됩니다.

1️⃣ **Java에서 `native` 메서드 선언**  
2️⃣ **JNI 헤더 파일 생성 (`javac` + `javah` 명령어 사용)**  
3️⃣ **C/C++로 네이티브 메서드 구현**  
4️⃣ **공유 라이브러리(`.dll` 또는 `.so`) 빌드**  
5️⃣ **Java에서 네이티브 라이브러리 로드(`System.loadLibrary()`) 후 실행**

---

## 4. 네이티브 메서드 예제 (Java + C 연동)

### **4.1 Java 코드 (네이티브 메서드 선언)**
```java
public class NativeExample {
    // 네이티브 메서드 선언 (C에서 구현)
    public native void sayHello();

    // 네이티브 라이브러리 로드
    static {
        System.loadLibrary("NativeLib");
    }

    public static void main(String[] args) {
        new NativeExample().sayHello(); // 네이티브 메서드 실행
    }
}
```

### **4.2 JNI 헤더 파일 생성 (`javac` + `javah`)**
터미널에서 다음 명령어 실행:
```sh
javac NativeExample.java  # 컴파일
javah -jni NativeExample   # JNI 헤더 파일 생성
```
➡ `NativeExample.h` 파일이 생성됨

### **4.3 C 코드 (네이티브 메서드 구현)**
```c
#include <jni.h>
#include <stdio.h>
#include "NativeExample.h"

JNIEXPORT void JNICALL Java_NativeExample_sayHello(JNIEnv *env, jobject obj) {
    printf("Hello from C!\n");
}
```

### **4.4 공유 라이브러리 컴파일**
리눅스/맥:
```sh
gcc -shared -o libNativeLib.so -I${JAVA_HOME}/include -I${JAVA_HOME}/include/linux NativeExample.c -fPIC
```
윈도우:
```sh
gcc -shared -o NativeLib.dll -I"%JAVA_HOME%\include" -I"%JAVA_HOME%\include\win32" NativeExample.c
```

### **4.5 실행 결과**
```sh
java NativeExample
```
출력:
```sh
Hello from C!
```
> **📌 Java에서 C 함수를 호출하여 네이티브 메시지를 출력!**

---

## 5. `System.loadLibrary()` vs. `System.load()` 차이점

| 메서드 | 설명 |
|--------|------|
| `System.loadLibrary("libName")` | `libName.so` 또는 `libName.dll`을 로드 (확장자 생략) |
| `System.load("C:/full/path/to/libName.dll")` | 라이브러리의 전체 경로를 지정하여 로드 |

✅ **대부분의 경우 `System.loadLibrary()`를 사용**하는 것이 편리함

---

## 6. 네이티브 메서드의 장점과 단점 ⚠️

✅ **장점**  
✔ **고성능 연산 가능** (Java보다 빠름)  
✔ **플랫폼 종속적인 기능 사용 가능** (OS API, 하드웨어 제어 등)  
✔ **기존 C/C++ 라이브러리 재사용 가능**

🚨 **단점**  
❌ **플랫폼 종속적** → OS별로 다른 라이브러리를 만들어야 함  
❌ **Java의 가비지 컬렉션(GC)과 호환 어려움**  
❌ **디버깅이 복잡함**

---

