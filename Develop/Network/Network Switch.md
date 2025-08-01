# 네트워크 스위치 

---

## 네트워크 스위치란?
![네트워크 스위치.svg](..%2F..%2Fetc%2Fimage%2FNetwork_image%2F%EB%84%A4%ED%8A%B8%EC%9B%8C%ED%81%AC%20%EC%8A%A4%EC%9C%84%EC%B9%98.svg) 

- 네트워크 스위치는 OSI 모델의 2계층(데이터 링크 계층)에서 동작하는 네트워크 장비입니다.
- 스위치는 MAC 주소를 기반으로 데이터 프레임을 전달하는 역할을 수행합니다.
- 스위치는 여러 장치를 연결하고, 각 장치 간의 통신을 효율적으로 관리합니다.
- 스위치는 '스위칭 테이블'을 유지하여 각 포트에 연결된 장치의 MAC 주소를 기록합니다.

## 스위치의 주요 기능
1. **MAC 주소 학습**
   - 스위치는 연결된 장치들의 MAC 주소를 자동으로 학습합니다.
   - 스위칭 테이블에 MAC 주소와 해당 포트 정보를 저장합니다.

2. **전송 방식**
   - **유니캐스트**: 특정 목적지에만 데이터를 전송
   - **브로드캐스트**: 네트워크의 모든 장치에 데이터를 전송
   - **멀티캐스트**: 특정 그룹의 장치들에만 데이터를 전송

3. **충돌 도메인 분리**
   - 각 포트는 독립적인 충돌 도메인을 가집니다.
   - 이는 네트워크 성능 향상에 기여합니다.

## 스위치의 종류
1. **관리형 스위치 (Managed Switch)**
   - VLAN, QoS, 포트 미러링 등 고급 기능 지원
   - 네트워크 관리자가 설정을 변경할 수 있음
   - 기업 환경에서 주로 사용

2. **비관리형 스위치 (Unmanaged Switch)**
   - 플러그 앤 플레이 방식으로 작동
   - 추가 설정이 필요 없음
   - 소규모 네트워크나 가정용으로 적합

3. **스마트 스위치 (Smart Switch)**
   - 관리형과 비관리형의 중간 기능 제공
   - 웹 인터페이스를 통한 기본적인 설정 가능
   - 중소규모 기업에 적합

## 스위치와 라우터의 차이점
1. **작동 계층**
   - 스위치: OSI 2계층 (데이터 링크 계층)
   - 라우터: OSI 3계층 (네트워크 계층)

2. **주소 처리**
   - 스위치: MAC 주소 기반 통신
   - 라우터: IP 주소 기반 통신

3. **통신 범위**
   - 스위치: 동일 네트워크 내 통신
   - 라우터: 서로 다른 네트워크 간 통신

4. **브로드캐스트 처리**
   - 스위치: 브로드캐스트 도메인 내에서 전파
   - 라우터: 브로드캐스트를 차단

## MAC 주소와 IP 주소의 차이점
### MAC 주소 (Media Access Control Address)
- 48비트로 구성된 물리적 주소
- 16진수로 표현 (예: 00:1A:2B:3C:4D:5E)
- 제조사에서 할당하는 고유한 주소
- 네트워크 인터페이스 카드(NIC)에 고정되어 있음
- 데이터 링크 계층에서 사용
- 로컬 네트워크 내에서만 사용

### IP 주소 (Internet Protocol Address)
- 32비트(IPv4) 또는 128비트(IPv6)로 구성된 논리적 주소
- 네트워크 관리자가 할당
- 네트워크 계층에서 사용
- 인터넷 전역에서 사용 가능
- 동적 할당(DHCP) 또는 정적 할당 가능
- 네트워크 위치를 식별하는 주소

## 스위치의 실제 적용 사례
1. **기업 네트워크**
   - 여러 부서 간의 효율적인 통신 관리
   - VLAN을 통한 네트워크 분리
   - QoS를 통한 중요 트래픽 우선 처리

2. **데이터 센터**
   - 서버 간의 고속 통신 지원
   - 대용량 데이터 처리
   - 네트워크 가용성 보장

3. **가정/소규모 사무실**
   - 여러 장치 연결
   - 간단한 네트워크 구성
   - 비용 효율적인 솔루션

---
* 참고자료
> [1] [네트워크 스위치란?](https://www.cloudflare.com/ko-kr/learning/network-layer/what-is-a-network-switch/)
> [2] [Cisco Networking Academy](https://www.netacad.com/)
> [3] [Network Switch Types and Functions](https://www.cisco.com/c/en/us/solutions/enterprise-networks/what-is-a-network-switch.html)

