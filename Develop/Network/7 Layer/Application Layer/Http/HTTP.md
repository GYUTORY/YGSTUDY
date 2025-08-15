---
title: HTTP HyperText Transfer Protocol
tags: [network, 7-layer, application-layer, http]
updated: 2025-08-10
---
# HTTP (HyperText Transfer Protocol)

## HTTP 개요
- HTTP는 웹의 기반이 되는 프로토콜로, HTML 문서와 같은 리소스들을 가져올 수 있도록 해주는 프로토콜입니다.
- 클라이언트-서버 모델을 따르는 프로토콜입니다.
- 기본적으로 80번 포트를 사용합니다.
- HTTPS는 HTTP의 보안이 강화된 버전으로, 443번 포트를 사용합니다.

## HTTP 기반 시스템의 구성요소

### 1. 클라이언트 (사용자 에이전트)
- 웹 브라우저가 가장 일반적인 클라이언트입니다.
- 사용자를 대신하여 HTTP 요청을 보내는 모든 도구가 클라이언트가 될 수 있습니다.
- 예시:
  - 웹 브라우저 (Chrome, Firefox, Safari 등)
  - 검색 엔진 크롤러
  - 모바일 앱
  - IoT 기기

### 2. 서버
- 클라이언트의 요청에 대한 응답을 제공하는 시스템
- 일반적으로 다음과 같은 역할을 수행:
  - 정적 파일 제공 (HTML, CSS, JavaScript, 이미지 등)
  - 동적 콘텐츠 생성
  - 데이터베이스 조작
  - 비즈니스 로직 처리

### 3. 프록시
- 클라이언트와 서버 사이에 위치하는 중간 서버
- 주요 기능:
  - 캐싱
  - 필터링
  - 로드 밸런싱
  - 인증
  - 로깅

## HTTP 프로토콜의 특징

### 1. Connectionless (비연결 지향)
- 클라이언트가 서버에 요청을 보내고 서버가 응답을 보내면 연결이 종료됩니다.
- 장점:
  - 서버 리소스의 효율적 사용
  - 동시 접속자 수 증가 가능
- 단점:
  - 매 요청마다 새로운 연결 설정 필요
  - 연결 설정에 따른 지연 발생

### 2. Stateless (무상태)
- 각 요청은 독립적으로 처리되며, 이전 요청과의 연관성이 없습니다.
- 장점:
  - 서버의 복잡도 감소
  - 확장성이 좋음
- 단점:
  - 상태 정보 유지를 위한 추가 작업 필요
  - 매 요청마다 인증 정보 전송 필요

### 3. 앱에서 세션을 사용하지 않는 이유
- HTTP의 Stateless 특성으로 인해 서버에서 세션을 관리해야 합니다.
- 모바일 앱의 특성상 다음과 같은 문제가 발생할 수 있습니다:
  - 네트워크 연결 불안정성
  - 앱 백그라운드 전환 시 세션 유지 어려움
  - 보안 취약점 (세션 하이재킹)
- 대안:
  - JWT (JSON Web Token) 사용
  - OAuth 2.0 인증
  - API 키 기반 인증

## HTTP 통신 흐름

### 1. TCP 연결 설정
- 클라이언트가 서버와 TCP 연결을 수립합니다.
- 연결 방식:
  - 새로운 연결 생성
  - 기존 연결 재사용
  - 여러 TCP 연결 병렬 사용

### 2. HTTP 메시지 전송
- HTTP/1.1: 텍스트 기반의 읽기 쉬운 메시지 형식
- HTTP/2: 바이너리 프로토콜로 변경되어 프레임 단위로 전송
- 메시지 구성:
  - 시작줄 (요청/응답 라인)
  - 헤더
  - 본문

### 3. 서버 응답 처리
- 서버는 요청을 처리하고 적절한 응답을 반환합니다.
- 응답 구성:
  - 상태 코드
  - 응답 헤더
  - 응답 본문

### 4. 연결 종료 또는 재사용
- HTTP/1.0: 각 요청마다 새로운 연결
- HTTP/1.1: Keep-Alive를 통한 연결 재사용
- HTTP/2: 멀티플렉싱을 통한 효율적인 연결 관리

## HTTP 메서드
- GET: 리소스 조회
- POST: 리소스 생성
- PUT: 리소스 수정
- DELETE: 리소스 삭제
- PATCH: 리소스 부분 수정
- HEAD: 리소스 헤더만 조회
- OPTIONS: 지원하는 메서드 조회
- TRACE: 요청/응답 추적
- CONNECT: 프록시 서버 연결

## HTTP 상태 코드
### 1xx (정보)
- 100 Continue
- 101 Switching Protocols

### 2xx (성공)
- 200 OK
- 201 Created
- 204 No Content

### 3xx (리다이렉션)
- 301 Moved Permanently
- 302 Found
- 304 Not Modified

### 4xx (클라이언트 오류)
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found

### 5xx (서버 오류)
- 500 Internal Server Error
- 502 Bad Gateway
- 503 Service Unavailable

## HTTP 헤더

## 배경
- Date
- Connection
- Cache-Control

- Host
- User-Agent
- Accept
- Authorization

- Server
- Set-Cookie
- Content-Type
- Content-Length

### HTTPS
- SSL/TLS를 통한 암호화
- 인증서를 통한 신원 확인
- 데이터 무결성 보장

### 보안 헤더
- HSTS
- CSP
- X-Frame-Options
- X-XSS-Protection

> 출처: 
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Overview
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Methods
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Status

- HSTS
- CSP
- X-Frame-Options
- X-XSS-Protection

> 출처: 
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Overview
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Methods
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Status






- HSTS
- CSP
- X-Frame-Options
- X-XSS-Protection

> 출처: 
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Overview
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Methods
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Status

- HSTS
- CSP
- X-Frame-Options
- X-XSS-Protection

> 출처: 
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Overview
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Methods
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Status










