# JVM 구조 및 메모리 관리

Java Virtual Machine(JVM)은 Java 프로그램을 실행하기 위한 가상 환경으로, Java의 플랫폼 독립성을 제공하는 핵심 요소입니다. JVM은 프로그램의 실행을 관리하고 메모리와 리소스를 효율적으로 활용합니다.

---

## **JVM 구조**
JVM은 크게 다음과 같은 구성 요소로 이루어져 있습니다.

1. **클래스 로더 시스템 (Class Loader Subsystem)**
    - Java 클래스 파일(`.class`)을 로드하고, 검증 및 링크를 수행.
    - **동작 과정**:
        1. **로딩(Loading)**: 클래스를 메모리로 읽어들임.
        2. **검증(Verification)**: 바이트코드가 유효한지 확인.
        3. **준비(Preparation)**: 클래스의 정적 변수와 메서드 준비.
        4. **해석(Resolution)**: 심볼릭 레퍼런스를 실제 메모리 주소로 변환.

2. **실행 엔진 (Execution Engine)**
    - Java 바이트코드를 실제 명령어로 변환하여 실행.
    - 주요 구성 요소:
        - **인터프리터(Interpreter)**: 바이트코드를 한 줄씩 실행.
        - **JIT 컴파일러(Just-In-Time Compiler)**: 자주 실행되는 코드를 네이티브 코드로 변환하여 성능 향상.
        - **가비지 컬렉터(Garbage Collector)**: 메모리 관리를 자동화.

3. **메모리 영역 (Memory Area)**
    - JVM의 메모리 구조는 여러 영역으로 나뉘어 프로그램의 데이터를 관리.
    - 자세한 내용은 아래 "메모리 구조"에서 다룹니다.

---

## **JVM 메모리 구조**
JVM 메모리는 크게 다음과 같이 구분됩니다.

### **1. 메서드 영역 (Method Area)**
- **역할**: 클래스 수준의 정보를 저장.
- **내용**: 클래스 메타데이터, 정적 변수, 상수 풀, 메서드 코드.

### **2. 힙 영역 (Heap Area)**
- **역할**: 객체와 배열을 저장.
- **특징**:
    - JVM에서 가장 큰 메모리 영역.
    - 가비지 컬렉션이 동작하는 영역.

### **3. 스택 영역 (Stack Area)**
- **역할**: 메서드 호출 시 생성되는 프레임 저장.
- **내용**:
    - 지역 변수
    - 메서드 매개변수
    - 반환값
- **특징**: 각 스레드에 독립적으로 할당.

### **4. 프로그램 카운터 (Program Counter, PC)**
- **역할**: 현재 실행 중인 명령어의 주소를 저장.

### **5. 네이티브 메서드 스택 (Native Method Stack)**
- **역할**: 네이티브 코드를 실행할 때 사용.

---

## **가비지 컬렉션 (Garbage Collection)**
가비지 컬렉션은 더 이상 참조되지 않는 객체를 자동으로 제거하여 메모리를 확보하는 기능입니다.

### **동작 원리**
1. **Mark (표시)**: 참조되는 객체를 식별.
2. **Sweep (제거)**: 참조되지 않는 객체를 메모리에서 제거.
3. **Compact (압축)**: 남은 객체를 힙 메모리 상에서 정리.

### **GC의 영역**
- **Young Generation (영 제너레이션)**:
    - 객체가 생성되는 영역.
    - 대부분의 객체는 이곳에서 생성 후 제거됨 (Minor GC).
- **Old Generation (올드 제너레이션)**:
    - Young Generation에서 살아남은 객체가 이동.
    - 큰 객체나 장수 객체를 관리.
- **Permanent Generation/Metaspace**:
    - 클래스 메타데이터를 저장.
    - Java 8부터 Metaspace로 변경.

### **GC의 종류**
1. **Serial GC**: 단일 스레드 기반. 작은 애플리케이션에 적합.
2. **Parallel GC**: 다중 스레드 기반. 대규모 데이터 처리에 적합.
3. **G1 GC**: 빠른 응답 시간과 효율적인 메모리 관리를 제공.

---

## **예제: 가비지 컬렉션 시뮬레이션**
다음 예제는 객체 생성 및 가비지 컬렉션의 동작을 시뮬레이션합니다.

### 코드:
```java
public class GarbageCollectionExample {
    public static void main(String[] args) {
        System.out.println("Garbage Collection 시작");

        for (int i = 0; i < 1000; i++) {
            String temp = new String("객체 " + i);
        }

        System.gc(); // 명시적으로 Garbage Collector 호출
        System.out.println("Garbage Collection 완료");
    }

    @Override
    protected void finalize() throws Throwable {
        System.out.println("객체가 가비지 컬렉션에 의해 제거되었습니다.");
    }
}
```

### 출력 (예상)
```
Garbage Collection 시작
객체가 가비지 컬렉션에 의해 제거되었습니다.
Garbage Collection 완료
```

## JVM의 특징
### 1. 플랫폼 독립성
- Java 코드는 바이트코드로 컴파일되어 모든 JVM에서 실행 가능.
### 2. 플랫폼 독립성 자동 메모리 관리
- 가비지 컬렉션을 통해 메모리 누수를 방지.
### 3. 멀티스레딩 지원
- 각 스레드에 독립된 스택 영역 제공.

## 요약
- JVM은 Java 프로그램의 실행을 관리하며, 클래스 로더와 실행 엔진을 통해 바이트코드를 처리.
- 메모리 구조는 메서드 영역, 힙, 스택 등으로 나뉘며, 각 영역은 특정 데이터를 저장.
- 가비지 컬렉션은 메모리를 자동으로 관리하여 효율적인 리소스 사용을 보장.


