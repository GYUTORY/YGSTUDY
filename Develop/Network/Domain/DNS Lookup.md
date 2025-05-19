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

##### 상세 설명
1. **로컬 DNS 캐시 확인**
   - 운영체제의 hosts 파일 확인 (/etc/hosts 또는 C:\Windows\System32\drivers\etc\hosts)
   - 브라우저의 DNS 캐시 확인
   - 로컬 DNS 리졸버의 캐시 확인

2. **DNS 리졸버의 동작 방식**
   - 재귀적(Recursive) 질의: 클라이언트를 대신하여 전체 DNS 조회 과정을 수행
   - 반복적(Iterative) 질의: 각 DNS 서버가 다음 단계의 서버 정보만 제공
   - 일반적으로 ISP의 DNS 서버는 재귀적 질의를 지원

3. **실제 예시**
   ```
   클라이언트 -> ISP DNS 서버(8.8.8.8)
   ISP DNS 서버 -> 루트 DNS 서버
   ISP DNS 서버 -> TLD DNS 서버
   ISP DNS 서버 -> 권한 있는 DNS 서버
   ISP DNS 서버 -> 클라이언트
   ```

#### 2. Root DNS Servers
- 루트 DNS 서버는 전 세계에 13개의 루트 서버(A~M)가 있으며, 각각 여러 대의 물리적 서버로 구성된 Anycast 네트워크로 운영됩니다.
- 루트 서버의 IP 주소는 DNS 리졸버에 하드코딩되어 있습니다.
- 예를 들어, www.example.com에 대한 질의에서 루트 서버는 .com TLD 서버의 정보를 반환합니다.
- 루트 서버는 도메인 이름의 최상위 도메인(TLD)에 대한 정보만 가지고 있습니다.

##### 상세 설명
1. **루트 서버 구조**
   - 13개의 루트 서버(A~M)는 전 세계적으로 분산 배치
   - 각 루트 서버는 Anycast 기술을 사용하여 여러 물리적 서버로 구성
   - 실제 물리적 서버는 수백 대에 달함

2. **루트 서버 운영 기관**
   - A: Verisign
   - B: USC-ISI
   - C: Cogent Communications
   - D: University of Maryland
   - E: NASA
   - F: Internet Systems Consortium
   - G: US Department of Defense
   - H: US Army Research Lab
   - I: Netnod
   - J: Verisign
   - K: RIPE NCC
   - L: ICANN
   - M: WIDE Project

3. **루트 힌트 파일**
   - 루트 서버의 IP 주소 목록
   - 일반적으로 named.root 또는 db.root 파일에 저장
   - 주기적으로 업데이트됨

#### 3. Top-Level Domain (TLD) DNS Servers
- TLD 서버는 .com, .net, .org, .kr 등과 같은 최상위 도메인을 관리합니다.
- 루트 서버로부터 받은 정보를 바탕으로, 리졸버는 해당 TLD 서버에 질의를 보냅니다.
- 예를 들어, .com TLD 서버는 example.com을 관리하는 권한 있는 DNS 서버의 정보를 반환합니다.
- TLD 서버는 도메인 등록 기관(Registry)에서 관리하며, 각 TLD마다 다른 기관이 관리합니다.

##### 상세 설명
1. **TLD 종류**
   - gTLD (Generic TLD): .com, .net, .org, .edu, .gov 등
   - ccTLD (Country Code TLD): .kr, .jp, .uk, .de 등
   - New gTLD: .app, .blog, .shop 등

2. **TLD 운영 기관**
   - .com, .net: Verisign
   - .org: Public Interest Registry
   - .kr: KISA (한국인터넷진흥원)
   - .jp: JPRS (일본레지스트리서비스)

3. **TLD 서버 구조**
   - 각 TLD는 여러 개의 네임서버로 구성
   - Anycast 기술을 사용하여 전 세계적으로 분산 배치
   - 고가용성과 부하 분산을 위한 설계

#### 4. Authoritative DNS Servers
- 권한 있는 DNS 서버는 실제 도메인을 소유한 조직이나 호스팅 서비스 제공업체가 운영합니다.
- TLD 서버로부터 받은 정보를 바탕으로, 리졸버는 권한 있는 DNS 서버에 질의를 보냅니다.
- 권한 있는 DNS 서버는 도메인에 대한 모든 DNS 레코드(A, AAAA, MX, CNAME 등)를 관리합니다.
- 예를 들어, www.example.com에 대한 A 레코드(IPv4 주소)나 AAAA 레코드(IPv6 주소)를 반환합니다.

##### 상세 설명
1. **권한 있는 DNS 서버 유형**
   - Primary (Master) DNS 서버: 원본 DNS 데이터를 관리
   - Secondary (Slave) DNS 서버: Primary 서버로부터 데이터를 복제
   - Hidden Master: 외부에 노출되지 않는 Primary 서버

2. **DNS 레코드 상세**
   - A 레코드: IPv4 주소 매핑 (예: example.com. IN A 93.184.216.34)
   - AAAA 레코드: IPv6 주소 매핑
   - CNAME 레코드: 도메인 별칭 (예: www.example.com. IN CNAME example.com.)
   - MX 레코드: 메일 서버 지정 (예: example.com. IN MX 10 mail.example.com.)
   - NS 레코드: 도메인의 네임서버 지정
   - TXT 레코드: SPF, DKIM 등 다양한 용도
   - SOA 레코드: 도메인 영역의 권한 정보

   ##### A 레코드 (Address Record)
   - 도메인 이름을 IPv4 주소로 매핑하는 가장 기본적인 레코드 타입입니다.
   - 예시:
     ```
     example.com.    IN    A    93.184.216.34
     www.example.com.    IN    A    93.184.216.34
     blog.example.com.    IN    A    93.184.216.35
     ```
   - 장점:
     - 직접적인 IP 주소 매핑으로 빠른 응답이 가능합니다
     - DNS 쿼리 횟수가 적어 성능이 좋습니다
     - 단일 쿼리로 IP 주소를 얻을 수 있습니다
     - DNS 캐싱이 효율적입니다
   - 단점:
     - IP 주소가 변경될 때마다 DNS 레코드를 수정해야 합니다
     - 서버 이전이나 IP 변경이 빈번한 환경에서는 관리가 어려울 수 있습니다
     - 여러 서버로의 부하 분산이 어렵습니다
     - CDN이나 클라우드 서비스 연동 시 유연성이 떨어집니다
   - 사용 사례:
     - 정적 IP 주소를 사용하는 웹 서버
     - 단일 서버로 운영되는 서비스
     - IP 주소가 자주 변경되지 않는 환경
     - 직접적인 IP 매핑이 필요한 경우

   ##### CNAME (Canonical Name)
   - 도메인 이름을 다른 도메인 이름으로 매핑하는 레코드 타입입니다.
   - 예시:
     ```
     www.example.com.    IN    CNAME    example.com.
     blog.example.com.    IN    CNAME    example.com.
     shop.example.com.    IN    CNAME    example.com.
     ```
   - 장점:
     - IP 주소 변경 시 원본 도메인만 수정하면 됩니다
     - 여러 서브도메인이 하나의 IP를 가리킬 때 유용합니다
     - CDN이나 클라우드 서비스 연동 시 유연하게 대응 가능합니다
     - 서비스 마이그레이션이 용이합니다
     - 도메인 관리가 단순화됩니다
   - 단점:
     - 최종 IP 주소를 얻기 위해 추가 DNS 쿼리가 필요합니다
     - 성능이 A 레코드보다 약간 느릴 수 있습니다
     - DNS 캐시 효율성이 떨어질 수 있습니다
     - 루트 도메인에는 사용할 수 없습니다
   - 사용 사례:
     - CDN 서비스 연동
     - 클라우드 서비스 사용
     - 여러 서브도메인 관리
     - 서비스 마이그레이션 계획
     - IP 주소가 자주 변경되는 환경
   - 주의사항:
     - CNAME 체인은 권장되지 않습니다 (성능 저하)
     - 루트 도메인에는 사용할 수 없습니다
     - 다른 레코드 타입과 함께 사용할 수 없습니다
     - TTL 값 설정에 주의가 필요합니다

3. **DNS 영역 전송**
   - AXFR: 전체 영역 전송
   - IXFR: 증분 영역 전송
   - TSIG: 영역 전송 시 보안

#### 5. IP Address Resolution
- 권한 있는 DNS 서버는 요청된 도메인에 대한 IP 주소 정보를 리졸버에게 반환합니다.
- 리졸버는 이 정보를 자신의 캐시에 저장하고, TTL 값에 따라 일정 시간 동안 유지합니다.
- 리졸버는 최종적으로 클라이언트에게 IP 주소를 반환합니다.
- 클라이언트는 받은 IP 주소를 사용하여 웹 서버와의 TCP 연결을 시작하고 HTTP 요청을 보냅니다.

##### 상세 설명
1. **DNS 캐싱 메커니즘**
   - 브라우저 캐시: 브라우저별 DNS 캐시
   - OS 캐시: 운영체제의 DNS 리졸버 캐시
   - ISP 캐시: ISP의 DNS 서버 캐시
   - TTL 기반 캐시 만료

2. **DNS 응답 구조**
   - Header: 질의 ID, 플래그, 응답 코드 등
   - Question: 원래 질의 내용
   - Answer: 요청된 리소스 레코드
   - Authority: 권한 있는 서버 정보
   - Additional: 추가 정보

3. **DNS 프로토콜 상세**
   - UDP 포트 53 사용 (기본)
   - TCP 포트 53 사용 (대용량 전송 시)
   - EDNS0 확장 지원
   - DNSSEC 지원

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

##### DNS 보안 상세
1. **DNSSEC**
   - DNS 레코드의 디지털 서명
   - DNS 응답의 무결성 검증
   - DNS 스푸핑 방지
   - DS, DNSKEY, RRSIG 레코드 사용

2. **DNS 암호화**
   - DoH (DNS over HTTPS): HTTPS를 통한 DNS 질의
   - DoT (DNS over TLS): TLS를 통한 DNS 질의
   - DNS 쿼리 프라이버시 보호
   - 중간자 공격 방지

3. **DNS 모니터링과 로깅**
   - DNS 쿼리 로깅
   - DNS 응답 시간 모니터링
   - DNS 캐시 히트율 분석
   - DNS 보안 이벤트 모니터링

4. **DNS 성능 최적화**
   - DNS 프리페칭
   - DNS 캐시 최적화
   - DNS 부하 분산
   - DNS 응답 시간 최적화