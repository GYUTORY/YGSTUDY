---
title: SOAP
tags: [network, tcp, api, backend, http, security]
updated: 2026-09-07
---

# SOAP

## 메시지 구조

SOAP 메시지는 XML 문서 하나다. Envelope가 루트 엘리먼트이고, 그 안에 Header와 Body가 들어간다. Fault는 Body 안에 에러가 있을 때만 나타난다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:tns="http://example.com/payment">
  <soap:Header>
    <!-- 인증 토큰, 트랜잭션 ID 등 -->
  </soap:Header>
  <soap:Body>
    <!-- 실제 요청 또는 응답 데이터 -->
  </soap:Body>
</soap:Envelope>
```

### Envelope

네임스페이스 선언이 핵심이다. `http://schemas.xmlsoap.org/soap/envelope/`는 SOAP 1.1, `http://www.w3.org/2003/05/soap-envelope`는 SOAP 1.2다. 둘을 섞으면 서버가 요청을 거부한다.

실무에서 이 에러가 나오는 경우는 클라이언트 라이브러리가 1.1로 보내는데 서버가 1.2만 받을 때다. SOAPAction 헤더 유무로도 버전을 구분할 수 있다. SOAP 1.2에서는 SOAPAction이 `Content-Type` 헤더의 `action` 파라미터로 들어간다.

### Header

선택 요소지만 실무에서는 거의 항상 쓴다. WS-Security 토큰, 분산 트랜잭션 ID, 상관관계 ID 같은 메타데이터가 여기 들어간다. `mustUnderstand="1"` 속성을 붙이면 수신 측이 해당 헤더를 처리하지 못할 때 반드시 Fault를 돌려줘야 한다.

```xml
<soap:Header>
  <wsse:Security
      xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
      soap:mustUnderstand="1">
    <wsse:UsernameToken>
      <wsse:Username>user123</wsse:Username>
      <wsse:Password
          Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">
        hashed_password_value
      </wsse:Password>
      <wsse:Nonce>base64encoded_nonce</wsse:Nonce>
      <wsu:Created xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
        2026-09-07T10:00:00Z
      </wsu:Created>
    </wsse:UsernameToken>
  </wsse:Security>
</soap:Header>
```

`mustUnderstand`를 1로 세팅한 헤더를 서버가 인식하지 못하면 `soap:MustUnderstand` Fault가 온다. 서버 구현이 해당 WS-* 확장을 지원하는지 미리 확인해야 한다.

### Body

실제 요청과 응답 데이터가 들어간다. WSDL에 정의된 타입을 따른다.

```xml
<soap:Body>
  <tns:TransferRequest>
    <tns:fromAccount>1234-5678</tns:fromAccount>
    <tns:toAccount>9876-5432</tns:toAccount>
    <tns:amount>50000</tns:amount>
    <tns:currency>KRW</tns:currency>
  </tns:TransferRequest>
</soap:Body>
```

### Fault

Body 안에 들어가는 에러 응답이다. SOAP 1.1과 1.2가 구조가 다르다.

SOAP 1.1 Fault:

```xml
<soap:Body>
  <soap:Fault>
    <faultcode>soap:Client</faultcode>
    <faultstring>계좌번호가 올바르지 않습니다</faultstring>
    <detail>
      <tns:ErrorDetail>
        <tns:code>INVALID_ACCOUNT</tns:code>
        <tns:message>fromAccount not found</tns:message>
      </tns:ErrorDetail>
    </detail>
  </soap:Fault>
</soap:Body>
```

`faultcode`는 `soap:Client`(요청 문제), `soap:Server`(서버 내부 문제), `soap:VersionMismatch`(네임스페이스 버전 불일치), `soap:MustUnderstand`(헤더 처리 실패) 중 하나다.

SOAP 1.2에서는 구조가 달라진다. `faultcode` → `Code/Value`, `faultstring` → `Reason/Text`로 계층화됐고, 서브코드도 지정할 수 있다. 기존 SOAP 1.1 클라이언트로 1.2 서버를 붙이면 Fault 파싱이 실패하는 경우가 있다.

## HTTP POST 전송

SOAP은 항상 HTTP POST로 전송한다. GET은 쓰지 않는다. Content-Type은 `text/xml;charset=UTF-8` (SOAP 1.1) 또는 `application/soap+xml;charset=UTF-8` (SOAP 1.2)다.

```
POST /services/PaymentService HTTP/1.1
Host: api.example-bank.com
Content-Type: text/xml;charset=UTF-8
SOAPAction: "http://example-bank.com/payment/transfer"
Content-Length: 1024

<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope ...>
  ...
</soap:Envelope>
```

SOAPAction 헤더가 SOAP 1.1에서 필수다. 서버가 Body를 파싱하지 않고도 어떤 오퍼레이션인지 라우팅할 수 있게 해준다. WAF나 방화벽에서 이 헤더로 화이트리스트 필터링을 하는 경우가 있어서, SOAPAction 값이 WSDL에 정의된 것과 다르면 403이 나온다.

응답은 200 OK에 SOAP Envelope가 담겨 온다. 에러일 때도 Body에 Fault가 담겨 오는데, SOAP 1.1 서버는 HTTP 상태코드 규칙이 제각각이다. Fault 응답을 200으로 보내는 서버도 있고 500으로 보내는 서버도 있다. SOAP 1.2는 클라이언트 에러는 400, 서버 에러는 500을 쓰도록 정했다.

REST와 크게 다른 지점이 여기다. REST는 HTTP 상태코드가 의미를 가지지만, SOAP에서 HTTP는 그냥 운반 수단이고 에러 정보는 Fault 안에 있다.

## WSDL과의 관계

SOAP 자체는 메시지 형식 명세다. 어떤 오퍼레이션이 있는지, 파라미터가 뭔지는 WSDL에 따로 기술한다.

WSDL이 있으면 클라이언트 코드를 자동 생성할 수 있다. Java의 `wsimport`, .NET의 `svcutil`, Python의 `zeep`이 이를 지원한다.

```bash
# Java 클라이언트 코드 자동 생성
wsimport -d ./generated -s ./src http://api.example-bank.com/payment?wsdl

# Python zeep으로 동적 호출
python3 -c "
from zeep import Client
client = Client('http://api.example-bank.com/payment?wsdl')
result = client.service.transfer(fromAccount='1234', toAccount='5678', amount=50000)
print(result)
"
```

공공기관 API 중에 WSDL은 있는데 최신 상태로 관리가 안 되는 경우가 있다. WSDL에 없는 파라미터를 실제 서버가 요구하거나, WSDL에 있는 파라미터가 실제로는 무시되는 경우다. 이때는 실제 전송 메시지를 SoapUI로 캡처해서 따라가는 수밖에 없다.

## WS-* 확장

SOAP 코어 스펙은 메시지 구조만 정의한다. 보안, 신뢰성 전달, 주소 지정, 분산 트랜잭션은 WS-* 계열 확장 스펙이 담당한다.

### WS-Security

SOAP 메시지 자체에 보안을 적용한다. HTTP 계층 보안(TLS)과 별개로, 메시지 수준에서 암호화와 서명을 한다.

메시지가 중간 노드를 거쳐 전달될 때 TLS는 홉 단위로만 보호된다. WS-Security는 종단간 보호가 된다. 금융권에서 이 차이가 중요하다.

지원하는 인증 방식:
- UsernameToken: 아이디/패스워드 (다이제스트 또는 평문)
- X.509 Certificate: 디지털 인증서로 서명
- SAML Token: SSO 토큰 전달
- Kerberos Token: 윈도우 환경 인증

```xml
<wsse:Security xmlns:wsse="..." soap:mustUnderstand="1">
  <!-- 타임스탬프 — 재전송 공격 방지 -->
  <wsu:Timestamp xmlns:wsu="...">
    <wsu:Created>2026-09-07T10:00:00Z</wsu:Created>
    <wsu:Expires>2026-09-07T10:05:00Z</wsu:Expires>
  </wsu:Timestamp>
  <!-- X.509 서명 -->
  <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
    <ds:SignedInfo>
      <ds:CanonicalizationMethod Algorithm="..."/>
      <ds:SignatureMethod Algorithm="..."/>
      <ds:Reference URI="#body">
        <ds:DigestMethod Algorithm="..."/>
        <ds:DigestValue>base64digest</ds:DigestValue>
      </ds:Reference>
    </ds:SignedInfo>
    <ds:SignatureValue>base64signature</ds:SignatureValue>
  </ds:Signature>
</wsse:Security>
```

Timestamp 만료 시간을 5분으로 짧게 잡는 이유가 있다. 메시지를 가로채서 나중에 재전송하는 replay attack을 막기 위해서다. 서버와 클라이언트의 시스템 시각이 크게 차이 나면 유효한 요청인데도 만료 에러가 난다. NTP 동기화가 필수다.

### WS-ReliableMessaging

네트워크가 불안정한 환경에서 메시지 전달을 보장한다. 시퀀스 번호를 붙이고, 수신 확인을 받으며, 재전송한다.

```xml
<wsrm:Sequence xmlns:wsrm="http://schemas.xmlsoap.org/ws/2005/02/rm">
  <wsa:Identifier>urn:uuid:abc-123-def-456</wsa:Identifier>
  <wsrm:MessageNumber>1</wsrm:MessageNumber>
</wsrm:Sequence>
```

직접 구현하는 일은 거의 없다. Apache CXF, IBM MQ, TIBCO 같은 미들웨어가 처리한다. 금융권 레거시 ESB에서 주로 쓰인다.

### WS-Addressing

비동기 전송이나 중간 노드 라우팅에서 메시지 주소 지정을 표준화한다.

```xml
<soap:Header>
  <wsa:To xmlns:wsa="http://www.w3.org/2005/08/addressing">
    http://example.com/payment/service
  </wsa:To>
  <wsa:Action>http://example.com/payment/transfer</wsa:Action>
  <wsa:MessageID>urn:uuid:xyz-789</wsa:MessageID>
  <wsa:ReplyTo>
    <wsa:Address>http://client.example.com/callback</wsa:Address>
  </wsa:ReplyTo>
</soap:Header>
```

`ReplyTo`로 비동기 콜백 주소를 지정할 수 있다. 처리 시간이 긴 작업에서 요청을 보내고 결과를 나중에 콜백으로 받는 패턴에서 쓴다.

### WS-AtomicTransaction

분산 트랜잭션을 SOAP 레이어에서 지원한다. 여러 서비스에 걸친 2PC(2-Phase Commit)를 구현한다. 코디네이터가 각 참여자에게 준비(Prepare) 메시지를 보내고, 전원 OK면 커밋을 지시한다.

REST에는 이에 직접 대응하는 표준 프로토콜이 없다. Saga 패턴으로 비슷한 보장을 구현할 수 있지만, 보상 트랜잭션 로직을 직접 짜야 한다.

## 금융·공공 API에서 아직 SOAP을 쓰는 이유

새 프로젝트에서 SOAP을 선택하는 곳은 없다. 그런데 은행 API, 공공기관 연계, 결제 게이트웨이 일부는 SOAP이다.

**기존 시스템 교체 비용이 너무 크다.** 핵심 뱅킹 시스템은 10~20년 전에 구축됐다. SOAP 기반 ESB가 수백 개 내부 서비스를 연결하고 있다. REST로 바꾸려면 연계된 모든 시스템을 동시에 전환해야 하는데, 가동 중인 금융 시스템을 건드리는 건 극히 보수적이다.

**WS-Security의 메시지 레벨 보안이 규제 요건을 충족한다.** 금융보안원 기준 일부와 전자서명법 관련 요건이 SOAP WS-Security 방식으로 충족되도록 기술 규격이 작성됐다. REST+TLS+OAuth2로도 같은 보안 수준을 달성할 수 있지만, 규격서 자체가 SOAP 기준으로 쓰여 있어서 거기에 맞추는 게 심사 통과가 빠르다.

**공공기관의 표준 연계 규격이 SOAP이다.** 행정안전부 전자정부 연계 표준, 건강보험심사평가원 API, 국세청 전자세금계산서 연계 등이 SOAP이다. 이 기관들과 연계해야 하는 시스템은 선택의 여지 없이 SOAP을 써야 한다.

**분산 트랜잭션 요건이 있다.** 계좌이체는 원장 차감과 상대 계좌 증액이 원자적으로 일어나야 한다. SOAP 기반 시스템은 WS-AT로 이걸 프레임워크 수준에서 처리했다. REST 전환 시 Saga로 대체하면 보상 트랜잭션 설계가 추가된다.

## REST/gRPC 마이그레이션 시 걸리는 부분

기술 구현보다 이 부분들이 더 오래 걸렸다.

**WSDL에서 OpenAPI Spec으로 자동 변환이 안 된다.** 변환 도구가 있긴 한데 결과물을 그대로 쓸 수 없다. SOAP 오퍼레이션 이름(`getUserByAccountNumber`)이 REST 리소스 설계(`GET /accounts/{id}`)와 1:1로 매핑되지 않는다. 판단은 사람이 해야 한다.

**Fault → HTTP 상태코드 매핑이 모호하다.** `faultcode`가 `Client`라고 다 400이 아니다. 계좌 없음은 404, 잔액 부족은 422, 권한 없음은 403으로 분리해야 하는데, 기존 Fault detail을 보고 판단해야 한다. 클라이언트 팀과 합의가 필요하다.

**WS-Security → JWT/OAuth2 전환 시 인증 모델이 달라진다.** WS-Security는 메시지마다 서명이 붙어 개별 메시지를 독립적으로 검증할 수 있다. JWT는 토큰 유효기간 안에서 요청을 허용한다. 동일한 보안 수준이 아니라는 걸 보안 팀과 감사팀에 설명하는 데 시간이 걸린다.

**기존 클라이언트 코드가 HTTP 상태코드를 무시하는 구조다.** SOAP 클라이언트는 HTTP 상태코드와 관계없이 Body를 파싱해서 Fault 여부를 판단하는 구조로 만들어진 경우가 많다. REST 전환 후 상태코드가 실제로 의미를 가지기 시작하면 클라이언트 측 코드 변경이 필요하다.

**WS-AtomicTransaction은 REST에 직접 대응물이 없다.** Saga로 대체할 때 보상 트랜잭션 로직을 새로 짜야 한다. 기존에 2PC로 처리하던 것을 Saga로 바꾸면 실패 케이스가 훨씬 많아지고 테스트 케이스가 3~5배 늘어날 수 있다.

**gRPC 전환 시 중간 게이트웨이 문제가 있다.** 공공기관 연계는 방화벽이나 L7 장비가 HTTP/2를 지원하지 않는 경우가 있다. gRPC-Web이나 Envoy Proxy 같은 변환 계층을 두는 방식으로 해결하기도 한다. 상대 기관의 네트워크 인프라를 바꾸는 건 내가 결정할 수 없다.
