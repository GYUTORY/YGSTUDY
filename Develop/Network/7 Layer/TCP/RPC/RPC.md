
# RPC

## 개요
- RPC(원격 프로시저 호출)는 분산 시스템에서 프로그램 간 통신을 위한 프로토콜입니다.
- 이를 통해 클라이언트 애플리케이션은 서버에 있는 함수 또는 프로시저를 원격으로 호출하여 분산된 서비스나 컴포넌트를 사용할 수 있습니다.


## 내용

### RPC의 개념
- RPC는 컴퓨터 프로그램 간의 통신을 위해 사용되는 프로토콜입니다. 
- 클라이언트 애플리케이션은 로컬 프로시저를 호출하는 것처럼 RPC를 사용하여 원격 프로시저를 호출할 수 있습니다.
- 이를 통해 애플리케이션은 마치 로컬 함수를 호출하는 것처럼 분산된 서비스나 컴포넌트를 투명하게 사용할 수 있습니다.

### RPC의 작동 방식
#### 클라이언트 호출
-  클라이언트는 로컬 프로시저를 호출하는 것처럼 RPC 프레임워크를 사용하여 원격 프로시저를 호출합니다.

#### 매개 변수 전달
- 클라이언트는 호출과 함께 매개 변수를 전달합니다.
- 이 매개 변수는 원격 프로시저로 전달되어 실행됩니다.

#### 원격 호출
- 클라이언트가 원격 프로시저를 호출하면, 해당 호출은 네트워크를 통해 서버로 전달됩니다.

#### 서버 실행
- 서버는 받은 호출을 처리하고 원격 프로시저를 실행합니다.

#### 응답 반환
- 서버는 실행 결과를 클라이언트로 반환하며, 클라이언트는 이 응답을 받아 원하는 작업을 수행합니다.

### RPC의 주요 구성 요소
#### 인터페이스 정의
- RPC 프로세스 간에 통신을 위한 프로시저 인터페이스를 정의합니다. 
- 주로 IDL(Interface Definition Language)을 사용하여 인터페이스를 명세화합니다.

#### 클라이언트 스텁(Client Stub)
- 클라이언트 애플리케이션이 로컬 프로시저를 호출하는 인터페이스입니다.
- 클라이언트 스텁은 호출을 패킹하여 서버로 전송합니다.

#### 서버 스텁(Server Stub)
- 서버에서 클라이언트로부터 받은 호출을 처리하는 인터페이스입니다. 
- 서버 스텁은 받은 호출을 언패킹하고 원격 프로시저를 실행합니다.

#### 시리얼라이저(Serializer)
- 매개 변수와 결과를 직렬화하여 네트워크를 통해 전송 가능한 형식으로 변환합니다.

#### 트랜스포터(Transporter)
- 클라이언트와 서버 간의 실제 통신을 처리하는 계층입니다.
- 주로 TCP/IP, HTTP, gRPC 등의 프로토콜을 사용합니다.

### RPC의 장점
#### 모듈성과 재사용성
- RPC는 프로시저 단위로 기능을 모듈화하여 개발할 수 있으며, 다른 애플리케이션에서 재사용할 수 있습니다.

#### 투명성
- RPC를 사용하면 원격 호출을 로컬 호출처럼 투명하게 처리할 수 있습니다. 
- 클라이언트는 원격 프로시저를 호출함으로써 내부 동작을 알 필요가 없습니다.

#### 분산 시스템 관리
- RPC는 분산 시스템에서 서비스 및 컴포넌트를 통합하고 관리하는 데 유용합니다.

#### 다양한 언어 및 플랫폼 지원
- 다양한 프로그래밍 언어와 플랫폼에서 RPC를 지원하므로, 다양한 애플리케이션 간에 통신할 수 있습니다.

### RPC의 사용 사례:
#### 마이크로서비스 아키텍처
- RPC는 마이크로서비스 아키텍처에서 각 서비스 간의 통신에 사용됩니다.

#### 원격 데이터 접근
- 분산 데이터베이스나 원격 서비스에 대한 데이터 접근을 위해 RPC가 사용됩니다.

#### 원격 프로시저 호출
- 원격 서버에서 실행되는 프로시저를 호출하기 위해 RPC를 사용할 수 있습니다.

## 결론
- RPC는 분산 시스템에서 프로그램 간 통신을 위한 프로토콜로, 클라이언트는 원격 프로시저를 호출하여 분산된 서비스나 컴포넌트를 사용할 수 있습니다.
- RPC는 모듈성과 재사용성을 강화하며, 분산 시스템 관리와 다양한 언어 및 플랫폼 간의 통신을 용이하게 합니다.
- 마이크로서비스 아키텍처와 원격 데이터 접근 등 다양한 사용 사례에서 RPC가 활용됩니다.

