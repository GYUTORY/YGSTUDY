

# DNS

- 인터넷을 구성하는 IP 주소는 IPv4의 경우 192.168.0.1 같이 숫자로 구성된다. 
- 이런 숫자는 아무런 의미도 없기 때문에 외우기 힘들어 따라서 naver.com 같은 문자열로 서버 주소를 표현한다.
- 즉, 호스트의 도메인 이름을 IP 주소로 변환시켜주거나, 반대의 경우를 수행할 수 있도록 개발된 데이터베이스 시스템이다.


> 정리 : DNS(Domain Name System)은 문자열 주소를 IP 주소로 해석해주는 네트워크 서비스를 말하며, DNS 서버에는 도메인 주소와 IP 주소의 쌍(Pair)이 저장된다.

<div align="center">
    <img src="../../../etc/image/Network_image/Domain.png" alt="Domain" width="50%">
</div>

- 만약 사용자가 브라우저의 주소창에 도메인 이름(domain.com)을 입력하면, 이 요청은 DNS에서 IP 주소(216.3.128.12)를 찾는다.
- 그리고 이 IP 주소에 해당하는 웹 서버로 요청을 전달하여 클라이언트와 서버가 통신할 수 있도록 한다.

---
## A 레코드와 CNAME
- DNS에 저장되는 정보의 타입에는 A 레코드와 CNAME이 있습니다.


### A 레코드
- A 레코드(A Record)는 DNS에 저장되는 정보의 타입으로 도메인 주소와 서버의 IP 주소를 직접 매핑시키는 방법이다.


#### 장단점
- <span style="color: pink;">장점</span> : 한번의 요청으로 찾아갈 서버의 IP 주소를 한번에 알 수 있다.
- <span style="color: pink;">단점</span> : IP 주소가 자주 바뀌는 환경에서는 조금 번거로울 수 있다.


<br>

### CNAME
- CNAME은 Canonical Name의 약자로 도메인 주소를 또 다른 도메인 주소로 매핑 시키는 형태의 DNS 레코드 타입이다.


#### 장단점 
- <span style="color: pink;">장점</span> : IP 주소가 자주 변경되는 환경에서 유연하게 대응할 수 있다.
- <span style="color: pink;">단점</span> : A 레코드의 단점은 실제 IP 주소를 얻을 때까지 여러번 DNS 정보를 요청해야 한다는 점이다.


---


<h2><span style="color: brown;">결론</span></h2>
1. DNS는 인터넷에서 문자열 주소와 IP 주소를 매핑해주는 중요한 서비스이다.
2. A 레코드와 CNAME은 각각 장단점이 있으므로, 상황에 맞게 적절하게 사용해야 한다.
