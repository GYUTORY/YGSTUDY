---
title: Spring Boot Profiles 가이드
tags: [framework, java, spring, spring-boot, profiles, configuration, environment]
updated: 2025-12-13
---

# Spring Boot Profiles

## 배경

### Spring Boot Profiles란?
Spring Boot에서는 환경(프로파일)에 따라 다른 설정을 적용할 수 있도록 Profiles 기능을 제공합니다. 개발(dev), 테스트(test), 운영(prod) 환경에 따라 서로 다른 설정 파일을 사용할 수 있어 환경별 맞춤 설정이 가능합니다.

### Profiles의 필요성
- **환경별 설정 분리**: 개발, 테스트, 운영 환경의 설정을 분리하여 관리
- **보안 강화**: 환경별로 다른 데이터베이스, API 키 등 민감한 정보 관리
- **유연한 배포**: 동일한 애플리케이션을 다양한 환경에 배포 가능
- **개발 효율성**: 환경 전환 시 코드 변경 없이 설정만으로 대응

### 기본 개념
- **Profile**: 특정 환경에 대한 설정 그룹
- **Active Profile**: 현재 활성화된 프로파일
- **Profile-specific Properties**: 특정 프로파일에만 적용되는 설정
- **Default Profile**: 프로파일이 지정되지 않았을 때 사용되는 기본 설정

## 핵심

### 1. Profiles 설정 방법

#### 기본 설정 파일 (application.yml)
```yaml
# application.yml - 공통 설정
server:
  port: 8080
spring:
  application:
    name: my-app
  datasource:
    url: jdbc:h2:mem:testdb
    driver-class-name: org.h2.Driver
```

#### 개발 환경 설정 (application-dev.yml)
```yaml
# application-dev.yml
spring:
  config:
    activate:
      on-profile: dev
  datasource:
    url: jdbc:mysql://localhost:3306/devdb
    username: dev_user
    password: dev_password
    driver-class-name: com.mysql.cj.jdbc.Driver
  jpa:
    hibernate:
      ddl-auto: create-drop
    show-sql: true

logging:
  level:
    root: DEBUG
    org.springframework.web: DEBUG
    com.example: DEBUG

server:
  port: 8081
```

#### 테스트 환경 설정 (application-test.yml)
```yaml
# application-test.yml
spring:
  config:
    activate:
      on-profile: test
  datasource:
    url: jdbc:h2:mem:testdb
    driver-class-name: org.h2.Driver
  jpa:
    hibernate:
      ddl-auto: create-drop
    show-sql: false

logging:
  level:
    root: INFO

server:
  port: 0  # 랜덤 포트
```

#### 운영 환경 설정 (application-prod.yml)
```yaml
# application-prod.yml
spring:
  config:
    activate:
      on-profile: prod
  datasource:
    url: jdbc:mysql://prod-server:3306/proddb
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}
    driver-class-name: com.mysql.cj.jdbc.Driver
  jpa:
    hibernate:
      ddl-auto: validate
    show-sql: false

logging:
  level:
    root: WARN
    com.example: INFO
  file:
    name: logs/application.log

server:
  port: 80
```

### 2. Profiles 활성화 방법

#### application.yml에서 기본 프로파일 설정
```yaml
# application.yml
spring:
  profiles:
    active: dev  # 기본적으로 dev 프로파일 활성화
```

#### JVM 옵션으로 설정
```bash
# 개발 환경
java -jar -Dspring.profiles.active=dev myapp.jar

# 운영 환경
java -jar -Dspring.profiles.active=prod myapp.jar

# 다중 프로파일
java -jar -Dspring.profiles.active=prod,monitoring myapp.jar
```

#### 환경 변수로 설정
```bash
# Linux/macOS
export SPRING_PROFILES_ACTIVE=prod

# Windows
set SPRING_PROFILES_ACTIVE=prod

# Docker
docker run -e SPRING_PROFILES_ACTIVE=prod myapp
```

#### IDE에서 설정
```properties
# IntelliJ IDEA VM Options
-Dspring.profiles.active=dev

# Eclipse VM Arguments
-Dspring.profiles.active=dev
```

### 3. @Profile 어노테이션 사용

#### 특정 프로파일에서만 Bean 활성화
```java
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;

@Service
@Profile("dev")
public class DevService {
    
    public DevService() {
        System.out.println("Development 환경에서 실행됩니다.");
    }
    
    public String getEnvironment() {
        return "Development";
    }
}

@Service
@Profile("prod")
public class ProdService {
    
    public ProdService() {
        System.out.println("Production 환경에서 실행됩니다.");
    }
    
    public String getEnvironment() {
        return "Production";
    }
}
```

#### 프로파일별 설정 클래스
```java
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;

@Configuration
public class DatabaseConfig {
    
    @Bean
    @Profile("dev")
    public DataSource devDataSource() {
        return DataSourceBuilder.create()
            .url("jdbc:h2:mem:devdb")
            .username("sa")
            .password("")
            .driverClassName("org.h2.Driver")
            .build();
    }
    
    @Bean
    @Profile("prod")
    public DataSource prodDataSource() {
        return DataSourceBuilder.create()
            .url("jdbc:mysql://prod-server:3306/proddb")
            .username("${DB_USERNAME}")
            .password("${DB_PASSWORD}")
            .driverClassName("com.mysql.cj.jdbc.Driver")
            .build();
    }
}
```

### 4. 다중 프로파일 설정

#### Spring Boot 3.x 방식
```yaml
# application-common.yml
spring:
  config:
    activate:
      on-profile: dev, test  # dev 또는 test 환경에서 적용
server:
  port: 8082

logging:
  level:
    com.example: DEBUG
```

#### 프로파일 그룹 사용
```yaml
# application.yml
spring:
  profiles:
    group:
      development: dev, h2, debug
      production: prod, mysql, monitoring
    active: development
```

## 예시

### 1. 실제 사용 사례

#### 마이크로서비스 환경별 설정
```yaml
# application-dev.yml
spring:
  config:
    activate:
      on-profile: dev
  cloud:
    discovery:
      enabled: false
  datasource:
    url: jdbc:h2:mem:testdb

management:
  endpoints:
    web:
      exposure:
        include: "*"
  endpoint:
    health:
      show-details: always

# application-prod.yml
spring:
  config:
    activate:
      on-profile: prod
  cloud:
    discovery:
      enabled: true
      service-id: ${spring.application.name}
  datasource:
    url: jdbc:mysql://${DB_HOST}:${DB_PORT}/${DB_NAME}
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics
  endpoint:
    health:
      show-details: when-authorized
```

#### 프로파일별 외부 API 설정
```java
@Configuration
@ConfigurationProperties(prefix = "api")
@Data
public class ApiConfig {
    
    private String baseUrl;
    private String apiKey;
    private int timeout;
    
    @Bean
    @Profile("dev")
    public RestTemplate devRestTemplate() {
        RestTemplate restTemplate = new RestTemplate();
        restTemplate.setRequestFactory(new SimpleClientHttpRequestFactory());
        ((SimpleClientHttpRequestFactory) restTemplate.getRequestFactory())
            .setConnectTimeout(5000);
        return restTemplate;
    }
    
    @Bean
    @Profile("prod")
    public RestTemplate prodRestTemplate() {
        RestTemplate restTemplate = new RestTemplate();
        restTemplate.setRequestFactory(new SimpleClientHttpRequestFactory());
        ((SimpleClientHttpRequestFactory) restTemplate.getRequestFactory())
            .setConnectTimeout(timeout);
        return restTemplate;
    }
}
```

### 2. 프로파일별 로깅 설정

#### 개발 환경 로깅
```yaml
# application-dev.yml
logging:
  level:
    root: DEBUG
    org.springframework.web: DEBUG
    org.hibernate.SQL: DEBUG
    org.hibernate.type.descriptor.sql.BasicBinder: TRACE
  pattern:
    console: "%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - %msg%n"
    file: "%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - %msg%n"
```

#### 운영 환경 로깅
```yaml
# application-prod.yml
logging:
  level:
    root: WARN
    com.example: INFO
  pattern:
    console: "%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - %msg%n"
    file: "%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - %msg%n"
  file:
    name: logs/application.log
    max-size: 100MB
    max-history: 30
```

## 운영 팁

### 1. 프로파일 관리 전략

#### 프로파일 네이밍 컨벤션
```yaml
# 권장 프로파일명
dev          # 개발 환경
test         # 테스트 환경
staging      # 스테이징 환경
prod         # 운영 환경
local        # 로컬 개발 환경
docker       # Docker 환경
```

#### 환경별 설정 우선순위
```yaml
# 1. application-{profile}.yml (프로파일별 설정)
# 2. application.yml (기본 설정)
# 3. 환경 변수
# 4. JVM 시스템 프로퍼티
```

### 2. 보안 고려사항

#### 민감한 정보 관리
```yaml
# application-prod.yml
spring:
  datasource:
    url: jdbc:mysql://${DB_HOST}:${DB_PORT}/${DB_NAME}
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}
  redis:
    host: ${REDIS_HOST}
    password: ${REDIS_PASSWORD}
```

#### 환경 변수 사용
```bash
# 운영 환경에서 환경 변수 설정
export DB_HOST=prod-db.example.com
export DB_PORT=3306
export DB_NAME=proddb
export DB_USERNAME=prod_user
export DB_PASSWORD=secure_password
```

### 3. 문제 해결

#### 일반적인 오류 및 해결방법
```yaml
# 잘못된 방식 (Spring Boot 2.4+)
spring:
  profiles:
    active: dev

# 올바른 방식 (Spring Boot 2.4+)
spring:
  config:
    activate:
      on-profile: dev
```

#### 프로파일 확인 방법
```java
@RestController
public class ProfileController {
    
    @Autowired
    private Environment environment;
    
    @GetMapping("/profile")
    public String getActiveProfile() {
        return String.join(", ", environment.getActiveProfiles());
    }
    
    @GetMapping("/profiles")
    public Map<String, Object> getProfiles() {
        Map<String, Object> profiles = new HashMap<>();
        profiles.put("active", environment.getActiveProfiles());
        profiles.put("default", environment.getDefaultProfiles());
        return profiles;
    }
}
```

## 참고

### Spring Boot 버전별 차이점

| Spring Boot 버전 | 프로파일 활성화 방식 | 설명 |
|------------------|---------------------|------|
| **2.3 이하** | `spring.profiles.active` | 기존 방식 |
| **2.4+** | `spring.config.activate.on-profile` | 새로운 방식 |
| **3.0+** | `spring.config.activate.on-profile` | 권장 방식 |

### 프로파일별 권장 설정

| 환경 | 데이터베이스 | 로깅 레벨 | 포트 | 보안 |
|------|-------------|-----------|------|------|
| **개발** | H2/로컬 DB | DEBUG | 8081 | 낮음 |
| **테스트** | H2/테스트 DB | INFO | 랜덤 | 낮음 |
| **스테이징** | 스테이징 DB | INFO | 8080 | 중간 |
| **운영** | 운영 DB | WARN | 80/443 | 높음 |

### 프로파일 사용 체크리스트

#### 설정 파일 구성
- [ ] 기본 설정 파일 (application.yml) 작성
- [ ] 환경별 설정 파일 작성 (application-{profile}.yml)
- [ ] 프로파일별 Bean 설정 (@Profile 어노테이션)
- [ ] 환경 변수 설정

#### 배포 및 운영
- [ ] 프로파일 활성화 방법 결정
- [ ] 환경별 설정 검증
- [ ] 보안 설정 적용
- [ ] 모니터링 설정

### 결론
Spring Boot Profiles는 환경별 설정을 효율적으로 관리할 수 있는 강력한 기능입니다. 적절한 프로파일 설정과 관리 전략을 통해 개발부터 운영까지 일관된 애플리케이션 배포가 가능합니다. 특히 보안과 성능을 고려한 환경별 설정 분리는 현대적인 애플리케이션 개발에 필수적입니다.

