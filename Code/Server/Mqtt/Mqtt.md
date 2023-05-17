# 논문 제목
MQTT(MQ Telemetry Transport): Overview, Objectives, Applications, and Advantages

# 요약
 - 해당 내용은 MQTT(MQ Telemetry Transport) 프로토콜에 대한 개요, 목적, 사용 내용, 그리고 장점에 대해 다룹니다.
 - MQTT는 경량의 기계 간 통신을 위한 표준 메시징 프로토콜로서, 제한된 대역폭과 리소스가 있는 네트워크 환경에서 효율적인 데이터 전송을 제공합니다.
 - MQTT는 Publisher-Subscriber 모델을 기반으로 하며, 토픽을 통해 실시간 데이터 스트리밍과 이벤트 기반 통신을 지원합니다. 
 - 해당 설명은 MQTT의 기능과 특징을 설명하고, 다양한 응용 분야에서의 사용 사례를 소개하며, MQTT의 장점과 활용 가능성에 대해 논의합니다.

# 목차

서론
- 연구 배경
- 연구 목적

MQTT 개요
- MQTT의 기본 개념
- MQTT의 동작 방식
- MQTT의 주요 구성 요소
- MQTT 통신 모델

MQTT의 목적
- 리소스 제약된 환경에서의 데이터 전송
- 실시간 데이터 스트리밍 및 이벤트 기반 통신
- IoT 및 M2M 통신을 위한 표준 프로토콜

MQTT의 사용 내용
- 디바이스 간 통신을 위한 MQTT 프로토콜의 구현
- 토픽 기반 데이터 발행 및 구독
- MQTT 브로커의 역할과 기능

MQTT의 장점
- 가벼움과 효율성
- 확장성과 저전력 소비
- 신뢰성과 QoS(Quality of Service) 지원
- 보안 기능과 인증 프로토콜
- 다양한 언어 및 플랫폼의 지원

MQTT의 응용 분야
- 스마트 홈 및 스마트 시티
- 산업 자동화와 제조업체
- 헬스케어 및 의료 분야
- MQTT의 응용 분야
- 스마트 홈 및 스마트 시티
- 산업 자동화와 제조업체
- 헬스케어 및 의료 분야
- 교통 및 운송 관리
- 에너지 관리 시스템

# Publisher
- Publisher는 MQTT 브로커에 데이터를 발행하는 역할을 합니다.
- 특정 토픽에 대한 발행 권한이 필요합니다.
- 아래는 Node.js를 사용한 MQTT Publisher의 코드 예시입니다
- 

      const mqtt = require('mqtt');

      // MQTT 브로커에 연결
      const client = mqtt.connect('mqtt://broker.example.com');

      // 연결이 수립되면 데이터를 발행
      client.on('connect', () => {
         const topic = 'mytopic'; // 발행할 토픽
         const message = 'Hello, MQTT!'; // 발행할 메시지

         // 토픽에 데이터 발행
         client.publish(topic, message, (err) => {
         
         if (err) {
            console.error('Failed to publish message:', err);
         } else {
            console.log('Message published successfully.');
         }

         // 연결 종료
         client.end();
         });
      });

# Subscriber
- Subscriber는 MQTT 브로커에서 특정 토픽을 구독하여 데이터를 수신하는 역할을 합니다.
- MQTT 브로커로부터 발행된 데이터를 실시간으로 수신합니다.
- 아래는 Python을 사용한 MQTT Subscriber의 코드 예시입니다

       const mqtt = require('mqtt');
   
       // MQTT 브로커에 연결
       const client = mqtt.connect('mqtt://broker.example.com');
   
       // 연결이 수립되면 토픽을 구독
       client.on('connect', () => {
       const topic = 'mytopic'; // 구독할 토픽
   
       // 토픽 구독
       client.subscribe(topic, (err) => {
          if (err) {
              console.error('Failed to subscribe:', err);
          } else {
              console.log('Subscribed to topic:', topic);
          }
        });
       });
   
       // 데이터를 수신하면 처리
       client.on('message', (topic, message) => {
           console.log('Received message:', 'Topic=', topic, 'Message=', message.toString());
       });
   
       // 연결 종료 시 처리
       client.on('close', () => {
           console.log('Disconnected from MQTT broker');
       });


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

