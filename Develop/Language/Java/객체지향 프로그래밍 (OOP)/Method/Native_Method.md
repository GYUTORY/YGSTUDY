
# 네이티브 메서드 (Native Method)

## 개념
네이티브 메서드(Native Method)란 **Java 코드가 아닌 다른 프로그래밍 언어(C/C++)로 작성된 메서드**를 호출하기 위해 Java에서 사용하는 메서드입니다.  
Java 애플리케이션에서 네이티브 메서드를 사용하면, Java가 제공하지 않는 기능이나 기존 시스템과의 통합이 가능해집니다.

### 주요 특징
1. **JNI(Java Native Interface)**를 통해 네이티브 메서드를 호출합니다.
2. 성능 개선이나 하드웨어에 밀접한 작업, 기존의 네이티브 라이브러리 활용에 적합합니다.
3. 운영 체제와 밀접하게 통합되거나 플랫폼별 기능을 지원할 때 사용됩니다.

---

## 사용 목적
- **운영 체제 기능 접근**: Java로 직접 수행할 수 없는 시스템 레벨 작업.
- **성능 향상**: Java보다 속도가 빠른 C/C++ 코드를 활용.
- **레거시 코드 활용**: 기존 C/C++ 라이브러리를 재사용.
- **특정 플랫폼 기능 사용**: 플랫폼 고유 API 호출.

---

## 예시

### 1. 네이티브 메서드 선언
Java에서는 `native` 키워드를 사용하여 네이티브 메서드를 선언합니다.  
이 메서드는 구현이 없으며, 네이티브 라이브러리에 의해 정의됩니다.

```java
public class NativeExample {
    // 네이티브 메서드 선언
    public native void printMessage();

    static {
        // 네이티브 라이브러리 로드
        System.loadLibrary("NativeLib");
    }

    public static void main(String[] args) {
        NativeExample example = new NativeExample();
        example.printMessage(); // 네이티브 메서드 호출
    }
}
```

---

### 2. 네이티브 코드 작성 (C 코드)
`printMessage` 메서드의 구현을 C로 작성합니다.

```c
#include <jni.h>
#include <stdio.h>
#include "NativeExample.h"

// 네이티브 메서드 구현
JNIEXPORT void JNICALL Java_NativeExample_printMessage(JNIEnv *env, jobject obj) {
    printf("안녕하세요, 네이티브 메서드입니다!\n");
}
```

---

### 3. 네이티브 코드 컴파일 및 사용
1. **헤더 파일 생성**: `javac -h . NativeExample.java` 명령으로 JNI 헤더 파일 생성.
2. **네이티브 코드 컴파일**: C 코드를 컴파일하여 공유 라이브러리 생성 (`.dll`, `.so` 등).
    - Windows: `gcc -shared -o NativeLib.dll -I"%JAVA_HOME%/include" -I"%JAVA_HOME%/include/win32" NativeExample.c`
    - Linux/Mac: `gcc -shared -o libNativeLib.so -I"$JAVA_HOME/include" -I"$JAVA_HOME/include/linux" NativeExample.c`

3. **라이브러리 로드 및 실행**: Java 애플리케이션에서 `System.loadLibrary`를 통해 라이브러리 로드 후 실행.

---

## 장점
1. **성능 향상**: Java보다 효율적인 네이티브 코드를 사용하여 성능을 높일 수 있습니다.
2. **기존 코드 활용**: 기존의 C/C++로 작성된 라이브러리를 재사용할 수 있습니다.
3. **하드웨어 접근**: 하드웨어와 밀접한 작업 수행 가능.

---

## 단점 및 주의점
1. **이식성 문제**: 네이티브 코드가 플랫폼 의존적이므로 코드의 이식성이 떨어질 수 있습니다.
2. **복잡성 증가**: Java와 C/C++ 간의 인터페이스 관리 및 디버깅이 복잡합니다.
3. **안전성 문제**: 네이티브 코드는 메모리 관리 및 보안 이슈를 유발할 수 있습니다.

---

## 결론
네이티브 메서드는 Java의 기능을 확장하고 성능을 높이는 데 유용하지만, 복잡성과 이식성 문제를 고려해야 합니다.  
현대 애플리케이션에서는 가급적 네이티브 메서드의 사용을 최소화하고, 필요 시 신중하게 설계 및 관리하는 것이 중요합니다.
