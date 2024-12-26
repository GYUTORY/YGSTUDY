
# Spring Boot 2.0 vs Spring Boot 3.0

## 1. Spring Boot 2.0
Spring Boot 2.0은 2018년에 릴리스되었으며 Spring Framework 5.0을 기반으로 설계되었습니다. 주요 변경 사항은 리액티브 프로그래밍 지원과 다양한 성능 개선 사항입니다.

### 주요 특징
1. **리액티브 프로그래밍 지원**  
   Spring WebFlux를 통해 리액티브 애플리케이션 개발이 가능해졌습니다. Netty 기반의 비동기 처리로 고성능 애플리케이션 개발이 가능합니다.

   ```java
   @RestController
   public class ReactiveController {
       @GetMapping("/reactive")
       public Mono<String> reactiveEndpoint() {
           return Mono.just("Hello, Reactive World!");
       }
   }
   ```

2. **Actuator 개선**  
   애플리케이션의 상태와 메트릭을 모니터링하는 데 사용되는 Actuator가 더욱 강력해졌습니다.

   ```yaml
   management:
     endpoints:
       web:
         exposure:
           include: "*"
   ```

3. **Kotlin 지원 강화**  
   Kotlin 언어 지원이 추가되어 더 현대적인 애플리케이션 개발이 가능해졌습니다.

---

## 2. Spring Boot 3.0
Spring Boot 3.0은 2022년 말에 릴리스되었으며, Java 17 이상과 Spring Framework 6.0을 기반으로 설계되었습니다. 이는 모던 자바 기능과 새로운 Jakarta EE 기반으로의 전환을 포함합니다.

### 주요 특징
1. **Jakarta EE 전환**  
   Java EE에서 Jakarta EE로 전환되었습니다. 이는 패키지 변경을 포함하며, 기존 Java EE 애플리케이션을 Spring Boot 3.0으로 마이그레이션하려면 리팩토링이 필요합니다.

   ```java
   import jakarta.persistence.Entity;
   import jakarta.persistence.Id;

   @Entity
   public class User {
       @Id
       private Long id;
       private String name;
   }
   ```

2. **Java 17 이상 필수**  
   Java 17 이상을 요구하며, Record 및 Pattern Matching과 같은 최신 언어 기능을 활용할 수 있습니다.

   ```java
   public record UserDTO(String name, int age) {}
   ```

3. **Native 지원**  
   GraalVM을 사용한 네이티브 이미지 빌드를 공식 지원하여 메모리 사용량과 시작 시간을 크게 줄일 수 있습니다.

   ```bash
   ./mvnw native:compile
   ```

4. **관찰 가능성(Observability) 개선**  
   Micrometer와 통합하여 메트릭, 추적 및 로그의 통합 모니터링이 용이합니다.

---

## 3. 주요 차이점
| **항목**           | **Spring Boot 2.0**               | **Spring Boot 3.0**               |
|-------------------|----------------------------------|----------------------------------|
| **기반 플랫폼**    | Java 8 이상, Java EE              | Java 17 이상, Jakarta EE          |
| **리액티브 지원**   | Spring WebFlux                    | Spring WebFlux (추가 개선)         |
| **네이티브 지원**   | 제한적 (실험적 지원)               | 공식 지원 (GraalVM 통합)           |
| **관찰 가능성**     | Actuator를 통해 제한적 지원         | Micrometer 통합으로 향상된 지원     |
| **패키지 변경**     | Java EE 사용                      | Jakarta EE 패키지 변경             |

---

## 4. 마이그레이션 가이드
Spring Boot 2.x에서 3.x로 마이그레이션하려면 다음을 확인해야 합니다.

1. **Java 버전 확인**  
   Java 17 이상으로 업그레이드합니다.

2. **패키지 변경**  
   Java EE 패키지를 Jakarta EE 패키지로 수정합니다.

   ```diff
   - import javax.persistence.Entity;
   - import javax.persistence.Id;
   + import jakarta.persistence.Entity;
   + import jakarta.persistence.Id;
   ```

3. **의존성 업데이트**  
   Gradle 또는 Maven 설정에서 Spring Boot 버전을 3.0 이상으로 업데이트합니다.

   ```xml
   <parent>
       <groupId>org.springframework.boot</groupId>
       <artifactId>spring-boot-starter-parent</artifactId>
       <version>3.0.0</version>
   </parent>
   ```

---

## 5. 결론
Spring Boot 2.0은 리액티브 프로그래밍과 성능 개선을 중심으로 한 버전이며, Spring Boot 3.0은 모던 Java 기능과 네이티브 지원에 중점을 둔 최신 버전입니다. 새로운 프로젝트를 시작하거나 기존 애플리케이션을 마이그레이션할 때 이 차이점을 고려하여 적절한 버전을 선택하십시오.
