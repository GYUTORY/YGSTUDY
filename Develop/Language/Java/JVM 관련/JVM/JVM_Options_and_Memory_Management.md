
# Java - JVM 옵션 및 메모리 관리 이해

## JVM이란?
JVM(Java Virtual Machine)은 자바 바이트코드를 실행하기 위한 가상 머신입니다. JVM은 플랫폼에 독립적으로 동작하며, 메모리 관리, JIT 컴파일, 가비지 컬렉션과 같은 중요한 기능을 제공합니다.

---

## JVM 메모리 구조
JVM은 프로그램 실행 중에 사용하는 메모리를 여러 영역으로 나눕니다.

1. **메소드 영역(Method Area)**
    - 클래스 로드 정보, 상수, 정적 변수, 메소드 코드가 저장됩니다.

2. **힙(Heap)**
    - 객체가 생성되고 저장되는 영역입니다.
    - 가비지 컬렉션의 대상이 됩니다.

3. **스택(Stack)**
    - 각 스레드마다 생성되는 영역으로, 메서드 호출과 관련된 지역 변수, 호출 스택 정보가 저장됩니다.

4. **PC 레지스터(Program Counter Register)**
    - 현재 실행 중인 명령의 주소를 저장합니다.

5. **네이티브 메서드 스택(Native Method Stack)**
    - 네이티브 코드를 실행하기 위한 스택입니다.

---

## JVM 주요 옵션
JVM 실행 시 다양한 옵션을 제공하여 메모리 크기, 성능 튜닝 등을 설정할 수 있습니다.

### 메모리 설정 옵션
- `-Xms<size>` : 힙 메모리의 초기 크기 설정 (예: `-Xms512m`)
- `-Xmx<size>` : 힙 메모리의 최대 크기 설정 (예: `-Xmx1024m`)
- `-Xss<size>` : 스레드 스택 크기 설정 (예: `-Xss1m`)
- `-XX:MetaspaceSize=<size>` : 메타스페이스 초기 크기 설정 (Java 8 이상)
- `-XX:MaxMetaspaceSize=<size>` : 메타스페이스 최대 크기 설정

### 가비지 컬렉션(GC) 옵션
- `-XX:+UseSerialGC` : 단일 스레드 가비지 컬렉션 사용
- `-XX:+UseParallelGC` : 병렬 가비지 컬렉션 사용
- `-XX:+UseG1GC` : G1 가비지 컬렉션 사용 (권장)
- `-XX:+PrintGCDetails` : GC 동작 상세 정보 출력

### 디버깅 및 로깅 옵션
- `-XX:+PrintFlagsFinal` : JVM에서 사용 중인 모든 설정 플래그 출력
- `-Xlog:gc` : 가비지 컬렉션 로그 출력
- `-XX:+HeapDumpOnOutOfMemoryError` : OutOfMemoryError 발생 시 힙 덤프 생성

---

## JVM 메모리 관리 예제
아래는 JVM 옵션을 설정하여 프로그램을 실행하고, GC 동작을 관찰하는 간단한 예제입니다.

### 예제 프로그램
```java
import java.util.ArrayList;
import java.util.List;

public class MemoryManagementExample {
    public static void main(String[] args) {
        List<String> list = new ArrayList<>();
        for (int i = 0; i < 1000000; i++) {
            list.add("데이터 " + i);
            if (i % 100000 == 0) {
                System.out.println("생성된 객체 수: " + i);
            }
        }
    }
}
```

### 실행 명령
다음 명령어를 통해 JVM 메모리 설정 및 GC 로그를 확인할 수 있습니다.
```bash
java -Xms256m -Xmx512m -XX:+UseG1GC -Xlog:gc MemoryManagementExample
```

### 로그 분석
실행 중 출력된 GC 로그는 메모리 사용량과 GC가 동작한 시점에 대한 정보를 제공합니다.

---

## 주의사항
1. **적절한 메모리 크기 설정**: 지나치게 큰 힙 크기를 설정하면 시스템 메모리 부족 문제가 발생할 수 있습니다.
2. **GC 알고리즘 선택**: 애플리케이션 특성에 맞는 GC 알고리즘을 선택하세요.
3. **성능 테스트 필수**: JVM 옵션 변경 후 애플리케이션 성능 테스트를 수행해야 합니다.

---

## 결론
JVM 옵션과 메모리 관리는 Java 애플리케이션 성능 최적화의 중요한 부분입니다. 메모리 구조와 GC의 동작 방식을 이해하고, 적절한 JVM 옵션을 설정하여 애플리케이션의 안정성과 성능을 보장할 수 있습니다.
