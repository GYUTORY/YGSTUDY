최종 업데이트 2026-01-13, 버전 v1.1

# YGSTUDY 인덱스

레포 전체를 한눈에 볼 수 있도록 주제 맵과 대표 문서를 모았습니다.

각 섹션은 3줄 요약과 대표 문서 3개 링크를 제공합니다.

## Application Architecture
- 현대 서버 애플리케이션의 구조와 패턴을 정리합니다.
- 마이크로서비스, 쿠버네티스, 디자인 패턴 관점에서 핵심 개념을 담았습니다.
- 실무 적용 시 고려 포인트(운영, 신뢰성, 확장)를 함께 다룹니다.

- 대표 문서:
  - [MSA 개요](Develop/Application Architecture/MSA/MSA.md)
  - [Kubernetes 핵심](Develop/Application Architecture/Kubernetes/Kubernetes.md)
  - [생성 패턴](Develop/Application Architecture/Design Pattern/생성 패턴.md)

## AWS
- AWS 인프라 구성 요소와 운영 모범사례를 묶었습니다.
- 컨테이너(ECR/ECS/EKS), 네트워킹(Route 53/S3), 보안(IAM/KMS)을 포함합니다.
- 선택 기준과 비용/보안 고려사항을 함께 다룹니다.

- 대표 문서:
  - [EKS](Develop/AWS/Containers/EKS.md)
  - [ECS vs EKS 비교](Develop/AWS/Containers/ECS와 EKS 비교.md)
  - [IAM](Develop/AWS/Security/IAM.md)

## DataBase
- RDBMS/NoSQL 기초부터 성능 최적화까지 정리했습니다.
- 인덱스/락/격리수준, 실행계획, Redis 운용 포인트를 다룹니다.
- 보안(SQL Injection)과 운영을 포함합니다.

- 대표 문서:
  - [RDBMS에서의 Index](Develop/DataBase/RDBMS/RDBMS에서의 index.md)
  - [Lock](Develop/DataBase/RDBMS/Lock.md)
  - [Redis](Develop/DataBase/NoSQL/Redis/Redis.md)

## Framework
- Node/NestJS, Java/Spring 프레임워크의 구조와 사용법입니다.
- DI, 모듈 구조, 테스트, 런타임 동작을 다룹니다.
- 프로젝트에 바로 적용 가능한 예시들을 포함합니다.

- 대표 문서:
  - [NestJS Basic](Develop/Framework/Node/NestJS/Basic.md)
  - [exports vs providers](Develop/Framework/Node/NestJS/exports_vs_providers.md)
  - [Spring Bean](Develop/Framework/Java/Spring/Bean.md)

## Language
- Java/JavaScript/TypeScript의 핵심 문법과 심화 주제입니다.
- 비동기, 제너레이터, 고급 타입, 컬렉션 등 실전 중심으로 구성했습니다.
- 프로젝트 설정(ESLint/Prettier/tsconfig)도 포함합니다.

- 대표 문서:
  - [JS 비동기 메커니즘](Develop/Language/JavaScript/05_이벤트_루프_비동기/JavaScript의 비동기 처리 메커니즘.md)
  - [TypeScript 유틸리티 타입](Develop/Language/TypeScript/ 타입 유틸리티/유틸리티 타입.md)
  - [JVM 구조](Develop/Language/Java/JVM 관련/JVM/JVM 구조 및 메모리 관리.md)

## Network
- OSI 7계층, HTTP/HTTPS, TLS, TCP 등을 정리했습니다.
- 대용량 API 처리, 프로토콜 선택 기준 등 설계 관점을 제공합니다.
- gRPC/MQTT/RPC 등 통신 스택 비교를 포함합니다.

- 대표 문서:
  - [HTTP](Develop/Network/7 Layer/Application Layer/Http/HTTP.md)
  - [TLS Handshake](Develop/Network/7 Layer/Application Layer/Http/TLS HandShake.md)
  - [gRPC](Develop/Network/7 Layer/Transport Layer/TCP/RPC/gRPC.md)

## OS
- 프로세스/스레드, 메모리 구조, 동시성 개념을 다룹니다.
- 스케줄링, 컨텍스트 스위칭 등 시스템 동작의 기본을 정리했습니다.
- 운영 관점의 핵심 체크포인트를 담았습니다.

- 대표 문서:
  - [Process & Thread](Develop/OS/Process & Thread/Process & Thread.md)
  - [메모리 관리](Develop/OS/Memory/메모리 관리.md)
  - [레이드 컨디션](Develop/OS/레이드 컨디션.md)

## Security
- 대칭/비대칭 암호, 해시, 인증/인가의 기본을 정리했습니다.
- 운영 환경에서의 보안 헤더, 시크릿 관리, 로테이션을 다룹니다.
- 보안 점검을 위한 확인 사항을 제공합니다.

- 대표 문서:
  - [AES](Develop/Security/AES.md)
  - [RSA](Develop/Security/RSA.md)
  - [SHA](Develop/Security/SHA.md)

## WebServer
- Nginx 기본, SSL/TLS 설정, 리버스 프록시 구성을 담았습니다.
- 캐시, 레이트 리미트, 헬스체크 등 운영 팁을 정리합니다.
- Ingress/로드밸런서 연동 시 고려사항을 포함합니다.

- 대표 문서:
  - [Nginx SSL](Develop/WebServer/Nginx/SSL.md)
  - [CORS](Develop/WebServer/Nginx/CORS.md)
  - [TLS & SSL](Develop/WebServer/TLS & SSL.md)

## DevOps
- CI/CD 파이프라인, GitOps, IaC의 기초를 다룹니다.
- 팀 개발을 위한 자동화와 품질 보증 흐름을 담았습니다.
- 예제 중심으로 빠르게 적용할 수 있습니다.

- 대표 문서:
  - [Bitbucket Pipeline](Develop/DevOps/CI_CD/Bitbucket_Pipeline.md)
  - [Node Bitbucket Pipeline](Develop/Framework/Node/Bitbucket_Pipeline.md)
  - [SSM Deploy](Develop/AWS/Monitoring & Management/SSM_Deploy.md)

## DataRepresentation
- 2진수/16진수, 인코딩, 버퍼 등 데이터 표현의 기본입니다.
- 비트 연산과 수 체계 전환을 사례로 설명합니다.
- 실제 버그로 이어지는 함정도 함께 다룹니다.

- 대표 문서:
  - [2진수→16진수 변환](Develop/DataRepresentation/2진수를 16진수로 변환하는 방법.md)
  - [Buffer](Develop/DataRepresentation/Buffer.md)
  - [Base64](Develop/DataRepresentation/Encoding/Base64.md)

---

문서 전반은 지속적으로 보완 중입니다.

새로 작성하거나 수정한 문서는 상단의 "최종 업데이트/버전" 표기를 따라갑니다.

