---
title: Amazon MQ 운영 노트
tags: [aws, amazon-mq, rabbitmq, activemq, messaging, AMQP, jms]
updated: 2026-07-03
---

# Amazon MQ 운영 노트

Amazon MQ는 RabbitMQ와 ActiveMQ를 관리형으로 돌려주는 서비스다. 브로커 소프트웨어 자체는 오픈소스 그대로고, AWS가 EC2 인스턴스 프로비저닝, 패치, 백업, 장애 조치를 대신 해준다. SQS/SNS처럼 AWS 자체 프로토콜을 쓰는 게 아니라 AMQP 0-9-1, MQTT, STOMP, OpenWire, JMS 같은 표준 프로토콜을 그대로 지원한다. 이게 Amazon MQ를 쓰는 거의 유일한 이유다.

기존에 자체 호스팅 RabbitMQ나 ActiveMQ를 돌리던 애플리케이션이 있고, 코드에 AMQP나 JMS 클라이언트가 이미 박혀 있다면 Amazon MQ로 넘어가는 게 맞다. 반대로 신규 프로젝트를 처음부터 짜는 거라면 대부분 SQS/SNS가 낫다.

## SQS/SNS와 Amazon MQ 중 뭘 쓸까

이 판단을 잘못하면 나중에 고생한다. 기준은 하나다. 표준 메시징 프로토콜을 유지해야 하느냐.

기존 애플리케이션이 RabbitMQ의 AMQP나 IBM MQ, ActiveMQ의 JMS 위에서 돌고 있고, 이걸 최소한의 코드 수정으로 클라우드에 올려야 한다면 Amazon MQ다. 스프링 애플리케이션에서 `spring-boot-starter-amqp`로 짠 코드, JMS `MessageListener`로 짠 코드를 그대로 살릴 수 있다. 프로토콜 레벨에서 호환되니 커넥션 문자열만 바꾸면 대부분 돌아간다.

반대로 다음 경우엔 SQS/SNS가 낫다.

- 애플리케이션을 새로 짜거나 어차피 메시징 레이어를 다시 쓸 거다
- 브로커 인스턴스를 직접 관리하고 싶지 않다 (SQS는 완전 서버리스라 인스턴스 개념 자체가 없다)
- 트래픽이 크게 출렁여서 자동으로 늘어나고 줄어드는 처리량이 필요하다
- 초당 수만 건 이상을 안정적으로 흘려야 한다

Amazon MQ는 결국 EC2 인스턴스 위에서 도는 브로커라 처리량에 상한이 있다. 인스턴스 타입에 묶여 있고, 그 이상 필요하면 스케일 업하거나 클러스터를 늘려야 한다. SQS는 사실상 무한히 늘어난다. 대신 SQS는 AMQP도 JMS도 아니고, 메시지 라우팅이 RabbitMQ의 익스체인지처럼 정교하지 않다. 라우팅 키 기반 토픽 익스체인지, 헤더 익스체인지 같은 걸 쓰고 있었다면 SQS로 그대로 옮기기 어렵다.

실무에서 자주 겪는 상황은 이렇다. 온프레미스나 자체 EC2에서 RabbitMQ를 돌리던 팀이 운영 부담을 줄이려고 클라우드로 넘어온다. 이때 "이왕 옮기는 김에 SQS로 다 바꾸자"는 얘기가 나오는데, 익스체인지/큐 바인딩 구조가 복잡할수록 재작성 비용이 크다. 일단 Amazon MQ로 최소 변경 마이그레이션을 하고, 나중에 컴포넌트 단위로 천천히 SQS로 넘기는 게 현실적이다.

## 자체 호스팅 RabbitMQ에서 넘어올 때 겪는 문제

커넥션 문자열만 바꾸면 끝날 것 같지만 실제로는 걸리는 게 몇 개 있다.

### 버전 차이

Amazon MQ가 지원하는 RabbitMQ 버전은 제한적이다. 자체 호스팅으로 최신 버전을 쓰고 있었다면, Amazon MQ가 그 버전을 아직 지원하지 않는 경우가 있다. 마이그레이션 전에 대상 버전을 먼저 확인해야 한다. 버전이 다르면 플러그인 호환성이나 정책 동작이 미묘하게 달라질 수 있다.

그리고 Amazon MQ의 RabbitMQ는 관리형이라 임의 플러그인을 켤 수 없다. `rabbitmq_delayed_message_exchange` 같은 커뮤니티 플러그인에 의존하고 있었다면 그대로 못 옮긴다. 지연 메시지가 필요하면 애플리케이션 레벨에서 TTL + Dead Letter Exchange 조합으로 다시 구현하거나, 아예 다른 방식을 찾아야 한다.

### 관리 API 접근 제한

자체 호스팅에서는 `rabbitmqctl`로 노드에 직접 붙어서 큐를 만들고, 정책을 걸고, 유저를 관리했다. Amazon MQ에서는 브로커 호스트에 SSH로 못 들어간다. 관리 UI(RabbitMQ Management Console)와 HTTP API는 열려 있지만, `rabbitmqctl` 같은 노드 직접 조작은 안 된다. 배포 스크립트나 운영 자동화가 `rabbitmqctl`에 의존하고 있었다면 전부 HTTP 관리 API 호출로 다시 짜야 한다.

### 사용자/권한 관리 방식

자체 호스팅에서 rabbitmq 내부 유저를 CLI로 관리했다면, Amazon MQ에서는 브로커 생성 시 지정한 관리자 계정으로 시작하고, 추가 유저는 관리 콘솔이나 API로 만든다. LDAP 연동도 지원하지만 설정 방식이 다르다.

### 마이그레이션 순서

메시지를 무손실로 옮기려면 보통 이렇게 한다. 새 Amazon MQ 브로커를 띄우고, 컨슈머를 먼저 양쪽 브로커에 모두 붙인다. 그다음 프로듀서를 새 브로커로 전환한다. 기존 브로커의 큐가 다 비워지면 기존 브로커의 컨슈머를 뗀다. 이렇게 하면 인플라이트 메시지를 잃지 않는다. 프로듀서와 컨슈머를 동시에 전환하면 전환 시점에 어느 한쪽 브로커에 남은 메시지가 처리되지 않고 붕 뜬다.

## 배포 방식: 단일 인스턴스 vs 클러스터

배포 모드 선택은 가용성과 비용을 직접 결정한다.

### 단일 인스턴스 (single-instance)

브로커 하나만 뜬다. 인스턴스가 죽으면 AWS가 같은 AZ 안에서 새 인스턴스를 다시 띄우는데, 이 과정에서 몇 분간 브로커가 통째로 내려간다. 개발/스테이징 환경이나, 짧은 다운타임을 감내할 수 있는 워크로드에만 쓴다. 프로덕션에서 단일 인스턴스로 돌리다가 인스턴스 교체 중에 서비스가 멈춰서 장애가 나는 경우를 봤다.

### RabbitMQ 클러스터 배포 (cluster deployment)

RabbitMQ는 3개 노드로 구성된 클러스터로 배포한다. 3개 노드가 서로 다른 AZ에 분산되고, 큐가 미러링된다. 노드 하나가 죽어도 나머지 둘이 살아 있어서 브로커가 계속 돈다. 프로덕션 RabbitMQ는 사실상 이 모드가 기본이다.

주의할 점은 클러스터라고 해서 처리량이 3배가 되는 게 아니라는 거다. 큐가 미러링되기 때문에 쓰기는 오히려 노드 간 복제 오버헤드가 붙는다. 클러스터는 처리량이 아니라 가용성을 위한 거다. 처리량을 늘리려면 인스턴스 타입을 키우거나 큐를 여러 브로커에 나눠야 한다.

### ActiveMQ의 active/standby

ActiveMQ는 RabbitMQ와 구조가 다르다. active/standby 방식으로, 두 브로커가 뜨지만 한 번에 하나만 활성 상태다. 액티브 브로커가 죽으면 스탠바이가 승격되면서 페일오버가 일어난다. 이 페일오버에도 수십 초에서 분 단위의 시간이 걸린다. 그동안 커넥션은 끊긴다. ActiveMQ 클라이언트에 페일오버 트랜스포트(`failover:(...)`)를 설정해두면 자동으로 재연결을 시도한다.

## 브로커 재시작과 커넥션 끊김

이게 실무에서 제일 자주 데는 부분이다. Amazon MQ는 관리형이라 AWS가 유지보수 윈도우에 브로커를 패치하고 재시작한다. 클러스터 배포라도 노드를 하나씩 롤링으로 재시작하는데, 이때 그 노드에 붙어 있던 커넥션은 끊긴다.

핵심은 이거다. 관리형이라도 커넥션 끊김은 반드시 일어난다. 애플리케이션이 커넥션이 끊겨도 스스로 다시 붙을 수 있어야 한다. 이걸 준비 안 하면 유지보수 윈도우마다 메시지 처리가 멈춘다.

유지보수 윈도우는 브로커 생성 시 지정할 수 있다. 트래픽이 적은 시간대로 잡아둔다. 하지만 지정한다고 커넥션이 안 끊기는 게 아니라, 언제 끊길지를 정하는 것뿐이다.

### 스프링 AMQP에서 재연결

스프링의 `CachingConnectionFactory`는 기본적으로 커넥션이 끊기면 다음 요청 때 다시 연결을 시도한다. 하지만 컨슈머 쪽은 조금 더 신경 써야 한다. `SimpleMessageListenerContainer`나 `DirectMessageListenerContainer`에 복구 인터벌을 명시적으로 설정해두는 게 좋다.

```java
@Configuration
public class RabbitConfig {

    @Bean
    public CachingConnectionFactory connectionFactory() {
        CachingConnectionFactory factory = new CachingConnectionFactory();
        factory.setUri("amqps://b-xxxx.mq.ap-northeast-2.amazonaws.com:5671");
        factory.setUsername("admin");
        factory.setPassword("...");
        // 커넥션 캐싱 모드. CONNECTION 모드면 여러 커넥션을 캐싱한다
        factory.setCacheMode(CachingConnectionFactory.CacheMode.CHANNEL);
        return factory;
    }

    @Bean
    public SimpleRabbitListenerContainerFactory rabbitListenerContainerFactory(
            CachingConnectionFactory connectionFactory) {
        SimpleRabbitListenerContainerFactory factory =
                new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        // 커넥션이 끊겼을 때 재시도 간격. 기본 5초
        factory.setRecoveryInterval(5000L);
        // 컨슈머가 죽었을 때 컨테이너를 살려두고 재시도하게 함
        factory.setMissingQueuesFatal(false);
        return factory;
    }
}
```

여기서 `amqps`와 포트 `5671`을 쓴 것에 주의한다. Amazon MQ의 RabbitMQ는 TLS를 강제한다. 평문 AMQP(`amqp`, 포트 5672)로는 못 붙는다. 자체 호스팅에서 평문으로 쓰다가 넘어오면 이 부분에서 커넥션이 안 되는데, 로그만 봐서는 원인을 찾기 어렵다.

### 커넥션 끊김을 애플리케이션이 어떻게 감지하나

RabbitMQ Java 클라이언트에는 자동 복구 기능이 있다. `ConnectionFactory.setAutomaticRecoveryEnabled(true)`를 켜두면 (최신 클라이언트는 기본 활성), 클라이언트가 커넥션이 끊긴 걸 감지하고 백그라운드에서 다시 붙는다. 채널, 컨슈머, 큐 선언까지 자동으로 복구한다.

하지만 자동 복구가 진행되는 동안 발행한 메시지는 유실될 수 있다. 커넥션이 복구되기 전에 `basicPublish`를 호출하면 예외가 난다. 그래서 프로듀서 쪽은 발행 실패를 잡아서 재시도하는 로직이 따로 있어야 한다.

## 프로듀서 재연결과 발행 확인

컨슈머는 자동 복구로 어느 정도 커버되지만, 프로듀서는 메시지 유실 위험이 있어서 더 조심해야 한다.

발행할 때 두 가지를 챙긴다. 첫째, Publisher Confirms를 켠다. 브로커가 메시지를 받았다고 확인(ack)을 보내줄 때까지 발행 성공으로 치지 않는다. 둘째, 발행이 실패하거나 nack가 오면 재시도한다.

```java
@Component
public class ReliableProducer {

    private final RabbitTemplate rabbitTemplate;

    public ReliableProducer(RabbitTemplate rabbitTemplate) {
        this.rabbitTemplate = rabbitTemplate;
        // Publisher Confirm 콜백. 브로커가 메시지를 받았는지 확인한다
        this.rabbitTemplate.setConfirmCallback((correlation, ack, cause) -> {
            if (!ack) {
                // nack가 왔다. 재발행 대상으로 넘긴다
                log.warn("메시지 발행 실패, cause={}", cause);
                requeueForRetry(correlation);
            }
        });
        // 라우팅 실패(어떤 큐에도 안 들어감) 시 콜백
        this.rabbitTemplate.setReturnsCallback(returned -> {
            log.warn("라우팅 실패: {}", returned.getMessage());
        });
    }

    public void send(String exchange, String routingKey, Object payload) {
        int attempt = 0;
        while (attempt < 3) {
            try {
                rabbitTemplate.convertAndSend(exchange, routingKey, payload);
                return;
            } catch (AmqpException e) {
                // 커넥션이 복구되는 중이면 여기로 떨어진다
                attempt++;
                log.warn("발행 재시도 {}/3", attempt);
                sleep(1000L * attempt);
            }
        }
        // 3번 실패하면 별도 저장소에 넣어두고 나중에 재처리
        deadLetterStore.save(exchange, routingKey, payload);
    }
}
```

`application.yml`에 Publisher Confirm을 켜는 설정도 필요하다.

```yaml
spring:
  rabbitmq:
    publisher-confirm-type: correlated
    publisher-returns: true
    template:
      mandatory: true   # 라우팅 실패 시 메시지를 버리지 않고 returns 콜백으로 돌려받음
```

`mandatory: true`를 빼먹으면 라우팅되지 못한 메시지가 조용히 사라진다. 익스체인지에는 도달했지만 바인딩된 큐가 없으면 브로커가 그냥 버린다. 이 설정이 있어야 returns 콜백으로 돌아온다.

주의할 건, Publisher Confirm은 성능을 깎는다. 매 발행마다 브로커 ack를 기다리므로 처리량이 떨어진다. 대량 발행이라면 비동기 confirm이나 배치 confirm을 쓰는 게 낫다. 모든 메시지에 동기 confirm을 걸면 초당 처리량이 크게 줄어드는 걸 실측으로 확인한 적이 있다.

## ENI 기반 프라이빗 접속

Amazon MQ 브로커를 만들면 지정한 VPC의 서브넷에 ENI(Elastic Network Interface)가 생긴다. 브로커는 이 ENI를 통해 프라이빗 IP로 접근한다. 퍼블릭 접근을 끄면(권장) 브로커는 VPC 내부에서만 접근 가능하다.

여기서 몇 가지 실수가 나온다.

보안 그룹을 잘못 잡으면 애플리케이션이 브로커에 못 붙는다. 브로커 ENI에 붙은 보안 그룹의 인바운드에 RabbitMQ면 5671(AMQPS)과 443(관리 콘솔/API), ActiveMQ면 프로토콜에 맞는 포트를 열어야 한다. 애플리케이션이 도는 서브넷/보안 그룹에서 오는 트래픽을 허용해야 한다. 이걸 안 열어두고 커넥션 타임아웃만 계속 나서 원인 찾느라 시간을 버리는 경우가 흔하다.

클러스터 배포는 AZ마다 ENI가 생긴다. 그래서 지정하는 서브넷도 여러 AZ에 걸쳐 있어야 한다. 단일 AZ 서브넷만 지정하면 클러스터 배포를 못 만든다.

온프레미스에서 접근해야 하면 VPN이나 Direct Connect로 VPC에 붙은 다음, 프라이빗 IP로 접근한다. 브로커 엔드포인트는 DNS 이름으로 나오는데, 이 DNS가 프라이빗 IP로 해석되려면 VPC의 DNS를 탈 수 있어야 한다. 온프레미스에서 이 DNS를 못 풀어서 접속이 안 되는 경우가 있다.

## CloudWatch로 큐 적체 모니터링

브로커가 살아 있어도 큐에 메시지가 쌓이면 문제다. 컨슈머가 발행 속도를 못 따라가고 있다는 신호다. Amazon MQ는 CloudWatch로 메트릭을 보낸다.

RabbitMQ에서 봐야 할 주요 메트릭.

- `MessageCount`: 큐에 쌓인 메시지 수. 이게 계속 늘면 컨슈머가 밀리고 있는 거다
- `MessageReadyCount`: 컨슈머에게 전달될 준비가 된 메시지 수
- `MessageUnacknowledgedCount`: 컨슈머가 받았지만 아직 ack하지 않은 메시지 수. 이게 높으면 컨슈머가 처리 중에 멈춰 있거나 처리가 느린 거다
- `ConsumerCount`: 큐에 붙은 컨슈머 수. 0으로 떨어지면 컨슈머가 다 죽었다는 뜻이라 즉시 알람을 걸어야 한다
- `SystemCpuUtilization`, `RabbitMQMemUsed`: 브로커 인스턴스 자원. 메모리가 임계치에 가까우면 RabbitMQ가 발행을 막는다(memory alarm)

가장 중요한 알람은 두 개다. `MessageCount`가 일정 임계치를 넘으면(적체 발생), `ConsumerCount`가 0이면(컨슈머 다운). 이 둘만 잡아도 큐 관련 장애의 대부분을 조기에 잡는다.

RabbitMQ 메모리 알람은 특히 주의한다. 메시지가 쌓여서 브로커 메모리가 워터마크를 넘으면 RabbitMQ가 프로듀서의 발행을 블록한다. 이때 프로듀서 쪽에서 `basicPublish`가 멈추거나 타임아웃이 나기 시작하는데, 브로커가 죽은 게 아니라 일부러 막고 있는 상태라 원인을 찾기 헷갈린다. `RabbitMQMemUsed`가 급증하는 그래프를 같이 봐야 이게 메모리 백프레셔라는 걸 안다.

```
CloudWatch 알람 예시
- MessageCount > 10000 (5분 지속)     → 적체 경고
- ConsumerCount < 1                    → 컨슈머 다운, 즉시 호출
- RabbitMQMemUsed > 임계 (2분 지속)    → 메모리 백프레셔 임박
- SystemCpuUtilization > 80% (5분)     → 사이징 부족 신호
```

## 인스턴스 사이징 실수

브로커 인스턴스 타입을 잘못 잡으면 두 방향으로 문제가 난다.

### 너무 작게 잡은 경우

`mq.t3.micro` 같은 버스터블 인스턴스로 프로덕션을 돌리는 실수를 많이 본다. t3 계열은 CPU 크레딧으로 도는데, 평소엔 괜찮다가 트래픽이 몰리면 크레딧이 바닥나고 CPU가 스로틀된다. 이 순간 브로커 응답이 느려지고 큐가 밀린다. t3는 개발/테스트용이다. 프로덕션은 `mq.m5` 같은 고정 성능 인스턴스를 쓴다.

메모리도 중요하다. RabbitMQ는 메시지를 메모리에 들고 있다가 워터마크를 넘으면 디스크로 페이징하거나 발행을 막는다. 작은 인스턴스는 메모리가 적어서, 컨슈머가 잠깐 밀리기만 해도 금방 메모리 알람에 걸린다. 순간 트래픽 스파이크에 큐가 얼마나 쌓일 수 있는지를 계산해서 메모리를 잡아야 한다.

### 너무 크게 잡은 경우

반대로 트래픽 대비 지나치게 큰 인스턴스를 잡아두면 돈만 나간다. Amazon MQ는 인스턴스가 떠 있는 시간만큼 계속 과금된다. SQS처럼 요청 건당 과금이 아니라, 브로커가 24시간 떠 있으면 트래픽이 0이어도 인스턴스 요금이 그대로 나간다. 클러스터 배포면 노드 3개분 요금이다. 트래픽이 적은데 클러스터 m5.large를 3개 띄워두고 매달 요금 보고 놀라는 경우가 있다.

### 사이징의 현실적인 접근

처음부터 완벽한 사이즈를 못 맞춘다. 트래픽 예측이 어긋나기 때문이다. 그래서 이렇게 한다. 우선 예상 피크 트래픽에 여유를 조금 두고 시작한 다음, CloudWatch로 CPU, 메모리, 큐 길이를 한동안 관찰한다. CPU가 늘 낮고 큐가 안 쌓이면 한 단계 낮춘다. 반대로 피크 시간에 CPU가 80%를 치거나 메모리 알람이 뜨면 올린다.

인스턴스 타입 변경은 브로커 재시작을 동반한다. 즉 커넥션이 끊긴다. 그래서 사이즈 조정도 유지보수 윈도우나 트래픽 적은 시간에 하고, 애플리케이션 재연결 로직이 제대로 도는지 먼저 확인한 다음 진행한다. 앞에서 재연결을 강조한 이유가 여기서도 나온다. 재연결이 안 되면 사이즈 하나 바꾸는 것도 장애가 된다.

## 정리하며 챙길 것

Amazon MQ는 표준 프로토콜을 유지해야 할 때 쓰는 서비스다. 신규 프로젝트라면 SQS/SNS를 먼저 검토한다. 관리형이라도 브로커 재시작과 커넥션 끊김은 반드시 일어나므로, 프로듀서/컨슈머 양쪽에 재연결과 발행 확인 로직을 넣어둔다. 배포 모드는 프로덕션이면 클러스터(RabbitMQ)나 active/standby(ActiveMQ)로 가고, 인스턴스는 버스터블 대신 고정 성능으로 잡되 CloudWatch를 보면서 조정한다. 큐 적체와 컨슈머 다운 알람은 초기에 걸어둔다.
