# RabbitMQTT
- RabbitMQ와 MQTT 프로토콜을 결합한 메시지 브로커입니다.
- RabbitMQ는 AMQP(Advanced Message Queuing Protocol)를 사용하는 메시지 브로커이며,
MQTT는 경량 메시징 프로토콜로 주로 IoT(Internet of Things) 디바이스와 통신에 사용됩니다.
- RabbitMQTT는 이 두 가지 프로토콜의 강점을 결합하여 메시지 전달을 효율적으로 처리하는데 사용됩니다.


# RabbitMQTT의 기본 작동 원리
## Publisher
- 메시지를 생성하고 RabbitMQTT에게 메시지를 전송합니다. 
- 이때, MQTT 프로토콜을 통해 메시지를 발행(publish)합니다.

## RabbitMQTT
- RabbitMQTT 서버는 MQTT 프로토콜을 지원하고, 받은 메시지를 AMQP 형식으로 변환하여 RabbitMQ로 전달합니다.

## RabbitMQ
- RabbitMQ는 AMQP 메시지 브로커로서 메시지를 받아들이고, 메시지 큐에 저장하거나 바로 소비자에게 전달합니다.

## Consumer
- 메시지를 받기 위해 RabbitMQTT에 연결된 MQTT 구독자들이 있습니다. 
- RabbitMQ는 받은 메시지를 MQTT 프로토콜을 사용하여 구독자에게 전송합니다.


# RabbitMQTT의 사용법
- MQTT를 이해하고 RabbitMQ에 대한 기본적인 지식이 필요합니다. 
- 다음은 RabbitMQTT를 사용하는 간단한 예제입니다.

## RabbitMQTT 설치 및 설정
- RabbitMQ를 설치하고 RabbitMQTT 플러그인을 활성화합니다. 
- 이를 통해 MQTT 프로토콜 지원이 가능해집니다.

## Publisher 작성
- 메시지를 생성하고 MQTT 프로토콜을 통해 RabbitMQTT에 메시지를 발행하는 출판자(Publisher)를 작성합니다.

## Consumer 작성
- RabbitMQTT에 구독(subscribe)하여 메시지를 받을 수 있는 구독자(Consumer)를 작성합니다.

## 메시지 발행과 구독
- Publisher는 메시지를 RabbitMQTT에 발행하고, 해당 메시지를 구독하고 있는 Consumer가 메시지를 받아 처리합니다.


### RabbitMQTT에서는 MQTT의 토픽(topic)은 사용하지 않나?
- MQTT에서 토픽은 메시지를 발행자(Publisher)에서 구독자(Subscriber)로 라우티아는 데 사용되는 계층적인 문자열입니다.
- 발행자는 특정 토픽에 메시지를 발행하고, 구독자는 해당 토픽에 대해 구독하여 해당 토픽과 일치하는 메시지를 수신합니다.
- MQTT 토픽은 RabbitMQ에서 직접 사용되지 않습니다. 
- 대신, RabbitMQTT는 MQTT 토픽을 RabbitMQ의 라우팅 키(routing key)와 큐(queue)에 매핑합니다.

## RabbitMQTT가 MQTT 토픽을 다루는 방법
### MQTT 토픽과 RabbitMQ 교환(exchange) 매핑
- MQTT 토픽으로 메시지가 발행되면, RabbitMQTT는 해당 토픽을 RabbitMQ 교환으로 매핑합니다. 
- 이 매핑은 일반적으로 RabbitMQTT에서 구성되며, 메시지를 RabbitMQ에서 어떻게 분배할지 결정합니다.

### RabbitMQ 교환과 큐 매핑
- RabbitMQ에서 메시지는 교환으로 발행되고, 라우팅 키를 기반으로 큐로 라우팅됩니다. 
- RabbitMQTT는 MQTT 토픽을 RabbitMQ의 라우팅 키와 매핑합니다.
- 따라서 매핑 및 라우팅 키에 따라 메시지가 하나 이상의 큐로 전달될 수 있습니다.

### 소비자와 큐
- RabbitMQ에서 소비자는 특정 큐를 구독합니다.
- 메시지는 교환으로부터 매핑과 라우팅 키에 따라 큐로 라우팅되고, 이후 소비자는 해당 큐에서 메시지를 수신합니다.

## 정리
> 요약하면, RabbitMQTT는 MQTT 토픽을 직접 사용하지 않지만, MQTT 토픽을 RabbitMQ 교환과 라우팅 키에 매핑하여 유사한 기능을 구현합니다. 실제로 RabbitMQ에서의 메시지 라우팅 및 전달은 RabbitMQ의 교환과 큐 시스템에 의존합니다.
