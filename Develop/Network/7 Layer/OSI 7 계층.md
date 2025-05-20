- 2024-04-27 초안 작성중 

# OSI 7 Layer

---

## 작동 원리
1. OSI 7계층은 응용, 표현, 세션, 전송, 네트워크, 데이터링크, 물리계층으로 나뉨.
2. 전송 시 7계층에서 1계층으로 각각의 층마다 인식할 수 있어야 하는 헤더를 붙임(캡슐화)
3. 수신 시 1계층에서 7계층으로 헤더를 떼어냄(디캡슐화)
4. 출발지에서 데이터가 전송될 때 헤더가 추가되는데 2계층에서만 오류제어를 위해 꼬리부분에 추가됌
5. 물리계층에서 1, 0 의 신호가 되어 전송매체 (동축케이블, 광섬유 등)을 통해 전송

![OSI 7 Layer.jpeg](..%2F..%2F..%2Fetc%2Fimage%2FNetwork_image%2FOSI%207%20Layer.jpeg)

## 물리계층(Physical Layer)
- 주로 전기적, 기계적, 기능적인 특성을 이용해 통신 케이블로 데이터를 전송하는 **물리적인 장비**
- 데이터는 0과 1의 비트열로 변환해서 주고받는 기능만 할 뿐
- 데이터 단위 : Bit
- 장비 : **통신 케이블, 리퍼터, 허브** 등

### 주요 기능
- 비트 스트림을 전기적 신호로 변환
- 물리적 매체를 통한 비트 전송
- 물리적 연결의 설정, 유지, 해제
- 전송 속도, 전송 모드(단방향, 양방향) 제어

### 실제 예시
- 이더넷 케이블(RJ-45)
- 광섬유 케이블
- 무선 LAN의 전파
- USB 케이블

## 데이터링크 계층(Data-Link Layer)
- 물리계층을 통해 송수신되는 정보의 오류와 흐름을 관리하여 안전한 통신의 흐름을 관리
- 프레임에 물리적 주소(MAC address)를 부여하고 에러검출, 재전송, 흐름제어를 수행
- 데이터 단위 : Frame
- 장비 : **브리지, 스위치, 이더넷** 등(여기서 MAC주소를 사용)

### 주요 기능
- 프레임 동기화
- 흐름 제어(Flow Control)
- 오류 제어(Error Control)
- MAC 주소를 통한 통신
- 프레임의 순서 제어

### 실제 프로토콜
- Ethernet
- PPP(Point-to-Point Protocol)
- HDLC(High-Level Data Link Control)
- ATM(Asynchronous Transfer Mode)

## 네트워크 계층(Network Layer)
- 데이터를 목적지까지 가장 안전하고 빠르게 전달
- 라우터(Router)를 통해 경로를 선택하고 주소를 정하고(IP) 경로(Route)에 따라 패킷을 전달 > IP 헤더 붙음
- 데이터 단위 : Packet
- 장비 : **[라우터]([라우팅.md](..%2F%EB%9D%BC%EC%9A%B0%ED%8C%85.md))**

### 주요 기능
- 라우팅(Routing)
- 패킷 포워딩(Packet Forwarding)
- 논리적 주소 지정(IP 주소)
- 서브네팅(Subnetting)
- QoS(Quality of Service) 관리

### 실제 프로토콜
- IP(Internet Protocol)
- ICMP(Internet Control Message Protocol)
- IGMP(Internet Group Management Protocol)
- ARP(Address Resolution Protocol)
- RARP(Reverse Address Resolution Protocol)

## 전송 계층(Transport Layer)
- port 번호, 전송방식(TCP/UDP) 결정 > TCP 헤더 붙음
  - TCP : 신뢰성, 연결지향적
  - UDP : 비신뢰성, 비연결성, 실시간
- 두 지점간의 신뢰성 있는 데이터를 주고 받게 해주는 역할
- 신호를 분산하고 다시 합치는 과정을 통해서 에러와 경로를 제어

### TCP의 주요 특징
- 연결 지향적(Connection-oriented)
- 신뢰성 있는 전송 보장
- 순서 보장
- 흐름 제어
- 혼잡 제어
- 3-way handshaking을 통한 연결 설정
- 4-way handshaking을 통한 연결 종료

### UDP의 주요 특징
- 비연결형(Connectionless)
- 최소한의 오류 검사
- 실시간 전송에 적합
- 헤더 오버헤드가 적음
- 멀티캐스트/브로드캐스트 지원

### 실제 프로토콜
- TCP(Transmission Control Protocol)
- UDP(User Datagram Protocol)
- SCTP(Stream Control Transmission Protocol)
- DCCP(Datagram Congestion Control Protocol)

## 세션 계층(Session Layer)
- 주 지점간의 프로세스 및 통신하는 호스트 간의 연결 유지
- TCP/IP 세션 체결, 포트번호를 기반으로 통신 세션 구성
- API, Socket

### 주요 기능
- 세션 설정, 관리, 종료
- 동기화(Synchronization)
- 대화 제어(Dialog Control)
- 토큰 관리
- 체크포인트 설정

### 실제 프로토콜
- NetBIOS
- RPC(Remote Procedure Call)
- SQL
- NFS(Network File System)

## 표현 계층(Presentation Layer)
- 데이터를 어떻게 표현할지 정하는 역할을 하는 계층

### 주요 기능
- 데이터 형식 변환
- 데이터 압축/해제
- 데이터 암호화/복호화
- 문자 코드 변환
- 미디어 포맷 변환

### 실제 예시
- JPEG, PNG, GIF (이미지 포맷)
- MPEG, AVI (비디오 포맷)
- ASCII, Unicode (문자 인코딩)
- SSL/TLS (암호화)
- MIME (이메일 첨부파일)

## 응용 계층(Application Layer)
- 사용자와 가장 밀접한 계층으로 인터페이스 역할
- 응용 프로세스 간의 정보 교환을 담당
- 최종 목적지로, 응용 프로세스와 직접 관계하여 일반적인 응용 서비스를 수행

### 주요 프로토콜
- HTTP/HTTPS (웹 서비스)
- FTP (파일 전송)
- SMTP, POP3, IMAP (이메일)
- DNS (도메인 이름 시스템)
- DHCP (동적 IP 할당)
- SNMP (네트워크 관리)
- Telnet, SSH (원격 접속)

### 실제 응용 프로그램
- 웹 브라우저
- 이메일 클라이언트
- 파일 공유 프로그램
- 메신저
- 게임 클라이언트

---
* 참고자료
> [1] [네트워크의 기본 OSI 7 계층](https://velog.io/@cgotjh/%EB%84%A4%ED%8A%B8%EC%9B%8C%ED%81%AC-OSI-7-%EA%B3%84%EC%B8%B5-OSI-7-LAYER-%EA%B8%B0%EB%B3%B8-%EA%B0%9C%EB%85%90-%EA%B0%81-%EA%B3%84%EC%B8%B5-%EC%84%A4%EB%AA%85)
> [2] [OSI 7 계층이란?](https://lxxyeon.tistory.com/155)
> [3] [OSI 7계층 상세 설명](https://shlee0882.tistory.com/110)
> [4] [네트워크 프로토콜](https://www.cloudflare.com/learning/network-layer/what-is-a-protocol/)

