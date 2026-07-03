---
title: Apache Tomcat
tags: [tomcat, servlet-container, java, war, jndi, connector, session-clustering]
updated: 2026-04-07
---

# Apache Tomcat

## Tomcat이란

Apache Tomcat은 Java Servlet, JSP, WebSocket을 실행하는 서블릿 컨테이너다. Apache Software Foundation에서 관리하며, Java로 작성됐다. 이름에 Apache가 붙어서 Apache HTTP Server와 헷갈리는 경우가 많은데, 완전히 다른 소프트웨어다. HTTP Server는 정적 파일을 서빙하는 웹 서버이고, Tomcat은 Java 애플리케이션을 실행하는 WAS(Web Application Server)다.

Spring Boot가 내장 Tomcat을 기본으로 쓰면서 별도 설치 없이 사용하는 경우가 많아졌지만, 레거시 시스템이나 WAR 배포 환경에서는 여전히 독립 Tomcat을 직접 운영한다. 독립 Tomcat을 쓸 때는 설정 파일 구조와 튜닝 포인트를 제대로 알아야 장애를 줄일 수 있다.

## 디렉토리 구조

Tomcat을 설치하면 아래 디렉토리가 생긴다. 각 디렉토리의 역할을 모르면 설정 변경할 때 삽질한다.

```
$CATALINA_HOME/
├── bin/          # 시작/종료 스크립트 (startup.sh, shutdown.sh, catalina.sh)
├── conf/         # 설정 파일 (server.xml, context.xml, web.xml, tomcat-users.xml)
├── lib/          # Tomcat 공통 라이브러리 (JDBC 드라이버 여기에 넣음)
├── logs/         # 로그 파일 (catalina.out, localhost_access_log)
├── webapps/      # WAR 파일 배포 경로
├── work/         # JSP 컴파일 결과물 (문제 생기면 이 디렉토리 지우고 재시작)
└── temp/         # 임시 파일
```

`CATALINA_HOME`과 `CATALINA_BASE`를 구분해야 한다. `CATALINA_HOME`은 Tomcat 바이너리 위치, `CATALINA_BASE`는 인스턴스별 설정/배포 위치다. 하나의 바이너리로 여러 인스턴스를 돌릴 때 `CATALINA_BASE`를 분리해서 사용한다. 단일 인스턴스면 둘 다 같은 경로다.

## server.xml 핵심 설정

server.xml은 Tomcat 전체 구조를 정의하는 파일이다. 계층 구조를 이해해야 설정을 제대로 할 수 있다.

```
Server (최상위, JVM 1개당 1개)
└── Service (Connector와 Engine을 묶는 단위)
    ├── Connector (클라이언트 요청을 받는 진입점)
    └── Engine (요청을 처리하는 엔진)
        └── Host (가상 호스트, 도메인 단위)
            └── Context (웹 애플리케이션 1개)
```

실제 server.xml 예시:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Server port="8005" shutdown="SHUTDOWN">

  <Service name="Catalina">

    <!-- HTTP Connector -->
    <Connector port="8080"
               protocol="org.apache.coyote.http11.Http11NioProtocol"
               connectionTimeout="20000"
               redirectPort="8443"
               maxThreads="200"
               minSpareThreads="25"
               acceptCount="100" />

    <!-- AJP Connector (앞단 Apache httpd 연동 시) -->
    <Connector port="8009"
               protocol="AJP/1.3"
               secretRequired="true"
               secret="my-ajp-secret"
               redirectPort="8443" />

    <Engine name="Catalina" defaultHost="localhost">
      <Host name="localhost" appBase="webapps"
            unpackWARs="true" autoDeploy="true">
      </Host>
    </Engine>

  </Service>
</Server>
```

여기서 주의할 것:

- `Server port="8005"`는 shutdown 명령을 받는 포트다. 운영 환경에서는 이 포트를 외부에서 접근 못하게 막아야 한다. 누군가 `telnet localhost 8005`로 접속해서 `SHUTDOWN` 문자열을 보내면 Tomcat이 꺼진다. shutdown 문자열을 랜덤 값으로 바꾸거나, port를 `-1`로 설정해서 비활성화하는 게 안전하다.
- `autoDeploy="true"`는 개발 환경에서는 편리한데, 운영에서는 끄는 게 맞다. webapps 디렉토리를 주기적으로 감시하면서 리소스를 소비하고, 의도하지 않은 배포가 일어날 수 있다.

## Connector 구성 (BIO / NIO / APR)

Connector는 클라이언트의 TCP 연결을 처리하는 컴포넌트다. 어떤 프로토콜 구현체를 쓰느냐에 따라 성능 특성이 달라진다.

### BIO (Blocking I/O)

```xml
<Connector port="8080"
           protocol="org.apache.coyote.http11.Http11Protocol"
           maxThreads="200" />
```

요청 하나당 스레드 하나를 할당한다. 동시 접속이 많으면 스레드가 금방 고갈된다. Tomcat 8.5부터는 BIO가 제거됐다. Tomcat 7 이하를 아직 쓰고 있다면 NIO로 바꾸는 게 맞다.

### NIO (Non-blocking I/O)

```xml
<Connector port="8080"
           protocol="org.apache.coyote.http11.Http11NioProtocol"
           maxThreads="200" />
```

Tomcat 8.5 이상에서 기본값이다. 하나의 스레드가 여러 연결을 처리할 수 있어서 동시 접속 처리 능력이 BIO보다 훨씬 낫다. 대부분의 환경에서 NIO를 쓰면 된다.

### NIO2

```xml
<Connector port="8080"
           protocol="org.apache.coyote.http11.Http11Nio2Protocol"
           maxThreads="200" />
```

Java NIO.2 (AIO) 기반이다. NIO와 성능 차이가 크지 않아서 실무에서 굳이 NIO2를 선택할 이유는 별로 없다.

### APR (Apache Portable Runtime)

```xml
<Connector port="8080"
           protocol="org.apache.coyote.http11.Http11AprProtocol"
           maxThreads="200" />
```

네이티브 라이브러리(libtcnative)를 사용한다. TLS 처리 성능이 가장 좋다. 단, OS에 APR 라이브러리를 별도로 설치해야 하고, JNI를 통해 네이티브 코드를 호출하기 때문에 네이티브 메모리 릭이 발생하면 디버깅이 까다롭다. SSL 처리가 많은 환경에서 고려할 만하지만, 앞단에 Nginx나 Apache httpd를 두고 TLS를 거기서 처리하면 APR을 쓸 필요가 줄어든다.

### Connector 주요 속성

| 속성 | 설명 | 기본값 |
|------|------|--------|
| `maxThreads` | 요청을 처리하는 최대 스레드 수 | 200 |
| `minSpareThreads` | 유휴 상태로 유지할 최소 스레드 수 | 10 |
| `acceptCount` | 모든 스레드가 사용 중일 때 대기열 크기 | 100 |
| `connectionTimeout` | 연결 후 요청이 없으면 끊는 시간(ms) | 60000 |
| `maxConnections` | 동시에 처리 가능한 최대 연결 수 | NIO: 10000 |
| `keepAliveTimeout` | keep-alive 연결 유지 시간(ms) | connectionTimeout 값 사용 |

`maxThreads`와 `acceptCount`의 관계를 이해해야 한다. 동시 요청이 `maxThreads`를 초과하면 `acceptCount` 크기의 대기열에 들어가고, 대기열마저 가득 차면 클라이언트는 connection refused를 받는다.

## context.xml 설정

context.xml은 웹 애플리케이션 단위의 설정을 정의한다. `conf/context.xml`에 넣으면 모든 애플리케이션에 적용되고, 각 애플리케이션의 `META-INF/context.xml`에 넣으면 해당 앱에만 적용된다.

```xml
<Context>
    <!-- 세션 쿠키 설정 -->
    <CookieProcessor sameSiteCookies="strict" />

    <!-- 리소스 캐시 크기 (기본 10MB, JSP가 많으면 늘려야 한다) -->
    <Resources cachingAllowed="true" cacheMaxSize="102400" />

    <!-- JNDI 데이터소스 (아래 섹션에서 상세 설명) -->
    <Resource name="jdbc/mydb"
              auth="Container"
              type="javax.sql.DataSource"
              ... />
</Context>
```

운영 중에 "Unable to add the resource" 경고가 로그에 찍히면 `cacheMaxSize`를 올려야 한다. 정적 파일이나 JSP가 많은 애플리케이션에서 자주 발생한다.

## JNDI 데이터소스 설정

애플리케이션 코드에 DB 접속 정보를 하드코딩하지 않고, Tomcat이 커넥션 풀을 관리하게 할 수 있다. context.xml에 DataSource를 정의하고, 애플리케이션에서 JNDI lookup으로 가져다 쓴다.

### context.xml 설정

```xml
<Context>
    <Resource name="jdbc/mydb"
              auth="Container"
              type="javax.sql.DataSource"
              factory="org.apache.tomcat.jdbc.pool.DataSourceFactory"
              driverClassName="com.mysql.cj.jdbc.Driver"
              url="jdbc:mysql://db-host:3306/mydb?useSSL=true&amp;serverTimezone=Asia/Seoul"
              username="app_user"
              password="secret123"
              maxActive="50"
              maxIdle="20"
              minIdle="5"
              maxWait="10000"
              testOnBorrow="true"
              validationQuery="SELECT 1"
              validationInterval="30000"
              timeBetweenEvictionRunsMillis="30000"
              minEvictableIdleTimeMillis="60000"
              removeAbandoned="true"
              removeAbandonedTimeout="60"
              logAbandoned="true" />
</Context>
```

JDBC 드라이버 jar 파일은 `$CATALINA_HOME/lib/`에 넣어야 한다. 애플리케이션의 `WEB-INF/lib/`에 넣으면 클래스로더 충돌이 생길 수 있다.

### web.xml에서 참조 선언

```xml
<resource-ref>
    <res-ref-name>jdbc/mydb</res-ref-name>
    <res-type>javax.sql.DataSource</res-type>
    <res-auth>Container</res-auth>
</resource-ref>
```

### Java 코드에서 사용

```java
Context initCtx = new InitialContext();
Context envCtx = (Context) initCtx.lookup("java:comp/env");
DataSource ds = (DataSource) envCtx.lookup("jdbc/mydb");

try (Connection conn = ds.getConnection()) {
    // DB 작업
}
```

주의사항:

- `testOnBorrow="true"`와 `validationQuery`를 반드시 설정한다. 이게 없으면 DB가 커넥션을 끊은 후에도 Tomcat이 죽은 커넥션을 반환해서 "Connection is closed" 에러가 터진다. MySQL의 `wait_timeout` 기본값이 8시간이라, 밤새 트래픽이 없으면 아침에 첫 요청이 실패하는 일이 생긴다.
- `removeAbandoned="true"`는 커넥션을 가져간 후 반환하지 않는 코드가 있을 때 강제 회수한다. `logAbandoned="true"`와 함께 쓰면 어디서 커넥션을 누수했는지 스택트레이스가 찍힌다.
- Spring Boot를 쓰면 HikariCP가 기본 커넥션 풀이라 JNDI를 쓸 일이 거의 없다. 독립 Tomcat에 WAR로 배포하는 환경에서 주로 사용한다.

## WAR 배포 방식

### 방법 1: webapps 디렉토리에 복사

가장 단순한 방법이다. WAR 파일을 `$CATALINA_HOME/webapps/`에 복사하면 Tomcat이 자동으로 압축을 풀고 배포한다.

```bash
cp myapp.war $CATALINA_HOME/webapps/

# ROOT.war로 복사하면 / 경로로 접근 가능
cp myapp.war $CATALINA_HOME/webapps/ROOT.war
```

`autoDeploy="true"`이면 Tomcat 재시작 없이 배포된다. 하지만 운영 환경에서 이 방식은 위험하다. 배포 중에 요청이 들어오면 불완전한 상태의 애플리케이션이 응답할 수 있다.

### 방법 2: server.xml에 Context 정의

```xml
<Host name="localhost" appBase="webapps"
      unpackWARs="true" autoDeploy="false">

    <Context path="" docBase="/opt/deploy/myapp.war"
             reloadable="false" />
</Host>
```

WAR 파일 경로를 명시적으로 지정한다. `autoDeploy="false"`와 함께 쓰면 의도하지 않은 배포를 막을 수 있다.

### 방법 3: 심볼릭 링크 활용

```bash
# 버전별 WAR 관리
/opt/deploy/myapp-v1.0.war
/opt/deploy/myapp-v1.1.war

# 심볼릭 링크로 현재 버전 지정
ln -sf /opt/deploy/myapp-v1.1.war /opt/deploy/myapp.war

# Tomcat 재시작
$CATALINA_HOME/bin/shutdown.sh && $CATALINA_HOME/bin/startup.sh
```

롤백할 때 심볼릭 링크만 이전 버전으로 변경하면 된다. 무중단 배포가 필요하면 이 방법만으로는 부족하고, 로드 밸런서와 함께 사용해야 한다.

### 배포 시 자주 겪는 문제

- work 디렉토리에 이전 JSP 컴파일 결과가 남아서 변경 사항이 반영 안 되는 경우가 있다. 배포할 때 `$CATALINA_HOME/work/` 하위를 삭제하고 재시작하면 해결된다.
- WAR 파일 이름이 컨텍스트 경로가 된다. `myapp.war`는 `/myapp`으로 접근한다. `/`로 접근하게 하려면 `ROOT.war`로 이름을 바꿔야 한다.
- 배포 후 "ClassNotFoundException"이 발생하면 대부분 라이브러리 충돌이다. Tomcat의 lib 디렉토리에 있는 jar와 애플리케이션의 WEB-INF/lib에 있는 jar가 겹치는지 확인한다.

## 스레드풀 튜닝

Tomcat의 요청 처리 성능은 스레드풀 설정에 크게 좌우된다. 기본값으로 운영하다가 트래픽이 조금만 늘면 문제가 생긴다.

### Executor로 스레드풀 분리

Connector마다 별도 스레드풀을 쓰는 대신, Executor를 정의해서 공유할 수 있다.

```xml
<Service name="Catalina">

    <Executor name="tomcatThreadPool"
              namePrefix="catalina-exec-"
              maxThreads="300"
              minSpareThreads="25"
              maxIdleTime="60000" />

    <Connector port="8080"
               executor="tomcatThreadPool"
               protocol="org.apache.coyote.http11.Http11NioProtocol"
               connectionTimeout="20000" />
</Service>
```

### 적정 스레드 수 산정

공식처럼 딱 떨어지는 답은 없다. 하지만 기본적인 계산 방법이 있다.

```
필요 스레드 수 = 초당 요청 수 × 평균 응답 시간(초)
```

초당 요청이 100개이고 평균 응답 시간이 0.5초면, 동시에 50개 스레드가 필요하다. 여기에 여유분을 더해서 설정한다. DB 호출이 느려지거나 외부 API 타임아웃이 길어지면 스레드가 밀리기 때문에, 피크 타임 기준으로 2~3배 여유를 잡는 게 현실적이다.

스레드를 무작정 늘리면 안 된다. 스레드가 많아지면 컨텍스트 스위칭 비용이 증가하고, 각 스레드가 스택 메모리를 잡아먹는다(기본 1MB). 300개면 스택 메모리만 300MB다.

### 모니터링

스레드풀 상태는 JMX로 확인할 수 있다.

```bash
# jconsole 또는 VisualVM에서 확인
# MBean: Catalina:type=ThreadPool,name="http-nio-8080"

# 또는 curl로 Manager API 호출
curl -u admin:password http://localhost:8080/manager/status?XML=true
```

`currentThreadsBusy`가 `maxThreads`에 근접하면 스레드 고갈 직전이다. 이 상태가 지속되면 스레드 수를 늘리거나, 애플리케이션의 응답 시간을 줄이는 게 근본적인 해결 방법이다.

## JVM 메모리 설정

Tomcat은 Java 프로세스이므로 JVM 메모리 설정이 중요하다. `$CATALINA_HOME/bin/setenv.sh` 파일을 만들어서 설정한다. catalina.sh를 직접 수정하면 업그레이드할 때 덮어씌워지기 때문에 setenv.sh를 사용한다.

```bash
#!/bin/bash
# $CATALINA_HOME/bin/setenv.sh

CATALINA_OPTS="
  -Xms2g
  -Xmx2g
  -XX:MetaspaceSize=256m
  -XX:MaxMetaspaceSize=512m
  -XX:+UseG1GC
  -XX:MaxGCPauseMillis=200
  -Xlog:gc*:file=$CATALINA_HOME/logs/gc.log:time,uptime:filecount=5,filesize=10m
  -XX:+HeapDumpOnOutOfMemoryError
  -XX:HeapDumpPath=$CATALINA_HOME/logs/
  -Djava.net.preferIPv4Stack=true
"

JAVA_OPTS="
  -Dfile.encoding=UTF-8
  -Duser.timezone=Asia/Seoul
"
```

핵심 포인트:

- **Xms와 Xmx를 같은 값으로 설정한다.** 다르게 설정하면 힙 확장/축소가 반복되면서 GC 부담이 늘어난다. 운영 환경에서는 필요한 메모리를 처음부터 확보하는 게 안정적이다.
- **CATALINA_OPTS vs JAVA_OPTS:** `CATALINA_OPTS`는 Tomcat 프로세스에만 적용되고, `JAVA_OPTS`는 shutdown 명령 등 다른 Java 프로세스에도 적용된다. 메모리 설정은 `CATALINA_OPTS`에 넣어야 shutdown 프로세스가 불필요하게 큰 메모리를 잡지 않는다.
- **MetaspaceSize:** Java 8+에서 PermGen 대신 Metaspace를 사용한다. 클래스를 많이 로드하는 애플리케이션(Spring Framework 등)에서는 기본값이 부족할 수 있다. 재배포를 반복하면 Metaspace가 차면서 OutOfMemoryError가 발생하는 경우가 있는데, 이는 클래스로더 누수 문제다.
- **HeapDumpOnOutOfMemoryError:** OOM이 발생하면 자동으로 힙 덤프를 생성한다. 이게 없으면 OOM 원인을 분석할 방법이 없다. 디스크 공간이 충분한지 확인해야 한다. 2GB 힙이면 덤프 파일도 2GB 이상 나올 수 있다.

### 메모리 산정 기준

실제 필요한 힙 메모리는 이렇게 추정한다:

```
전체 메모리 = 힙(Xmx) + Metaspace + 스레드 스택(스레드 수 × 1MB) + NIO 버퍼 + 네이티브 메모리
```

4GB RAM 서버에서 Tomcat을 돌린다면, 힙을 2GB로 잡고 나머지를 OS와 다른 프로세스에 남겨두는 게 안전하다. 힙을 너무 크게 잡으면 GC pause가 길어지고, OS의 파일 캐시에 쓸 메모리가 줄어든다.

## 세션 클러스터링

Tomcat 여러 대를 운영할 때 세션을 공유해야 하는 경우가 있다. Tomcat은 자체적으로 세션 클러스터링을 지원한다.

### DeltaManager (All-to-All 복제)

모든 노드에 세션을 복제한다. 노드 수가 적을 때(4대 이하) 적합하다.

```xml
<Cluster className="org.apache.catalina.ha.tcp.SimpleTcpCluster"
         channelSendOptions="8">

    <Manager className="org.apache.catalina.ha.session.DeltaManager"
             expireSessionsOnShutdown="false"
             notifyListenersOnReplication="true" />

    <Channel className="org.apache.catalina.tribes.group.GroupChannel">
        <Membership className="org.apache.catalina.tribes.membership.McastService"
                    address="228.0.0.4"
                    port="45564"
                    frequency="500"
                    dropTime="3000" />
        <Receiver className="org.apache.catalina.tribes.transport.nio.NioReceiver"
                  address="auto"
                  port="4000"
                  autoBind="100"
                  selectorTimeout="5000"
                  maxThreads="6" />
        <Sender className="org.apache.catalina.tribes.transport.ReplicationTransmitter">
            <Transport className="org.apache.catalina.tribes.transport.nio.PooledParallelSender" />
        </Sender>
        <Interceptor className="org.apache.catalina.tribes.group.interceptors.TcpFailureDetector" />
        <Interceptor className="org.apache.catalina.tribes.group.interceptors.MessageDispatchInterceptor" />
    </Channel>

    <Valve className="org.apache.catalina.ha.tcp.ReplicationValve"
           filter="" />
    <Valve className="org.apache.catalina.ha.session.JvmRouteBinderValve" />

    <ClusterListener className="org.apache.catalina.ha.session.ClusterSessionListener" />
</Cluster>
```

애플리케이션의 web.xml에 `<distributable/>` 태그를 추가해야 동작한다. 세션에 넣는 객체는 모두 `Serializable`을 구현해야 한다. 그렇지 않으면 복제가 실패하면서 로그에 NotSerializableException이 쌓인다.

### BackupManager (Primary-Secondary 복제)

세션을 하나의 백업 노드에만 복제한다. 노드가 많을 때 DeltaManager보다 네트워크 부하가 적다.

```xml
<Manager className="org.apache.catalina.ha.session.BackupManager"
         expireSessionsOnShutdown="false"
         notifyListenersOnReplication="true"
         mapSendOptions="6" />
```

### 현실적인 선택

Tomcat 자체 클러스터링은 설정이 복잡하고, 멀티캐스트가 안 되는 클라우드 환경(AWS, GCP)에서는 사용하기 어렵다. 실무에서는 아래 방법을 더 많이 쓴다.

- **Sticky Session:** 로드 밸런서에서 같은 사용자를 같은 서버로 보낸다. 해당 서버가 죽으면 세션이 날아가는 단점이 있다.
- **Redis/Memcached에 세션 저장:** Tomcat의 세션 매니저를 교체해서 외부 저장소에 세션을 저장한다. `redisson-tomcat` 같은 라이브러리를 사용한다.
- **JWT 기반 Stateless:** 서버에 세션을 저장하지 않고, 토큰에 정보를 담는다. 세션 클러스터링 자체가 필요 없어진다.

## 앞단에 Nginx/Apache httpd 두는 구성

Tomcat 앞에 웹 서버를 두는 이유는 몇 가지가 있다.

- Tomcat은 정적 파일 처리 성능이 웹 서버보다 떨어진다
- TLS 처리를 웹 서버에 맡기면 Tomcat의 부하가 줄어든다
- 여러 Tomcat 인스턴스에 로드 밸런싱을 할 수 있다
- Tomcat을 외부에 직접 노출하지 않아서 보안상 낫다

### Nginx + Tomcat (Reverse Proxy)

```nginx
upstream tomcat_backend {
    server 127.0.0.1:8080;
    # 여러 대일 경우
    # server 10.0.0.2:8080;
    # server 10.0.0.3:8080;
}

server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate     /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # 정적 파일은 Nginx가 직접 처리
    location /static/ {
        alias /var/www/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 나머지는 Tomcat으로 프록시
    location / {
        proxy_pass http://tomcat_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 5s;
        proxy_read_timeout 60s;
        proxy_send_timeout 30s;
    }
}
```

### Apache httpd + Tomcat (mod_proxy)

```apache
<VirtualHost *:443>
    ServerName example.com

    SSLEngine on
    SSLCertificateFile    /etc/ssl/certs/example.com.crt
    SSLCertificateKeyFile /etc/ssl/private/example.com.key

    ProxyPreserveHost On
    ProxyPass        / http://127.0.0.1:8080/
    ProxyPassReverse / http://127.0.0.1:8080/

    RequestHeader set X-Forwarded-Proto "https"
</VirtualHost>
```

### Apache httpd + Tomcat (mod_jk / AJP)

AJP는 바이너리 프로토콜이라 HTTP보다 오버헤드가 적다. 하지만 2020년에 발견된 Ghostcat 취약점(CVE-2020-1938) 이후로 AJP 사용 시 보안 설정에 신경 써야 한다.

```apache
# workers.properties
worker.list=tomcat1
worker.tomcat1.type=ajp13
worker.tomcat1.host=127.0.0.1
worker.tomcat1.port=8009
worker.tomcat1.secret=my-ajp-secret
```

Tomcat server.xml에서 AJP Connector의 `secretRequired="true"`와 `secret` 속성을 반드시 설정한다. 그렇지 않으면 외부에서 AJP 포트로 직접 접근해서 서버 파일을 읽을 수 있다.

### 프록시 구성 시 주의사항

Tomcat 앞에 프록시를 두면 클라이언트 IP가 프록시 서버 IP로 찍힌다. Tomcat에서 실제 클라이언트 IP를 알려면 `RemoteIpValve`를 설정해야 한다.

```xml
<!-- server.xml의 Host 안에 추가 -->
<Valve className="org.apache.catalina.valves.RemoteIpValve"
       remoteIpHeader="X-Forwarded-For"
       protocolHeader="X-Forwarded-Proto"
       internalProxies="127\.0\.0\.1|10\.0\.0\.\d{1,3}" />
```

이 설정이 없으면 `request.getRemoteAddr()`가 항상 127.0.0.1을 반환하고, 접근 로그에도 프록시 IP만 찍힌다. IP 기반 접근 제어나 감사 로그를 남기는 경우 문제가 된다.

타임아웃 설정도 맞춰야 한다. Nginx의 `proxy_read_timeout`이 60초인데 Tomcat의 요청 처리가 90초 걸리면, Nginx가 먼저 연결을 끊으면서 사용자는 502를 받는다. 프록시 서버의 타임아웃이 Tomcat보다 길어야 한다.

## 보안 설정

운영 환경에서 반드시 확인해야 할 보안 설정들이다.

### 불필요한 기본 애플리케이션 제거

```bash
# 설치 직후 webapps에 있는 기본 앱들
rm -rf $CATALINA_HOME/webapps/docs
rm -rf $CATALINA_HOME/webapps/examples
rm -rf $CATALINA_HOME/webapps/manager
rm -rf $CATALINA_HOME/webapps/host-manager
rm -rf $CATALINA_HOME/webapps/ROOT
```

manager와 host-manager는 관리용 웹 UI인데, 약한 비밀번호로 노출되면 WAR 파일을 업로드해서 원격 코드 실행이 가능하다. 쓸 일이 없으면 삭제한다.

### 서버 정보 숨기기

```xml
<!-- server.xml Connector에 추가 -->
<Connector port="8080" ... server="WebServer" />
```

```xml
<!-- conf/web.xml의 DefaultServlet에 추가 -->
<init-param>
    <param-name>showServerInfo</param-name>
    <param-value>false</param-value>
</init-param>
```

에러 페이지에 Tomcat 버전이 노출되면 공격자가 알려진 취약점을 바로 찾을 수 있다.

### 커스텀 에러 페이지

```xml
<!-- conf/web.xml에 추가 -->
<error-page>
    <error-code>404</error-code>
    <location>/error/404.html</location>
</error-page>
<error-page>
    <error-code>500</error-code>
    <location>/error/500.html</location>
</error-page>
<error-page>
    <exception-type>java.lang.Throwable</exception-type>
    <location>/error/500.html</location>
</error-page>
```

기본 에러 페이지는 스택트레이스를 그대로 보여준다. 클래스 이름, 파일 경로 같은 내부 정보가 노출된다.

## 트러블슈팅

### catalina.out이 너무 커지는 문제

Tomcat은 기본적으로 stdout/stderr를 `catalina.out`에 append한다. 로그 로테이션 설정이 없으면 파일이 끝없이 커진다. 디스크가 꽉 차서 Tomcat이 멈추는 사고가 실제로 일어난다.

```bash
# logrotate 설정
# /etc/logrotate.d/tomcat
/opt/tomcat/logs/catalina.out {
    copytruncate
    daily
    rotate 7
    compress
    missingok
    size 100M
}
```

`copytruncate`를 써야 Tomcat을 재시작하지 않고 로그를 로테이션할 수 있다.

### Too many open files

동시 접속이 많아지면 파일 디스크립터 제한에 걸린다. Tomcat 프로세스의 ulimit을 확인하고 올려야 한다.

```bash
# 현재 Tomcat 프로세스의 제한 확인
cat /proc/$(pgrep -f catalina)/limits | grep "Max open files"

# /etc/security/limits.conf 수정
tomcat soft nofile 65536
tomcat hard nofile 65536

# systemd 서비스 파일에서 설정
[Service]
LimitNOFILE=65536
```

### OutOfMemoryError 대응

OOM이 발생하면 힙 덤프를 분석한다.

```bash
# 힙 덤프 분석 (Eclipse MAT 사용)
# 1. HeapDumpOnOutOfMemoryError로 자동 생성된 덤프 파일 확인
ls -la $CATALINA_HOME/logs/*.hprof

# 2. 실행 중인 Tomcat에서 수동으로 힙 덤프 생성
jmap -dump:format=b,file=heap.hprof $(pgrep -f catalina)
```

자주 발생하는 OOM 원인:

- 세션에 큰 객체를 넣고 세션 타임아웃이 긴 경우
- 재배포를 반복하면서 클래스로더가 정리되지 않는 경우 (Metaspace OOM)
- 대량 데이터를 한 번에 메모리에 올리는 쿼리
