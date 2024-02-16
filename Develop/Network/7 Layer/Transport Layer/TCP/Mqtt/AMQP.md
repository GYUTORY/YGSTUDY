
# AMPT
- AMQP (Advanced Message Queuing Protocol)는 메시지 브로커 시스템을 위한 개방형 네트워크 프로토콜로,
비동기적 메시지 전달을 지원하여 시스템 간의 통신과 데이터 교환을 용이하게 합니다.
- AMQP는 다양한 언어와 플랫폼에서 사용 가능하며, 분산 시스템의 효율적인 통신을 위해 설계되었습니다. 


# 내용
## AMQP의 구조
### Producer (생산자)
- 메시지를 생성하고 메시지 브로커로 전송하는 주체입니다.
### Broker (브로커)
- 메시지를 수신하고 적절한 큐에 메시지를 저장하는 중간 역할을 합니다. 
### Queue (큐)
- 메시지들이 저장되는 대기열로, Consumer가 메시지를 처리하기 전까지 보관됩니다. 
### Consumer (소비자)
- 큐에 있는 메시지를 가져와서 처리하는 주체입니다.

## 메시지 전달 방식
- AMQP는 메시지를 라우팅하기 위해 다양한 교환기(exchange)와 바인딩(binding)을 사용합니다. 
- 메시지는 Producer에서 Broker로 전송되고, 교환기를 통해 적절한 큐에 라우팅되어 Consumer가 메시지를 수신합니다.
- 교환기는 라우팅 알고리즘에 따라 메시지를 큐에 바인딩합니다.

## 메시지 속성
- AMQP 메시지는 머리(header), 속성(properties), 페이로드(payload)로 구성됩니다. 
- 머리는 메시지의 메타데이터를 포함하며, 속성은 메시지에 대한 추가 정보를 담고 있습니다.
- 페이로드는 실제 데이터를 가지고 있으며, 메시지 처리에 필요한 내용이 담겨 있습니다.

## 메시지의 지속성
- AMQP는 메시지의 지속성을 보장하기 위해 메시지를 디스크에 저장하고, 큐나 브로커의 재시작 시에도 메시지가 유지될 수 있도록 지원합니다. 
- 이를 통해 메시지의 손실을 방지하고, 안정적인 메시지 처리를 보장합니다.

## 보안
- AMQP는 TLS/SSL 암호화를 통해 메시지의 보안을 강화합니다. 
- 또한, 사용자 인증 및 접근 제어를 설정하여 민감한 데이터의 보호를 지원합니다.

## 프로토콜 버전
- AMQP는 버전 0-9-1과 1.0이 가장 널리 사용되며, 두 버전은 서로 다른 프로토콜입니다.
- AMQP 0-9-1은 RabbitMQ와 같은 브로커에서 주로 사용되고, AMQP 1.0은 Apache Qpid와 ActiveMQ와 같은 브로커에서 지원됩니다.



# 정리
- AMQP는 비동기적 메시지 전달을 지원하는 클라이언트와 브로커 시스템 간의 통신을 위한 개방형 프로토콜입니다. 
- Producer, Broker, Queue, Consumer의 구조로 이루어져 있으며, 메시지 전달 방식과 지속성, 보안 등 다양한 기능을 제공합니다. 
- 이를 통해 복잡한 분산 시스템에서 효율적인 메시지 교환과 데이터 처리를 가능하게 합니다.