# DNS Lookup

---

# 개념정리

#### DNS Lookup
- 도메인 이름과 IP 주소 간의 매핑 정보를 조회하는 과정입니다.
- 이 과정은 도메인 이름을 IP 주소로 변환하거나, IP 주소를 도메인 이름으로 변환하는데 사용됩니다.
- DNS Lookup은 다음과 같은 단계로 이루어집니다.

#### 1. Recursive DNS Lookup
- 클라이언트(예: 웹 브라우저)가 www.example.com과 같은 도메인 이름에 접근하려고 할 때, 먼저 로컬 DNS 리졸버에 질의를 보냅니다.
- 로컬 DNS 리졸버는 일반적으로 ISP(인터넷 서비스 제공업체)나 공개 DNS 서비스(예: Google DNS 8.8.8.8, Cloudflare 1.1.1.1)에서 제공합니다.
- 리졸버는 먼저 자신의 캐시를 확인합니다. 캐시는 TTL(Time To Live) 값에 따라 일정 시간 동안만 유효합니다.
- 캐시에 정보가 없거나 만료된 경우, 리졸버는 루트 DNS 서버에 질의를 시작합니다.

#### 2. Root DNS Servers
- 루트 DNS 서버는 전 세계에 13개의 루트 서버(A~M)가 있으며, 각각 여러 대의 물리적 서버로 구성된 Anycast 네트워크로 운영됩니다.
- 루트 서버의 IP 주소는 DNS 리졸버에 하드코딩되어 있습니다.
- 예를 들어, www.example.com에 대한 질의에서 루트 서버는 .com TLD 서버의 정보를 반환합니다.
- 루트 서버는 도메인 이름의 최상위 도메인(TLD)에 대한 정보만 가지고 있습니다.

#### 3. Top-Level Domain (TLD) DNS Servers
- TLD 서버는 .com, .net, .org, .kr 등과 같은 최상위 도메인을 관리합니다.
- 루트 서버로부터 받은 정보를 바탕으로, 리졸버는 해당 TLD 서버에 질의를 보냅니다.
- 예를 들어, .com TLD 서버는 example.com을 관리하는 권한 있는 DNS 서버의 정보를 반환합니다.
- TLD 서버는 도메인 등록 기관(Registry)에서 관리하며, 각 TLD마다 다른 기관이 관리합니다.

#### 4. Authoritative DNS Servers
- 권한 있는 DNS 서버는 실제 도메인을 소유한 조직이나 호스팅 서비스 제공업체가 운영합니다.
- TLD 서버로부터 받은 정보를 바탕으로, 리졸버는 권한 있는 DNS 서버에 질의를 보냅니다.
- 권한 있는 DNS 서버는 도메인에 대한 모든 DNS 레코드(A, AAAA, MX, CNAME 등)를 관리합니다.
- 예를 들어, www.example.com에 대한 A 레코드(IPv4 주소)나 AAAA 레코드(IPv6 주소)를 반환합니다.

#### 5. IP Address Resolution
- 권한 있는 DNS 서버는 요청된 도메인에 대한 IP 주소 정보를 리졸버에게 반환합니다.
- 리졸버는 이 정보를 자신의 캐시에 저장하고, TTL 값에 따라 일정 시간 동안 유지합니다.
- 리졸버는 최종적으로 클라이언트에게 IP 주소를 반환합니다.
- 클라이언트는 받은 IP 주소를 사용하여 웹 서버와의 TCP 연결을 시작하고 HTTP 요청을 보냅니다.

#### 추가 정보
- DNS 캐싱: 각 단계에서 정보를 캐싱하여 이후의 질의를 빠르게 처리할 수 있습니다.
- DNS 레코드 타입:
  - A: IPv4 주소
  - AAAA: IPv6 주소
  - CNAME: 별칭(Canonical Name)
  - MX: 메일 서버
  - NS: 네임 서버
  - TXT: 텍스트 정보
- DNS 보안: DNSSEC(DNS Security Extensions)를 통해 DNS 응답의 무결성을 보장합니다.
- DNS 오버 HTTPS(DoH)와 DNS 오버 TLS(DoT): DNS 질의를 암호화하여 프라이버시를 보호합니다.