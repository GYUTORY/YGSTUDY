# Spring Boot Profiles ✨

## 1. Profiles 개념
Spring Boot에서는 **환경(프로파일)**에 따라 다른 설정을 적용할 수 있도록 `Profiles` 기능을 제공합니다.  
즉, 개발(`dev`), 테스트(`test`), 운영(`prod`) 환경에 따라 서로 다른 **설정 파일**을 사용할 수 있습니다.

---

## 2. Profiles 설정 방법

### 2.1 `application.yml`에서 프로파일 정의

```yaml
spring:
  profiles:
    active: dev  # 👉🏻 기본적으로 `dev` 프로파일을 활성화
```
💡 **설명**
- `spring.profiles.active` : 현재 활성화할 프로파일을 설정합니다.
- 위 설정에서는 **dev 환경을 기본 프로파일**로 사용합니다.

---

### 2.2 환경별 설정 파일 작성

Spring Boot는 다음과 같이 **환경별 설정 파일**을 만들 수 있습니다.

#### 1️⃣ **기본 설정 파일 (`application.yml`)**
```yaml
server:
  port: 8080
spring:
  application:
    name: my-app
```
💡 **설명**
- 모든 환경에서 공통으로 사용하는 설정입니다.
- 예: 애플리케이션 이름(`spring.application.name`)

#### 2️⃣ **개발 환경 (`application-dev.yml`)**
```yaml
spring:
  config:
    activate:
      on-profile: dev  # 👉🏻 `dev` 프로파일일 때만 활성화
server:
  port: 8081
logging:
  level:
    root: DEBUG
```
💡 **설명**
- `dev` 환경에서는 서버 포트를 **8081번**으로 설정합니다.
- 로그 레벨을 **DEBUG**로 설정하여 디버깅 정보를 더 많이 출력합니다.

#### 3️⃣ **운영 환경 (`application-prod.yml`)**
```yaml
spring:
  config:
    activate:
      on-profile: prod  # 👉🏻 `prod` 프로파일일 때만 활성화
server:
  port: 80
logging:
  level:
    root: WARN
```
💡 **설명**
- `prod` 환경에서는 **포트를 80번**(기본 HTTP 포트)으로 설정합니다.
- 로그 레벨을 **WARN**으로 설정하여 중요 로그만 출력합니다.

---

## 3. Profiles 적용 방법 🚀

### 3.1 `application.yml`에서 지정
```yaml
spring:
  profiles:
    active: dev
```
- `spring.profiles.active`로 기본 프로파일을 설정할 수 있습니다.
- `application-dev.yml` 설정이 적용됩니다.

---

### 3.2 JVM 옵션으로 설정
```shell
java -jar -Dspring.profiles.active=prod myapp.jar
```
- **운영 환경에서는 `prod` 설정을 적용**할 수 있습니다.

---

### 3.3 환경 변수로 설정
```shell
export SPRING_PROFILES_ACTIVE=prod
```
- 운영 서버에서는 환경 변수로 설정하는 것이 일반적입니다.

---

## 4. @Profile 애너테이션 사용

Spring Boot에서는 특정 **Bean을 특정 프로파일에서만 로드**할 수도 있습니다.

```java
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;

@Service
@Profile("dev")  // 👉🏻 이 Bean은 `dev` 환경에서만 활성화됨
public class DevService {
    public DevService() {
        System.out.println("Development 환경에서 실행됩니다.");
    }
}
```

💡 **설명**
- `@Profile("dev")`을 적용하면 `dev` 프로파일이 활성화된 경우에만 이 Bean이 등록됩니다.
- 운영 환경에서는 이 Bean이 **자동으로 제외**됩니다.

---

## 5. 다중 프로파일 설정 (Spring Boot 3.x 방식)

Spring Boot 3.x에서는 `spring.config.activate.on-profile`을 사용해야 합니다.

```yaml
spring:
  config:
    activate:
      on-profile: dev, test  # 👉🏻 `dev` 또는 `test` 환경에서만 적용
server:
  port: 8082
```

---

## 6. Profiles 관련 주요 오류 및 해결 방법 🔥

### ❌ `InactiveConfigDataAccessException` 오류 해결
```yaml
spring:
  profiles:
    active: local  # ❌ 최신 버전에서는 사용 불가
```
✅ **해결 방법**
```yaml
spring:
  config:
    activate:
      on-profile: local  # ✅ 올바른 방식
```

---

## 7. 정리 ✨
✅ Spring Boot에서 Profiles 기능을 사용하면 **환경별 맞춤 설정**이 가능하다.  
✅ `spring.config.activate.on-profile`을 사용하여 최신 방식으로 설정해야 한다.  
✅ `@Profile` 애너테이션을 사용하면 특정 Bean을 환경에 따라 다르게 관리할 수 있다.  
✅ `application.yml`, JVM 옵션, 환경 변수를 통해 Profile을 적용할 수 있다.

🔥 **이제 Spring Boot 프로젝트에서 Profiles를 활용해 보세요!**
