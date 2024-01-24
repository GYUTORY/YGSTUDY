# 논문 제목
MQTT(MQ Telemetry Transport): Overview, Objectives, Applications, and Advantages

# 요약
- 경량 메시징 프로토콜로서, 기기 간 통신을 위해 설계된 프로토콜입니다.
- MQTT는 TCP/IP 프로토콜을 기반으로 하여, TCP 통신을 사용하여 메시지를 전송합니다.


# Publish-Subscribe 모델
-  메시지 송신자와 수신자 간의 느슨한 결합을 제공하여 효율적인 통신을 가능하게 합니다.

# 발행자 (Publisher)
- 발행자는 메시지를 생성하고 특정 주제(Topic)에 해당하는 메시지를 브로커에게 보냅니다. 
- 주제는 메시지의 종류나 카테고리를 나타내며, 일반적으로 슬래시('/')로 계층 구조를 형성합니다. 
- 예를 들어, "home/living_room/temperature"과 같은 주제는 주거 공간의 온도에 대한 메시지를 나타낼 수 있습니다.

# 구독자 (Subscriber)
- 구독자는 특정 주제(Topic)를 구독하여 해당 주제와 관련된 메시지를 받습니다.
- 구독자는 브로커에게 해당 주제를 알려주고, 해당 주제로 발행된 모든 메시지를 수신합니다. 
- 예를 들어, "home/living_room/temperature" 주제를 구독하는 구독자는 해당 주제로 발행된 온도 값에 대한 메시지를 받을 수 있습니다.


# MQTT Broker
- 브로커는 발행자와 구독자 사이에서 중간 매개체 역할을 합니다. 
- 발행자가 메시지를 브로커에게 보내면, 브로커는 해당 메시지를 해당 주제를 구독하는 모든 구독자에게 전달합니다. 
- 브로커는 발행자와 구독자 간의 통신을 관리하고, 메시지의 라우팅과 필터링 역할을 수행합니다. 
- 또한, QoS (Quality of Service) 수준을 관리하여 메시지의 전달 신뢰성과 효율성을 제어합니다.

# Mosca 와 Mosquito
    - Mosca와 Mosquito는 둘 다 MQTT 브로커(Broker)로 사용되는 소프트웨어입니다.
    그러나 두 소프트웨어는 다른 개발자 및 커뮤니티에 의해 개발되었으며, 각각의 특징과 기능에 약간의 차이가 있습니다.

# Mosca
- Mosca는 MQTT 브로커의 오픈 소스 구현으로서, Node.js로 작성되었습니다.
- Mosca는 경량화되고 확장 가능한 MQTT 브로커를 제공하기 위해 설계되었습니다. 
- Mosca는 MQTT 3.1.1 프로토콜 사양을 준수하며, 다양한 클라이언트 플랫폼과의 상호 운용성을 지원합니다.
- 또한 Mosca는 플러그인 아키텍처를 가지고 있어 사용자 정의 기능을 추가하고 확장할 수 있는 유연성을 제공합니다.

# Mosquitto
- Mosquitto는 Eclipse Foundation에서 개발된 MQTT 브로커 소프트웨어입니다. 
- C 언어로 작성되었으며, 경량화된 구현을 제공하여 다양한 임베디드 시스템이나 리소스 제한된 환경에서 사용할 수 있습니다.
- Mosquitto는 MQTT 3.1 및 3.1.1 프로토콜 사양을 지원하며, 다양한 플랫폼 및 운영 체제에서 실행될 수 있습니다.
- 또한 Mosquitto는 트랜스포트 보안(TLS/SSL)과 인증 메커니즘을 포함한 다양한 보안 기능을 제공합니다.

# Topic과 Message에 대해서 자세하게 알아보자.

Topic
- MQTT에서 Topic은 데이터를 발행(Publish) 및 구독(Subscribe)하는 데 사용되는 주제(Subject)를 나타냅니다.
- Topic은 계층적인 구조로 구성되며, 슬래시("/")를 구분자로 사용하여 계층을 구분합니다. 
- 예를 들어, "home/livingroom/temperature"과 같은 Topic은 "home"이라는 상위 계층, "livingroom"이라는 중간 계층, "temperature"이라는 최하위 계층으로 구성됩니다.
- Topic의 구조는 애플리케이션에 맞게 설계되며, 데이터의 주제와 구조를 표현하는 데 사용됩니다.

Message
- Message는 MQTT를 통해 주고받는 데이터를 의미합니다. 
- 메시지는 일반적으로 문자열 또는 이진 데이터의 형태를 가지며, Topic에 연결된 MQTT 클라이언트에게 전달됩니다. 
- 발행자(Publisher)는 특정 Topic으로 메시지를 발행하면, 해당 Topic을 구독하는 모든 구독자(Subscriber)에게 메시지가 전송됩니다.
- 메시지는 주제와 함께 전달되며, 수신자는 Topic을 통해 메시지를 구분하고 처리할 수 있습니다.
- 예를 들어, "home/livingroom/temperature" Topic으로 온도 데이터를 발행하면, 해당 Topic을 구독하는 모든 구독자는 온도 데이터 메시지를 수신하고 처리할 수 있습니다.

