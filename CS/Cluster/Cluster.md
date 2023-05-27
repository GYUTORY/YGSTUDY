# 서버 클러스터 란



- 서버 클러스터란 각기 다른 서버들을 하나로 묶어서 하나의 시스템같이 동작하게 함으로써, 클라이언트들에게 고가용성의 서비스를 제공하는것을 말한다.
- 클러스터로 묶인 한시스템에 장애가 발생하면, 정보의 제공 포인트는 클러스터로 묶인 다른 정상적인 서버로 이동한다. 
- 서버클러스터는 사용자로 하여금 서버 기반 정보를 지속적이고, 끊기지않게 제공받을수 있게 한다.


# 클러스터의 장점
- 클러스터는 높은 수준의 가용성, 안정성, 확장성 을 제공 하기 위해 하나의 시스템을 이용하는것보다, 두개 또는 그이상의 시스템을 이용한다.


# 서버 클러스터의 구성
- Single quorum device cluster, 또한 표준 쿼럼 클러스터로 불리운다
- Majority node set cluster
- Local quorum cluster, 또한 싱글 노드 클러스터로 불리운다
- Single Quorum Device Cluster

# 클러스터 구성의 스토리지 소유 방법

1. 공유 스토리지
- 여러대의 서버가 공유하는 스토리지를 마련하여 데이터의 무결성을 확보, 확장성이 높아서 대규모 시스템에 적합하다.

2. 리플리케이션(데이터 미러 구성)
- 스토리지를 완전히 똑같은 내용으로 복제(리플리케이션)하여 데이터의 무결성을 확보한다.
- 저가로 구축할 수 있어서 소규모 시스템에 적합하다.


출처 
- https://allpartner.tistory.com/11
- https://coding-hyeok.tistory.com/44