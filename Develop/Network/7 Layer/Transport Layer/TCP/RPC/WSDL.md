---
title: WSDL Web Services Description Language
tags: [network, 7-layer, transport-layer, tcp, rpc, wsdl, soap, web-services]
updated: 2025-12-22
---

# WSDL (Web Services Description Language)

## 개요

WSDL은 Web Services Description Language의 약자로, 웹 서비스의 인터페이스를 XML 형식으로 기술하는 언어다. SOAP 웹 서비스가 제공하는 기능, 메서드, 데이터 타입, 통신 프로토콜을 명확하게 정의한다.

### WSDL의 목적

WSDL은 웹 서비스의 계약서 역할을 한다. 클라이언트는 WSDL 파일을 읽어 서버가 제공하는 기능을 파악하고, 자동으로 클라이언트 코드를 생성할 수 있다.

**실무 팁:**
WSDL 파일을 받으면 해당 서비스의 모든 기능을 파악할 수 있다. SOAP 클라이언트 라이브러리는 WSDL을 파싱하여 자동으로 클라이언트 코드를 생성한다.

## WSDL의 기본 구조

### WSDL 문서 구성 요소

WSDL 문서는 다음 6가지 주요 섹션으로 구성된다:

1. **types**: 데이터 타입 정의 (XML Schema 사용)
2. **message**: 메시지 구조 정의
3. **portType**: 서비스가 제공하는 작업(operation) 정의
4. **binding**: 포트 타입을 실제 프로토콜로 바인딩
5. **port**: 바인딩과 네트워크 주소 연결
6. **service**: 관련된 포트들의 집합

### WSDL 네임스페이스

```xml
<definitions 
    xmlns="http://schemas.xmlsoap.org/wsdl/"
    xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
    xmlns:tns="http://example.com/wsdl/UserService"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    targetNamespace="http://example.com/wsdl/UserService"
    name="UserService">
```

**주요 네임스페이스:**
- `http://schemas.xmlsoap.org/wsdl/`: WSDL 기본 네임스페이스
- `http://schemas.xmlsoap.org/wsdl/soap/`: SOAP 바인딩 네임스페이스
- `http://www.w3.org/2001/XMLSchema`: XML Schema 네임스페이스
- `targetNamespace`: 이 WSDL 문서의 고유 식별자

**실무 팁:**
네임스페이스는 충돌을 방지하기 위해 도메인 기반으로 작성한다. `targetNamespace`는 서비스의 고유 식별자로 사용된다.

## WSDL 섹션 상세 설명

### 1. types 섹션

데이터 타입을 XML Schema로 정의한다.

```xml
<types>
    <xsd:schema 
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        targetNamespace="http://example.com/wsdl/UserService">
        
        <!-- 사용자 정보 타입 -->
        <xsd:complexType name="User">
            <xsd:sequence>
                <xsd:element name="id" type="xsd:int"/>
                <xsd:element name="name" type="xsd:string"/>
                <xsd:element name="email" type="xsd:string"/>
                <xsd:element name="age" type="xsd:int" minOccurs="0"/>
            </xsd:sequence>
        </xsd:complexType>
        
        <!-- 사용자 생성 요청 -->
        <xsd:element name="CreateUserRequest">
            <xsd:complexType>
                <xsd:sequence>
                    <xsd:element name="name" type="xsd:string"/>
                    <xsd:element name="email" type="xsd:string"/>
                    <xsd:element name="age" type="xsd:int" minOccurs="0"/>
                </xsd:sequence>
            </xsd:complexType>
        </xsd:element>
        
        <!-- 사용자 생성 응답 -->
        <xsd:element name="CreateUserResponse">
            <xsd:complexType>
                <xsd:sequence>
                    <xsd:element name="user" type="tns:User"/>
                    <xsd:element name="success" type="xsd:boolean"/>
                </xsd:sequence>
            </xsd:complexType>
        </xsd:element>
        
        <!-- 사용자 조회 요청 -->
        <xsd:element name="GetUserRequest">
            <xsd:complexType>
                <xsd:sequence>
                    <xsd:element name="userId" type="xsd:int"/>
                </xsd:sequence>
            </xsd:complexType>
        </xsd:element>
        
        <!-- 사용자 조회 응답 -->
        <xsd:element name="GetUserResponse">
            <xsd:complexType>
                <xsd:sequence>
                    <xsd:element name="user" type="tns:User" minOccurs="0"/>
                </xsd:sequence>
            </xsd:complexType>
        </xsd:element>
        
        <!-- 에러 정보 -->
        <xsd:complexType name="Error">
            <xsd:sequence>
                <xsd:element name="code" type="xsd:string"/>
                <xsd:element name="message" type="xsd:string"/>
            </xsd:sequence>
        </xsd:complexType>
    </xsd:schema>
</types>
```

**실무 팁:**
`minOccurs="0"`은 선택적 필드를 의미한다. 기본값은 1이다. `maxOccurs="unbounded"`는 배열을 의미한다.

### 2. message 섹션

요청과 응답 메시지의 구조를 정의한다.

```xml
<message name="CreateUserRequest">
    <part name="body" element="tns:CreateUserRequest"/>
</message>

<message name="CreateUserResponse">
    <part name="body" element="tns:CreateUserResponse"/>
</message>

<message name="GetUserRequest">
    <part name="body" element="tns:GetUserRequest"/>
</message>

<message name="GetUserResponse">
    <part name="body" element="tns:GetUserResponse"/>
</message>

<message name="Fault">
    <part name="fault" element="tns:Error"/>
</message>
```

**실무 팁:**
WSDL 2.0에서는 message 섹션이 제거되고 types에서 직접 참조한다. 대부분의 실무에서는 WSDL 1.1을 사용한다.

### 3. portType 섹션

서비스가 제공하는 작업(operation)을 정의한다.

```xml
<portType name="UserServicePortType">
    <!-- 사용자 생성 작업 -->
    <operation name="createUser">
        <input message="tns:CreateUserRequest"/>
        <output message="tns:CreateUserResponse"/>
        <fault name="UserFault" message="tns:Fault"/>
    </operation>
    
    <!-- 사용자 조회 작업 -->
    <operation name="getUser">
        <input message="tns:GetUserRequest"/>
        <output message="tns:GetUserResponse"/>
        <fault name="UserFault" message="tns:Fault"/>
    </operation>
    
    <!-- 사용자 목록 조회 작업 -->
    <operation name="getUsers">
        <input message="tns:GetUsersRequest"/>
        <output message="tns:GetUsersResponse"/>
    </operation>
</portType>
```

**작업 패턴:**
- **Request-Response**: 입력과 출력이 모두 있는 일반적인 패턴
- **One-Way**: 입력만 있고 출력이 없는 패턴 (알림 등)
- **Solicit-Response**: 서버가 먼저 요청하는 패턴 (거의 사용 안 함)
- **Notification**: 출력만 있는 패턴 (거의 사용 안 함)

**실무 팁:**
대부분의 경우 Request-Response 패턴을 사용한다. One-Way는 비동기 알림에 사용한다.

### 4. binding 섹션

포트 타입을 실제 프로토콜(SOAP, HTTP 등)로 바인딩한다.

```xml
<binding name="UserServiceBinding" type="tns:UserServicePortType">
    <soap:binding 
        style="document" 
        transport="http://schemas.xmlsoap.org/soap/http"/>
    
    <!-- createUser 작업 바인딩 -->
    <operation name="createUser">
        <soap:operation 
            soapAction="http://example.com/wsdl/UserService/createUser"/>
        <input>
            <soap:body use="literal"/>
        </input>
        <output>
            <soap:body use="literal"/>
        </output>
        <fault name="UserFault">
            <soap:fault name="UserFault" use="literal"/>
        </fault>
    </operation>
    
    <!-- getUser 작업 바인딩 -->
    <operation name="getUser">
        <soap:operation 
            soapAction="http://example.com/wsdl/UserService/getUser"/>
        <input>
            <soap:body use="literal"/>
        </input>
        <output>
            <soap:body use="literal"/>
        </output>
        <fault name="UserFault">
            <soap:fault name="UserFault" use="literal"/>
        </fault>
    </operation>
</binding>
```

**바인딩 스타일:**
- **document/literal**: XML 문서를 그대로 전송 (권장)
- **rpc/literal**: RPC 스타일로 메서드 호출 형식
- **document/encoded**: SOAP 인코딩 사용 (구식, 권장 안 함)
- **rpc/encoded**: RPC + 인코딩 (구식, 권장 안 함)

**실무 팁:**
`document/literal` 스타일을 사용한다. `rpc/encoded`는 하위 호환성 문제가 있어 사용하지 않는다.

### 5. port 섹션

바인딩과 실제 네트워크 주소를 연결한다.

```xml
<port name="UserServicePort" binding="tns:UserServiceBinding">
    <soap:address location="http://example.com/services/UserService"/>
</port>
```

**실무 팁:**
프로덕션 환경에서는 HTTPS를 사용한다. `location` 속성에 실제 서비스 URL을 지정한다.

### 6. service 섹션

관련된 포트들의 집합을 정의한다.

```xml
<service name="UserService">
    <port name="UserServicePort" binding="tns:UserServiceBinding">
        <soap:address location="http://example.com/services/UserService"/>
    </port>
</service>
</definitions>
```

## 완전한 WSDL 예제

```xml
<?xml version="1.0" encoding="UTF-8"?>
<definitions 
    xmlns="http://schemas.xmlsoap.org/wsdl/"
    xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
    xmlns:tns="http://example.com/wsdl/UserService"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    targetNamespace="http://example.com/wsdl/UserService"
    name="UserService">

    <!-- 타입 정의 -->
    <types>
        <xsd:schema 
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            targetNamespace="http://example.com/wsdl/UserService">
            
            <xsd:complexType name="User">
                <xsd:sequence>
                    <xsd:element name="id" type="xsd:int"/>
                    <xsd:element name="name" type="xsd:string"/>
                    <xsd:element name="email" type="xsd:string"/>
                    <xsd:element name="age" type="xsd:int" minOccurs="0"/>
                </xsd:sequence>
            </xsd:complexType>
            
            <xsd:element name="CreateUserRequest">
                <xsd:complexType>
                    <xsd:sequence>
                        <xsd:element name="name" type="xsd:string"/>
                        <xsd:element name="email" type="xsd:string"/>
                        <xsd:element name="age" type="xsd:int" minOccurs="0"/>
                    </xsd:sequence>
                </xsd:complexType>
            </xsd:element>
            
            <xsd:element name="CreateUserResponse">
                <xsd:complexType>
                    <xsd:sequence>
                        <xsd:element name="user" type="tns:User"/>
                        <xsd:element name="success" type="xsd:boolean"/>
                    </xsd:sequence>
                </xsd:complexType>
            </xsd:element>
            
            <xsd:element name="GetUserRequest">
                <xsd:complexType>
                    <xsd:sequence>
                        <xsd:element name="userId" type="xsd:int"/>
                    </xsd:sequence>
                </xsd:complexType>
            </xsd:element>
            
            <xsd:element name="GetUserResponse">
                <xsd:complexType>
                    <xsd:sequence>
                        <xsd:element name="user" type="tns:User" minOccurs="0"/>
                    </xsd:sequence>
                </xsd:complexType>
            </xsd:element>
        </xsd:schema>
    </types>

    <!-- 메시지 정의 -->
    <message name="CreateUserRequest">
        <part name="body" element="tns:CreateUserRequest"/>
    </message>
    
    <message name="CreateUserResponse">
        <part name="body" element="tns:CreateUserResponse"/>
    </message>
    
    <message name="GetUserRequest">
        <part name="body" element="tns:GetUserRequest"/>
    </message>
    
    <message name="GetUserResponse">
        <part name="body" element="tns:GetUserResponse"/>
    </message>

    <!-- 포트 타입 정의 -->
    <portType name="UserServicePortType">
        <operation name="createUser">
            <input message="tns:CreateUserRequest"/>
            <output message="tns:CreateUserResponse"/>
        </operation>
        
        <operation name="getUser">
            <input message="tns:GetUserRequest"/>
            <output message="tns:GetUserResponse"/>
        </operation>
    </portType>

    <!-- 바인딩 정의 -->
    <binding name="UserServiceBinding" type="tns:UserServicePortType">
        <soap:binding 
            style="document" 
            transport="http://schemas.xmlsoap.org/soap/http"/>
        
        <operation name="createUser">
            <soap:operation 
                soapAction="http://example.com/wsdl/UserService/createUser"/>
            <input>
                <soap:body use="literal"/>
            </input>
            <output>
                <soap:body use="literal"/>
            </output>
        </operation>
        
        <operation name="getUser">
            <soap:operation 
                soapAction="http://example.com/wsdl/UserService/getUser"/>
            <input>
                <soap:body use="literal"/>
            </input>
            <output>
                <soap:body use="literal"/>
            </output>
        </operation>
    </binding>

    <!-- 서비스 정의 -->
    <service name="UserService">
        <port name="UserServicePort" binding="tns:UserServiceBinding">
            <soap:address location="http://example.com/services/UserService"/>
        </port>
    </service>
</definitions>
```

## WSDL과 SOAP의 관계

### SOAP란?

SOAP(Simple Object Access Protocol)는 XML 기반 메시지 프로토콜이다. WSDL은 SOAP 서비스를 설명하는 문서다.

**관계:**
- WSDL: 서비스의 인터페이스를 정의하는 문서
- SOAP: 실제 통신에 사용되는 프로토콜
- WSDL 없이 SOAP 사용 가능하지만, WSDL이 있으면 자동 코드 생성 가능

### SOAP 메시지 구조

WSDL로 정의된 서비스를 호출할 때 전송되는 SOAP 메시지 예시:

**요청 메시지:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope 
    xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:ns="http://example.com/wsdl/UserService">
    <soap:Header>
        <!-- 인증 정보 등 -->
    </soap:Header>
    <soap:Body>
        <ns:CreateUserRequest>
            <ns:name>홍길동</ns:name>
            <ns:email>hong@example.com</ns:email>
            <ns:age>30</ns:age>
        </ns:CreateUserRequest>
    </soap:Body>
</soap:Envelope>
```

**응답 메시지:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope 
    xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:ns="http://example.com/wsdl/UserService">
    <soap:Body>
        <ns:CreateUserResponse>
            <ns:user>
                <ns:id>123</ns:id>
                <ns:name>홍길동</ns:name>
                <ns:email>hong@example.com</ns:email>
                <ns:age>30</ns:age>
            </ns:user>
            <ns:success>true</ns:success>
        </ns:CreateUserResponse>
    </soap:Body>
</soap:Envelope>
```

**실무 팁:**
SOAP 메시지는 항상 Envelope로 감싸진다. Header는 선택적이고, Body는 필수다.

## WSDL 버전

### WSDL 1.1

가장 널리 사용되는 버전이다.

**특징:**
- 2001년 W3C Note로 발표
- message 섹션 사용
- SOAP 바인딩 지원
- HTTP, SMTP 등 다양한 전송 프로토콜 지원

**실무 팁:**
대부분의 기존 시스템은 WSDL 1.1을 사용한다. 새로운 프로젝트도 호환성을 위해 1.1을 사용하는 경우가 많다.

### WSDL 2.0

2007년 W3C 권고안으로 발표되었다.

**주요 변경사항:**
- message 섹션 제거, types에서 직접 참조
- interface로 portType 대체
- HTTP 바인딩 개선
- 더 명확한 네임스페이스 처리

**WSDL 1.1 vs 2.0 비교:**

| 항목 | WSDL 1.1 | WSDL 2.0 |
|------|----------|----------|
| message 섹션 | 있음 | 없음 (types에서 직접 참조) |
| portType | 있음 | interface로 변경 |
| 네임스페이스 | 복잡 | 단순화 |
| HTTP 바인딩 | 제한적 | 개선됨 |
| 사용률 | 높음 | 낮음 |

**실무 팁:**
WSDL 2.0은 아직 널리 사용되지 않는다. 대부분의 도구와 라이브러리는 WSDL 1.1을 지원한다.

## WSDL 사용 시나리오

### 1. 서버에서 WSDL 생성

Java에서 JAX-WS를 사용한 예시:

```java
package com.example.service;

import javax.jws.WebService;
import javax.jws.WebMethod;
import javax.jws.WebParam;

@WebService(
    targetNamespace = "http://example.com/wsdl/UserService",
    serviceName = "UserService"
)
public class UserService {
    
    @WebMethod
    public User createUser(
        @WebParam(name = "name") String name,
        @WebParam(name = "email") String email,
        @WebParam(name = "age") Integer age
    ) {
        // 사용자 생성 로직
        User user = new User();
        user.setId(123);
        user.setName(name);
        user.setEmail(email);
        user.setAge(age);
        return user;
    }
    
    @WebMethod
    public User getUser(@WebParam(name = "userId") Integer userId) {
        // 사용자 조회 로직
        return userRepository.findById(userId);
    }
}
```

서버 실행 시 자동으로 WSDL이 생성된다:
- `http://localhost:8080/services/UserService?wsdl`

**실무 팁:**
JAX-WS는 어노테이션을 기반으로 WSDL을 자동 생성한다. 수동으로 작성할 필요가 없다.

### 2. 클라이언트에서 WSDL 사용

Node.js에서 `soap` 라이브러리를 사용한 예시:

```javascript
const soap = require('soap');
const url = 'http://example.com/services/UserService?wsdl';

// WSDL에서 클라이언트 자동 생성
soap.createClient(url, (err, client) => {
    if (err) {
        console.error('클라이언트 생성 실패:', err);
        return;
    }
    
    // createUser 메서드 호출
    client.createUser({
        name: '홍길동',
        email: 'hong@example.com',
        age: 30
    }, (err, result) => {
        if (err) {
            console.error('요청 실패:', err);
            return;
        }
        console.log('사용자 생성 성공:', result);
    });
    
    // getUser 메서드 호출
    client.getUser({ userId: 123 }, (err, result) => {
        if (err) {
            console.error('요청 실패:', err);
            return;
        }
        console.log('사용자 정보:', result);
    });
});
```

**실무 팁:**
WSDL을 파싱하면 클라이언트 코드를 자동으로 생성할 수 있다. 수동으로 SOAP 메시지를 작성할 필요가 없다.

### 3. Java에서 WSDL로 클라이언트 생성

```bash
# wsimport 도구로 클라이언트 코드 생성
wsimport -d ./generated -s ./src http://example.com/services/UserService?wsdl
```

생성된 코드 사용:

```java
import com.example.wsdl.UserService;
import com.example.wsdl.UserServicePortType;
import com.example.wsdl.User;

public class Client {
    public static void main(String[] args) {
        UserService service = new UserService();
        UserServicePortType port = service.getUserServicePort();
        
        // createUser 호출
        User user = port.createUser("홍길동", "hong@example.com", 30);
        System.out.println("생성된 사용자 ID: " + user.getId());
        
        // getUser 호출
        User foundUser = port.getUser(123);
        System.out.println("사용자 이름: " + foundUser.getName());
    }
}
```

**실무 팁:**
`wsimport`는 WSDL에서 Java 클라이언트 코드를 자동 생성한다. 수동으로 SOAP 메시지를 작성할 필요가 없다.

## WSDL 문서화 및 주석

### 주석 추가

```xml
<definitions>
    <!--
        사용자 관리 서비스
        제공 기능:
        - 사용자 생성
        - 사용자 조회
        - 사용자 목록 조회
    -->
    
    <types>
        <!-- 사용자 정보 타입 -->
        <xsd:complexType name="User">
            <!-- 사용자 고유 ID -->
            <xsd:element name="id" type="xsd:int"/>
            <!-- 사용자 이름 -->
            <xsd:element name="name" type="xsd:string"/>
        </xsd:complexType>
    </types>
    
    <portType name="UserServicePortType">
        <!--
            사용자 생성 작업
            입력: 사용자 정보 (이름, 이메일, 나이)
            출력: 생성된 사용자 정보
        -->
        <operation name="createUser">
            <input message="tns:CreateUserRequest"/>
            <output message="tns:CreateUserResponse"/>
        </operation>
    </portType>
</definitions>
```

**실무 팁:**
WSDL에 주석을 추가하면 다른 개발자가 이해하기 쉽다. 특히 복잡한 타입이나 비즈니스 로직이 있는 경우 주석이 중요하다.

## WSDL 검증 및 테스트

### WSDL 유효성 검사

```bash
# 온라인 WSDL 검증 도구 사용
# 또는 Java wsimport로 검증
wsimport -Xnocompile http://example.com/services/UserService?wsdl
```

**일반적인 오류:**
- 네임스페이스 불일치
- 타입 정의 오류
- 바인딩 설정 오류
- 포트 주소 오류

**실무 팁:**
WSDL을 배포하기 전에 반드시 검증한다. 잘못된 WSDL은 클라이언트 코드 생성 실패를 유발한다.

### SOAP UI로 테스트

SOAP UI는 WSDL을 로드하여 서비스를 테스트할 수 있는 도구다.

**사용 방법:**
1. SOAP UI 실행
2. New SOAP Project 생성
3. WSDL URL 입력
4. 자동으로 작업 목록 생성
5. 각 작업에 대해 요청/응답 테스트

**실무 팁:**
SOAP UI는 WSDL 기반 서비스를 테스트하는 표준 도구다. 개발 중에 자주 사용한다.

## 실무에서의 주의사항

### 1. 네임스페이스 관리

**문제:**
네임스페이스가 일치하지 않으면 클라이언트가 서비스를 호출할 수 없다.

**해결:**
```xml
<!-- 모든 네임스페이스가 일관되게 사용되도록 주의 -->
<definitions 
    targetNamespace="http://example.com/wsdl/UserService"
    xmlns:tns="http://example.com/wsdl/UserService">
    
    <types>
        <xsd:schema 
            targetNamespace="http://example.com/wsdl/UserService">
            <!-- 타입 정의 -->
        </xsd:schema>
    </types>
</definitions>
```

**실무 팁:**
네임스페이스는 도메인 기반으로 작성하고, 모든 섹션에서 일관되게 사용한다.

### 2. 버전 관리

**문제:**
서비스 변경 시 기존 클라이언트가 동작하지 않을 수 있다.

**해결:**
- 새로운 버전의 서비스는 별도 네임스페이스 사용
- 기존 서비스는 유지 (deprecated 표시)
- 점진적 마이그레이션 지원

```xml
<!-- 버전 1 -->
<definitions 
    targetNamespace="http://example.com/wsdl/UserService/v1">

<!-- 버전 2 -->
<definitions 
    targetNamespace="http://example.com/wsdl/UserService/v2">
```

**실무 팁:**
서비스 변경 시 기존 클라이언트 호환성을 고려한다. 큰 변경은 새 버전으로 배포한다.

### 3. 성능 고려사항

**문제:**
WSDL 파일이 크면 파싱 시간이 오래 걸린다.

**해결:**
- 불필요한 타입 정의 제거
- 타입 재사용
- WSDL 파일 분리 (import 사용)

```xml
<!-- 외부 스키마 import -->
<types>
    <xsd:schema>
        <xsd:import 
            namespace="http://example.com/common"
            schemaLocation="http://example.com/common.xsd"/>
    </xsd:schema>
</types>
```

**실무 팁:**
공통 타입은 별도 스키마 파일로 분리하고 import로 참조한다. WSDL 파일 크기를 줄일 수 있다.

### 4. 보안 고려사항

**문제:**
WSDL 파일에 민감한 정보가 포함될 수 있다.

**해결:**
- 인증 정보는 WSDL에 포함하지 않음
- HTTPS 사용
- WSDL 접근 제한

**실무 팁:**
WSDL은 공개 정보만 포함한다. 인증은 SOAP Header나 별도 메커니즘으로 처리한다.

## WSDL vs REST API 비교

| 항목 | WSDL/SOAP | REST API |
|------|-----------|----------|
| 데이터 형식 | XML | JSON, XML 등 |
| 계약 정의 | WSDL 파일 필요 | OpenAPI/Swagger (선택) |
| 자동 코드 생성 | 지원 | 제한적 |
| 메시지 크기 | 큼 (XML 오버헤드) | 작음 (JSON) |
| 복잡도 | 높음 | 낮음 |
| 브라우저 지원 | 제한적 | 완전 지원 |
| 트랜잭션 | WS-Transaction 지원 | 제한적 |
| 보안 | WS-Security | HTTPS + OAuth 등 |

**실무 팁:**
새로운 프로젝트는 REST API를 선호한다. 기존 SOAP 서비스와 통신해야 하는 경우에만 WSDL을 사용한다.

## WSDL 2.0 예제

WSDL 2.0의 주요 변경사항:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<description 
    xmlns="http://www.w3.org/ns/wsdl"
    xmlns:tns="http://example.com/wsdl/UserService"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    targetNamespace="http://example.com/wsdl/UserService">

    <!-- 타입 정의 (message 섹션 없음) -->
    <types>
        <xsd:schema 
            targetNamespace="http://example.com/wsdl/UserService">
            <xsd:element name="CreateUserRequest" type="tns:CreateUserType"/>
            <xsd:element name="CreateUserResponse" type="tns:UserType"/>
            
            <xsd:complexType name="CreateUserType">
                <xsd:sequence>
                    <xsd:element name="name" type="xsd:string"/>
                    <xsd:element name="email" type="xsd:string"/>
                </xsd:sequence>
            </xsd:complexType>
            
            <xsd:complexType name="UserType">
                <xsd:sequence>
                    <xsd:element name="id" type="xsd:int"/>
                    <xsd:element name="name" type="xsd:string"/>
                    <xsd:element name="email" type="xsd:string"/>
                </xsd:sequence>
            </xsd:complexType>
        </xsd:schema>
    </types>

    <!-- Interface (portType 대체) -->
    <interface name="UserServiceInterface">
        <operation name="createUser" pattern="http://www.w3.org/ns/wsdl/in-out">
            <input element="tns:CreateUserRequest"/>
            <output element="tns:CreateUserResponse"/>
        </operation>
    </interface>

    <!-- 바인딩 -->
    <binding name="UserServiceSOAPBinding" 
             type="tns:UserServiceInterface" 
             interface="tns:UserServiceInterface">
        <soap:binding 
            xmlns:soap="http://www.w3.org/ns/wsdl/soap"
            style="document"
            protocol="http://www.w3.org/2003/05/soap/bindings/HTTP/"/>
        
        <operation ref="tns:createUser">
            <soap:operation 
                soapAction="http://example.com/wsdl/UserService/createUser"/>
        </operation>
    </binding>

    <!-- 서비스 -->
    <service name="UserService" interface="tns:UserServiceInterface">
        <endpoint 
            name="UserServiceEndpoint" 
            binding="tns:UserServiceSOAPBinding"
            address="http://example.com/services/UserService"/>
    </service>
</description>
```

**주요 차이점:**
- `definitions` → `description`
- `portType` → `interface`
- `message` 섹션 제거
- `port` → `endpoint`

**실무 팁:**
WSDL 2.0은 아직 널리 사용되지 않는다. 대부분의 도구는 WSDL 1.1을 지원한다.

## 요약

WSDL은 SOAP 웹 서비스를 기술하는 XML 기반 언어다. 서비스의 인터페이스, 데이터 타입, 통신 프로토콜을 명확하게 정의하여 클라이언트가 자동으로 코드를 생성할 수 있게 한다.

### 주요 내용

- **구조**: types, message, portType, binding, port, service
- **버전**: WSDL 1.1 (널리 사용), WSDL 2.0 (제한적)
- **용도**: SOAP 웹 서비스 계약 정의
- **자동 코드 생성**: 클라이언트 라이브러리가 WSDL을 파싱하여 코드 생성

### 사용 시나리오

- 기존 SOAP 서비스와 통신해야 하는 경우
- 엔터프라이즈 시스템 간 통신
- 트랜잭션 지원이 필요한 경우
- 강력한 타입 검증이 필요한 경우

**실무 팁:**
새로운 프로젝트는 REST API를 선호한다. 기존 SOAP 서비스와 통신해야 하는 경우에만 WSDL을 사용한다.


