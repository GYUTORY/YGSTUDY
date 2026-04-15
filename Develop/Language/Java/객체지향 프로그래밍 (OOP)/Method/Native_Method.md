---
title: Native Method
tags: [language, java, 객체지향-프로그래밍-oop, method, nativemethod, jni, jnr, panama]
updated: 2026-04-15
---

# 네이티브 메서드(Native Method)

## 네이티브 메서드란

Java가 아닌 다른 언어(주로 C, C++)로 작성된 메서드다. `native` 키워드를 붙여 선언하고, 실제 구현은 C/C++ 쪽에 둔다. JVM이 JNI(Java Native Interface)를 통해 네이티브 코드를 호출하는 구조다.

```java
public class SystemCall {
    public native void printNativeMessage();

    static {
        System.loadLibrary("NativeLib");
    }

    public static void main(String[] args) {
        new SystemCall().printNativeMessage();
    }
}
```

`native` 키워드가 붙은 메서드는 Java 쪽에 본문이 없다. 컴파일은 되지만 실행 시점에 네이티브 라이브러리가 로드되어 있어야 한다.

## 언제 쓰는가

- OS 시스템 콜 직접 호출이 필요한 경우 (파일 시스템, 프로세스 관리 등)
- 기존 C/C++ 라이브러리를 Java에서 사용해야 하는 경우
- JVM 위에서는 불가능한 하드웨어 직접 제어가 필요한 경우
- 성능이 극도로 중요한 연산 (암호화, 이미지 처리 등)

실무에서는 성능 때문에 네이티브 메서드를 쓰는 경우보다, 기존 C/C++ 라이브러리를 연동해야 해서 쓰는 경우가 훨씬 많다. JVM의 JIT 컴파일러가 충분히 빠르기 때문에 단순 연산 속도 차이는 크지 않다.

## JNI 구현 과정

### 1단계: Java에서 native 메서드 선언

```java
public class NativeExample {
    public native void sayHello();

    static {
        System.loadLibrary("NativeLib");
    }

    public static void main(String[] args) {
        new NativeExample().sayHello();
    }
}
```

### 2단계: JNI 헤더 파일 생성

Java 8까지는 `javah`를 썼지만, Java 9부터는 `javac -h`로 대체됐다.

```sh
# Java 9+
javac -h . NativeExample.java

# Java 8 이하
javac NativeExample.java
javah -jni NativeExample
```

### 3단계: C 코드로 구현

```c
#include <jni.h>
#include <stdio.h>
#include "NativeExample.h"

JNIEXPORT void JNICALL Java_NativeExample_sayHello(JNIEnv *env, jobject obj) {
    printf("Hello from C!\n");
}
```

함수 이름 규칙은 `Java_{패키지}_{클래스}_{메서드}` 형태다. 패키지가 `com.example`이면 `Java_com_example_NativeExample_sayHello`가 된다. 이 이름이 하나라도 틀리면 `UnsatisfiedLinkError`가 발생한다.

### 4단계: 공유 라이브러리 빌드

```sh
# Linux
gcc -shared -o libNativeLib.so \
    -I${JAVA_HOME}/include \
    -I${JAVA_HOME}/include/linux \
    NativeExample.c -fPIC

# macOS
gcc -shared -o libNativeLib.dylib \
    -I${JAVA_HOME}/include \
    -I${JAVA_HOME}/include/darwin \
    NativeExample.c -fPIC

# Windows
gcc -shared -o NativeLib.dll \
    -I"%JAVA_HOME%\include" \
    -I"%JAVA_HOME%\include\win32" \
    NativeExample.c
```

### 5단계: 실행

```sh
java -Djava.library.path=. NativeExample
# 출력: Hello from C!
```

`java.library.path`를 지정하지 않으면 시스템 기본 경로에서만 라이브러리를 찾는다. 개발 중에는 `-Djava.library.path=.`을 붙이는 게 편하다.

## UnsatisfiedLinkError 트러블슈팅

JNI를 쓸 때 가장 자주 만나는 에러가 `UnsatisfiedLinkError`다. 원인별로 정리하면 다음과 같다.

**라이브러리를 찾지 못하는 경우**

```
java.lang.UnsatisfiedLinkError: no NativeLib in java.library.path
```

`java.library.path`에 라이브러리 파일이 없다. 경로를 확인하거나 `System.load()`로 절대 경로를 지정한다.

```java
// 절대 경로로 로드
System.load("/opt/libs/libNativeLib.so");
```

**함수 이름이 매칭되지 않는 경우**

```
java.lang.UnsatisfiedLinkError: NativeExample.sayHello()V
```

C 쪽 함수 이름이 JNI 네이밍 규칙과 맞지 않는다. 패키지명을 변경하거나 클래스를 리팩토링한 뒤 헤더를 다시 생성하지 않으면 이 에러가 난다. `javac -h`로 헤더를 다시 만들고 C 코드의 함수 이름을 맞춰야 한다.

**아키텍처 불일치**

64비트 JVM에서 32비트 라이브러리를 로드하거나 그 반대인 경우 발생한다. `file` 명령어로 확인할 수 있다.

```sh
file libNativeLib.so
# 출력 예: ELF 64-bit LSB shared object, x86-64
```

## `System.loadLibrary()` vs `System.load()`

| 메서드 | 동작 |
|--------|------|
| `System.loadLibrary("NativeLib")` | `java.library.path`에서 `libNativeLib.so` (또는 `.dll`)를 찾는다 |
| `System.load("/full/path/libNativeLib.so")` | 절대 경로로 직접 로드한다 |

배포 환경에서는 `loadLibrary()`가 일반적이지만, 개발 중이나 테스트 시에는 `load()`로 절대 경로를 지정하는 게 디버깅하기 편하다.

## JNI 대안: JNA와 Panama API

JNI는 C 코드를 직접 작성해야 하고 헤더 생성, 빌드 과정이 번거롭다. 이런 문제를 줄이기 위한 대안이 있다.

### JNA (Java Native Access)

C 코드 작성 없이 Java에서 바로 네이티브 함수를 호출할 수 있다. 내부적으로 libffi를 사용한다.

```java
import com.sun.jna.Library;
import com.sun.jna.Native;

public interface CLibrary extends Library {
    CLibrary INSTANCE = Native.load("c", CLibrary.class);
    void printf(String format, Object... args);
}

// 사용
CLibrary.INSTANCE.printf("Hello from JNA\n");
```

JNI와 비교하면 헤더 생성이나 C 글루 코드가 필요 없어서 개발 속도가 빠르다. 다만 호출마다 libffi를 거치기 때문에 JNI보다 느리다. 호출 빈도가 높은 경우 성능 차이가 체감될 수 있다.

### Panama API (Java 22+, Foreign Function & Memory API)

Java 22에서 정식 도입된 API로, JNI를 대체하는 것이 목표다. C 코드 작성 없이 Java만으로 네이티브 함수 호출과 메모리 관리가 가능하다.

```java
import java.lang.foreign.*;
import java.lang.invoke.MethodHandle;

// C의 strlen 함수 호출
Linker linker = Linker.nativeLinker();
SymbolLookup stdlib = linker.defaultLookup();

MethodHandle strlen = linker.downcallHandle(
    stdlib.find("strlen").orElseThrow(),
    FunctionDescriptor.of(ValueLayout.JAVA_LONG, ValueLayout.ADDRESS)
);

try (Arena arena = Arena.ofConfined()) {
    MemorySegment str = arena.allocateFrom("Hello");
    long len = (long) strlen.invoke(str);
    // len = 5
}
```

Panama API는 JNI, JNA와 비교해서 다음 차이가 있다.

| 항목 | JNI | JNA | Panama API |
|------|-----|-----|------------|
| C 코드 작성 | 필요 | 불필요 | 불필요 |
| 빌드 과정 | 복잡 | 없음 | 없음 |
| 성능 | 빠름 | 느림 | JNI와 비슷 |
| 메모리 관리 | 수동 | 자동 | Arena 기반 |
| 최소 Java 버전 | 1.1 | 1.4 | 22 |

새 프로젝트에서 Java 22 이상을 쓸 수 있다면 Panama API가 가장 낫다. JNI의 복잡한 빌드 과정 없이 JNI 수준의 성능을 낼 수 있다.

## 장점과 단점

**장점**

- OS API나 하드웨어를 직접 다룰 수 있다
- 기존 C/C++ 라이브러리를 재작성 없이 사용할 수 있다
- 특정 연산에서 JVM보다 빠른 성능을 낼 수 있다

**단점**

- 플랫폼마다 별도 빌드가 필요하다. Linux, macOS, Windows 각각 라이브러리를 만들어야 한다
- GC가 네이티브 메모리를 관리하지 않는다. 메모리 누수를 직접 신경 써야 한다
- JVM 크래시 디버깅이 어렵다. 네이티브 코드에서 세그폴트가 나면 JVM 전체가 죽는다
- JNI 경계를 넘을 때마다 오버헤드가 있다. 호출 횟수를 줄이는 설계가 필요하다
