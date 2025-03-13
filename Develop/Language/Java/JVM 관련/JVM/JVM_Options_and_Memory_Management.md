# JVM 옵션 및 메모리 관리 🚀

## 1. JVM 옵션이란? 🤔

**JVM 옵션**은 **Java 애플리케이션의 성능을 최적화하고, 실행 환경을 조정하기 위해 사용하는 설정 값**입니다.  
JVM 실행 시 `java` 명령어 뒤에 **JVM 옵션을 추가하면 다양한 메모리 관리 및 성능 최적화 설정이 가능**합니다.

> **✨ JVM 옵션의 주요 역할**
> - **메모리 크기 조정 (Heap, Stack 크기 설정)**
> - **GC(Garbage Collection) 전략 설정**
> - **JIT(Just-In-Time) 컴파일러 옵션 조정**
> - **애플리케이션 모니터링 및 디버깅**

✅ **즉, JVM 옵션을 잘 활용하면 애플리케이션의 메모리 사용량과 성능을 최적화할 수 있습니다.**

---

## 2. JVM의 주요 메모리 영역 🔄

JVM은 **Heap, Stack, Metaspace, CodeCache** 등의 메모리 영역을 관리합니다.

📌 **JVM 메모리 구조 개요**
```
+--------------------------+
|      Code Cache         |  → JIT 컴파일된 코드 저장
+--------------------------+
|      Metaspace          |  → 클래스 메타데이터 저장
+--------------------------+
|        Heap             |  → 객체 및 인스턴스 저장 (GC 관리)
+--------------------------+
|       Stack             |  → 메서드 호출, 지역 변수 저장
+--------------------------+
```  

✅ **JVM 옵션을 통해 각 메모리 영역의 크기 및 동작 방식을 조정할 수 있습니다.**

---

## 3. JVM의 주요 옵션 및 설정 📌

### 3.1 **Heap 영역 크기 설정**

✔ **`-Xms<size>`** → 초기 Heap 크기 설정  
✔ **`-Xmx<size>`** → 최대 Heap 크기 설정

📌 **예제 (Heap 크기 설정)**
```sh
java -Xms512m -Xmx2g MyApplication
```
> **📌 초기 Heap 크기 512MB, 최대 Heap 크기 2GB로 설정**

---

### 3.2 **GC(Garbage Collection) 설정**

✔ **`-XX:+UseSerialGC`** → 단일 스레드 GC (싱글 스레드 환경에서 사용)  
✔ **`-XX:+UseParallelGC`** → 병렬 GC (멀티코어 환경에서 성능 최적화)  
✔ **`-XX:+UseG1GC`** → G1 GC (대형 애플리케이션에서 성능 최적화)

📌 **예제 (G1 GC 사용)**
```sh
java -XX:+UseG1GC MyApplication
```
> **📌 G1 GC를 사용하여 메모리 관리 최적화**

---

### 3.3 **Stack 크기 설정**

✔ **`-Xss<size>`** → 각 스레드의 Stack 크기 설정

📌 **예제 (Stack 크기 설정)**
```sh
java -Xss512k MyApplication
```
> **📌 각 스레드의 Stack 크기를 512KB로 설정**

---

### 3.4 **Metaspace 크기 설정 (JDK 8 이상)**

✔ **`-XX:MetaspaceSize=<size>`** → 초기 Metaspace 크기 설정  
✔ **`-XX:MaxMetaspaceSize=<size>`** → 최대 Metaspace 크기 설정

📌 **예제 (Metaspace 크기 설정)**
```sh
java -XX:MetaspaceSize=128m -XX:MaxMetaspaceSize=512m MyApplication
```
> **📌 초기 Metaspace 크기 128MB, 최대 크기 512MB로 설정**

---

### 3.5 **GC 로그 출력 설정**

✔ **`-Xlog:gc`** → GC 로그 출력  
✔ **`-Xlog:gc:gc.log`** → GC 로그를 파일로 저장

📌 **예제 (GC 로그 설정)**
```sh
java -Xlog:gc:gc.log MyApplication
```
> **📌 GC 로그를 `gc.log` 파일로 저장하여 분석 가능**

---

## 4. GC(Garbage Collection) 알고리즘 비교 🔄

| GC 유형 | 특징 |
|-----------|-----------------|
| **Serial GC** | 단일 스레드 GC (싱글 스레드 환경에서 사용) |
| **Parallel GC** | 멀티스레드 기반 GC (멀티코어 환경에서 성능 최적화) |
| **CMS GC** | GC 시간 최소화 (응답 속도가 중요한 서비스에 적합) |
| **G1 GC** | 대형 애플리케이션에 최적화된 GC (JDK 9 이상 기본 GC) |

📌 **G1 GC 설정 예제**
```sh
java -XX:+UseG1GC MyApplication
```

✅ **애플리케이션 특성에 맞는 GC 전략을 선택하면 성능 최적화 가능!**

---

## 5. JVM 메모리 최적화 방법 🚀

✔ **Heap 크기 조정 (`-Xms`, `-Xmx`)**  
✔ **GC 알고리즘 최적화 (`-XX:+UseG1GC`)**  
✔ **Metaspace 크기 설정 (`-XX:MaxMetaspaceSize`)**  
✔ **불필요한 객체 최소화 (객체 재사용, `StringBuilder` 활용)**  
✔ **메모리 누수 방지 (WeakReference, AutoCloseable 활용)**

✅ **JVM 옵션을 적절히 설정하면 Java 애플리케이션의 성능을 극대화할 수 있습니다.**

---

## 📌 결론

- **JVM 옵션을 활용하면 Java 애플리케이션의 메모리 사용 및 성능을 최적화 가능**
- **Heap, Stack, Metaspace 등의 크기를 설정하여 실행 환경 조정**
- **적절한 GC 알고리즘을 선택하면 메모리 관리 효율성 향상**
- **GC 로그 및 모니터링 도구를 활용하여 성능 분석 가능**

> **👉🏻 JVM 옵션과 메모리 관리를 잘 이해하면 애플리케이션의 안정성과 성능을 향상시킬 수 있음!**  

