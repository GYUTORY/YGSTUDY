# 📡 네트워크 프로토콜(Protocol) 개념 가이드

---

## 1. 개요 ✨

**프로토콜(Protocol)**은 **컴퓨터나 네트워크 장치가 서로 통신하기 위해 정한 규칙과 절차**를 의미합니다.  
네트워크 환경에서 **데이터를 효율적이고 안전하게 주고받기 위해 필수적인 요소**입니다.

> **🔹 프로토콜의 핵심 역할**
> - **데이터의 형식과 구조 정의**
> - **송수신 과정에서의 오류 처리**
> - **네트워크 장치 간의 원활한 상호작용 보장**

---

## 2. 프로토콜의 구성 요소

프로토콜은 일반적으로 **3가지 주요 요소**로 구성됩니다.

### **1️⃣ 구문(Syntax)**
👉🏻 **데이터 형식과 구조를 정의**합니다.  
예) 메시지 헤더, 패킷 구조, 데이터 길이 등

### **2️⃣ 의미론(Semantics)**
👉🏻 **데이터 해석 방식과 처리 방법을 정의**합니다.  
예) 오류 감지, 데이터 요청 & 응답 규칙

### **3️⃣ 타이밍(Timing)**
👉🏻 **데이터 전송의 속도 및 순서를 정의**합니다.  
예) 패킷 전송 속도 조절, 흐름 제어 (Flow Control)

---

## 3. 주요 프로토콜 종류 및 개념

### 3.1 네트워크 계층별 주요 프로토콜

OSI 7계층 모델을 기준으로 주요 프로토콜을 정리하면 다음과 같습니다.

| 계층 | 프로토콜 | 설명 |
|------|---------|------|
| 7. 응용(Application) | HTTP, FTP, SMTP | 웹 통신, 파일 전송, 이메일 |
| 6. 표현(Presentation) | SSL/TLS | 데이터 암호화 및 보안 |
| 5. 세션(Session) | NetBIOS, RPC | 세션 연결 및 유지 |
| 4. 전송(Transport) | TCP, UDP | 데이터 전송 및 흐름 제어 |
| 3. 네트워크(Network) | IP, ICMP | 라우팅 및 주소 지정 |
| 2. 데이터 링크(Data Link) | Ethernet, MAC | 물리적 주소 및 데이터 프레임 |
| 1. 물리(Physical) | Wi-Fi, Bluetooth | 실제 데이터 전송 |

---

## 4. 주요 프로토콜 설명 및 예제

### 4.1 HTTP (HyperText Transfer Protocol)

👉🏻 **웹 페이지를 주고받기 위한 프로토콜**입니다.  
클라이언트(브라우저)와 서버 간의 통신에서 사용됩니다.

```http
GET /index.html HTTP/1.1
Host: www.example.com
User-Agent: Mozilla/5.0
```

> 🔹 **설명**
> - `GET`: 클라이언트가 서버에서 데이터를 요청
> - `Host`: 요청 대상 서버
> - `User-Agent`: 클라이언트 정보

### 4.2 TCP (Transmission Control Protocol)

👉🏻 **데이터를 신뢰성 있게 전송하는 프로토콜**입니다.  
👉🏻 **데이터를 순서대로 정확하게 전달**합니다.

```python
import socket

# TCP 소켓 생성
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("localhost", 8080))  # IP, 포트 바인딩
server_socket.listen(1)  # 연결 대기

print("서버 대기 중...")
conn, addr = server_socket.accept()  # 클라이언트 연결 수락
print(f"{addr}에서 연결됨")

data = conn.recv(1024)  # 데이터 수신
print("받은 데이터:", data.decode())

conn.close()  # 연결 종료
```

> 🔹 **설명**
> - `socket.AF_INET`: IPv4 사용
> - `socket.SOCK_STREAM`: TCP 사용
> - `bind()`: IP, 포트 설정
> - `listen()`: 클라이언트 연결 대기

### 4.3 UDP (User Datagram Protocol)

👉🏻 **빠른 데이터 전송이 필요할 때 사용되는 프로토콜**  
👉🏻 **순서 보장 X, 신뢰성 낮음 (예: 실시간 스트리밍, 온라인 게임)**

```python
import socket

# UDP 소켓 생성
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = ("localhost", 8081)
message = "Hello, UDP!"

# 데이터 전송
udp_socket.sendto(message.encode(), server_address)
print("UDP 메시지 전송 완료")

udp_socket.close()
```

> 🔹 **설명**
> - `SOCK_DGRAM`: UDP 사용
> - `sendto()`: 연결 없이 메시지 전송

### 4.4 IP (Internet Protocol)

👉🏻 **네트워크에서 데이터를 목적지까지 전달하는 역할**  
👉🏻 **IP 주소를 기반으로 패킷을 라우팅**

```sh
# 현재 내 IP 확인 (Linux/Mac)
ifconfig

# 특정 도메인의 IP 주소 조회
nslookup google.com
```

> 🔹 **설명**
> - `ifconfig`: 네트워크 인터페이스 설정 확인
> - `nslookup`: 도메인의 IP 주소 조회

---

## 5. 프로토콜의 중요성

✅ **데이터가 올바르게 전달되도록 보장**  
✅ **서로 다른 기기 & 운영체제에서도 원활한 통신 가능**  
✅ **보안, 신뢰성, 속도 등을 조절할 수 있음**

