<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>DNS</title>
</head>
<body>

<h1>DNS</h1>

<p>
  인터넷을 구성하는 IP 주소는 IPv4의 경우 192.168.0.1 같이 숫자로 구성된다.
  이런 숫자는 아무런 의미도 없기 때문에 외우기 힘들어 따라서 naver.com 같은 문자열로 서버 주소를 표현한다.
  다만 실제 컴퓨터 통신에서는 문자열 주소를 IPv4 주소로 변환해주는 서비스가 필요하다.
  이런 서비스를 DNS 서비스라고 한다.
</p>

<p>
  DNS(Domain Name System)은 문자열 주소를 IP 주소로 해석해주는 네트워크 서비스를 말한다.
  DNS 서버에는 도메인 주소와 IP 주소의 쌍(Pair)이 저장된다.
</p>

---
<h2>A 레코드와 CNAME</h2>

<p>
  DNS에 저장되는 정보의 타입에는 A 레코드와 CNAME이 있습니다.
</p>

<h3>A 레코드</h3>

<p>
  A 레코드(A Record)는 DNS에 저장되는 정보의 타입으로 도메인 주소와 서버의 IP 주소를 직접 매핑시키는 방법이다.
</p>

<p>
  <span style="color: pink;">장점</span> : 한번의 요청으로 찾아갈 서버의 IP 주소를 한번에 알 수 있다.
</p>

<p>
  <span style="color: pink;">단점</span> : IP 주소가 자주 바뀌는 환경에서는 조금 번거로울 수 있다.
</p>

<h3>CNAME</h3>

<p>
  CNAME은 Canonical Name의 약자로 도메인 주소를 또 다른 도메인 주소로 매핑 시키는 형태의 DNS 레코드 타입이다.
</p>

<p>
  <span style="color: pink;">장점</span> : IP 주소가 자주 변경되는 환경에서 유연하게 대응할 수 있다.
</p>

<p>
  <span style="color: pink;">단점</span> : A 레코드의 단점은 실제 IP 주소를 얻을 때까지 여러번 DNS 정보를 요청해야 한다는 점이다.
</p>

---

<h2>A 레코드 vs CNAME</h2>

<p>
  A 레코드와 CNAME은 각각 장단점이 있으므로, 상황에 맞게 적절하게 사용해야 합니다.
</p>

</body>
</html>

---


<h2><span style="color: brown;">결론</span></h2>
1. DNS는 인터넷에서 문자열 주소와 IP 주소를 매핑해주는 중요한 서비스이다.
2. A 레코드와 CNAME은 각각 장단점이 있으므로, 상황에 맞게 적절하게 사용해야 한다.
