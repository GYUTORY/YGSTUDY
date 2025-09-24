---
title: AWS SNS (Simple Notification Service) 완전 가이드
tags: [aws, sns, notification, messaging, pub-sub, serverless]
updated: 2025-09-24
---

# AWS SNS (Simple Notification Service) 완전 가이드

## 서비스 개요

AWS SNS(Simple Notification Service)는 완전 관리형 메시지 알림 서비스로, 애플리케이션과 서비스 간의 메시지 전달을 위한 중앙 집중식 허브 역할을 합니다. 이 서비스는 퍼블리셔-구독자(Pub-Sub) 패턴을 기반으로 하여, 한 곳에서 메시지를 발행하면 여러 구독자에게 동시에 전달할 수 있는 구조를 제공합니다.

### 핵심 아키텍처 개념

**퍼블리셔(Publisher)**
- 메시지를 생성하고 SNS 주제에 발행하는 주체
- 애플리케이션, 서비스, 또는 AWS 서비스가 될 수 있음
- 메시지 발행 시 구독자에 대한 직접적인 지식이 필요하지 않음

**주제(Topic)**
- 메시지의 중앙 집중식 엔드포인트
- 고유한 ARN(Amazon Resource Name)을 가짐
- 메시지를 받아서 모든 구독자에게 전달하는 역할

**구독자(Subscriber)**
- 주제를 구독하여 메시지를 수신하는 엔드포인트
- 이메일, SMS, 모바일 푸시, HTTP(S), Lambda, SQS 등 다양한 형태 지원

## 핵심 특징과 장점

### 푸시 기반 메시징 시스템
SNS는 푸시 기반 메시징을 채택하여 구독자가 메시지를 폴링할 필요 없이 실시간으로 알림을 받을 수 있습니다. 이는 시스템 리소스를 절약하고 응답성을 향상시킵니다.

### 높은 확장성과 가용성
- 자동으로 확장되어 트래픽 증가에 대응
- AWS의 글로벌 인프라를 활용한 고가용성 보장
- 99.9% 이상의 가용성 SLA 제공

### 다양한 전송 프로토콜 지원
- **이메일**: SMTP를 통한 이메일 알림
- **SMS**: 전 세계 모바일 기기로 문자 메시지 전송
- **모바일 푸시**: APNS(Apple), FCM(Google), ADM(Amazon) 지원
- **HTTP/HTTPS**: RESTful API 엔드포인트로 메시지 전달
- **AWS 서비스**: Lambda, SQS, Kinesis Data Firehose 등과 연동

### 메시지 필터링 기능
구독자별로 메시지 필터 정책을 설정하여 필요한 메시지만 수신할 수 있습니다. 이는 불필요한 트래픽을 줄이고 비용을 절약하는 데 도움이 됩니다.

## 메시지 전달 보장과 재시도 정책

### At-Least-Once 전달 보장
SNS는 메시지가 최소 한 번은 전달되도록 보장합니다. 네트워크 오류나 일시적인 장애로 인해 메시지 전달이 실패할 경우, 자동으로 재시도합니다.

### 재시도 정책
- **표준 주제**: 지수 백오프를 사용한 재시도
- **FIFO 주제**: 순서가 보장되는 메시지 전달
- **Dead Letter Queue**: 최대 재시도 횟수 초과 시 실패한 메시지 처리

## 보안과 접근 제어

### IAM 기반 권한 관리
- 세밀한 권한 제어를 통한 보안 강화
- 주제별, 구독자별 접근 권한 설정 가능
- 교차 계정 액세스 지원

### 암호화
- 전송 중 암호화(TLS/SSL)
- 저장 시 암호화(KMS 키 사용 가능)
- 엔드포인트 인증을 통한 메시지 무결성 보장

## 비용 구조와 최적화

### 사용량 기반 과금
- 메시지 발행 건수에 따른 과금
- 전송 프로토콜별 차등 요금
- 데이터 전송 비용 별도 적용

### 비용 최적화 전략
- 메시지 필터링을 통한 불필요한 전송 방지
- 적절한 메시지 크기 유지
- 지역별 가격 차이 고려한 리전 선택

## 실제 사용 사례

### 이커머스 주문 알림 시스템
온라인 쇼핑몰에서 주문이 발생하면 SNS를 통해 다양한 알림을 동시에 전송할 수 있습니다. 주문 확인 이메일, 배송 상태 SMS, 모바일 앱 푸시 알림을 하나의 주제에서 관리하여 시스템 복잡성을 줄이고 일관성을 유지할 수 있습니다.

### 모니터링 및 알림 시스템
시스템 장애나 임계값 초과 시 개발팀, 운영팀, 관리자에게 즉시 알림을 전송합니다. CloudWatch와 연동하여 자동화된 모니터링 시스템을 구축할 수 있으며, 심각도에 따라 다른 알림 채널을 사용할 수 있습니다.

### 마이크로서비스 간 이벤트 전파
마이크로서비스 아키텍처에서 서비스 간 느슨한 결합을 위해 SNS를 활용합니다. 주문 서비스에서 주문 완료 이벤트를 발행하면, 재고 관리, 결제, 배송 서비스가 각각 필요한 작업을 수행할 수 있습니다.

### 사용자 참여도 향상
앱 사용자에게 개인화된 푸시 알림을 전송하여 사용자 참여도를 높입니다. 사용자 행동 패턴에 따라 맞춤형 메시지를 전송하고, A/B 테스트를 통해 최적의 메시지 전략을 수립할 수 있습니다.

## SNS와 다른 AWS 서비스 연동

### SNS + SQS 패턴
SNS에서 SQS로 메시지를 전달하는 패턴은 매우 일반적입니다. 이는 메시지 버퍼링, 배치 처리, 재시도 로직 구현에 유용합니다. SNS가 푸시 기반이라면 SQS는 풀 기반으로, 두 서비스의 장점을 결합할 수 있습니다.

### SNS + Lambda 패턴
Lambda 함수를 SNS 구독자로 설정하여 서버리스 이벤트 처리 시스템을 구축할 수 있습니다. 메시지 수신 시 Lambda 함수가 자동으로 실행되어 비즈니스 로직을 처리합니다.

### SNS + CloudWatch 패턴
CloudWatch 알람이 임계값을 초과하면 SNS를 통해 알림을 전송합니다. 이를 통해 시스템 모니터링과 알림을 자동화할 수 있습니다.

## 운영 모범 사례

### 메시지 설계 원칙
- 메시지 크기를 최소화하여 전송 비용 절약
- 구조화된 메시지 형식(JSON) 사용으로 파싱 효율성 향상
- 메시지 버전 관리로 하위 호환성 유지

### 모니터링과 로깅
- CloudWatch 메트릭을 통한 메시지 전송 성공률 모니터링
- 실패한 메시지에 대한 Dead Letter Queue 설정
- 구독자별 전송 지연 시간 추적

### 보안 고려사항
- 민감한 정보는 메시지에 포함하지 않고 참조 ID만 전송
- HTTPS 엔드포인트 사용으로 전송 중 암호화 보장
- 주제 정책을 통한 접근 권한 세밀하게 제어

### 성능 최적화
- 메시지 필터링을 통한 불필요한 전송 방지
- 배치 처리 가능한 경우 SQS와 연동하여 효율성 향상
- 리전별 가격 차이를 고려한 최적 리전 선택

## 주의사항과 제한사항

### 메시지 크기 제한
- 단일 메시지 최대 크기: 256KB
- 큰 데이터는 S3에 저장하고 참조 링크만 전송 권장

### 전송 프로토콜별 제한
- SMS: 일일 전송 한도 및 국가별 제한 존재
- 이메일: 스팸 필터링으로 인한 전송 실패 가능성
- 모바일 푸시: 플랫폼별 인증서 관리 필요

### 비용 관리
- 메시지 발행 건수에 따른 과금으로 예상치 못한 비용 발생 가능
- 필터링을 통한 불필요한 전송 방지로 비용 절약
- 사용량 모니터링을 통한 비용 예산 관리

## 참고 자료

### AWS 공식 문서
- [AWS SNS 개발자 가이드](https://docs.aws.amazon.com/ko_kr/sns/latest/dg/welcome.html)
- [SNS API 참조](https://docs.aws.amazon.com/ko_kr/sns/latest/api/welcome.html)
- [SNS 모범 사례](https://docs.aws.amazon.com/ko_kr/sns/latest/dg/sns-best-practices.html)
- [SNS 보안 모범 사례](https://docs.aws.amazon.com/ko_kr/sns/latest/dg/sns-security-best-practices.html)

### AWS 서비스 연동 가이드
- [SNS와 SQS 연동](https://docs.aws.amazon.com/ko_kr/sns/latest/dg/sns-sqs-as-subscriber.html)
- [SNS와 Lambda 연동](https://docs.aws.amazon.com/ko_kr/sns/latest/dg/sns-lambda-as-subscriber.html)
- [CloudWatch와 SNS 연동](https://docs.aws.amazon.com/ko_kr/AmazonCloudWatch/latest/monitoring/US_SetupSNS.html)

### SDK 및 도구
- [AWS SDK for JavaScript v3](https://docs.aws.amazon.com/sdk-for-javascript/v3/developer-guide/sns-examples.html)
- [AWS CLI SNS 명령어](https://docs.aws.amazon.com/cli/latest/reference/sns/)
- [AWS CDK SNS 구성 요소](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_sns-readme.html)

### 추가 학습 자료
- [AWS Well-Architected Framework - 메시징](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/messaging.html)
- [AWS 아키텍처 센터 - SNS 사용 사례](https://aws.amazon.com/architecture/)
- [AWS re:Invent 세션 - SNS 심화 학습](https://www.youtube.com/results?search_query=aws+reinvent+sns)
