---
title: AWS EBS (Elastic Block Store)
tags: [aws, ebs, storage, volume, disk, ec2, snapshot, iops]
updated: 2026-01-18
---

# AWS EBS (Elastic Block Store)

## 개요

EBS는 EC2의 블록 스토리지다. 하드디스크나 SSD처럼 사용한다. OS를 설치하고 데이터를 저장한다. 가용 영역 단위로 복제된다. 스냅샷으로 백업한다. 볼륨 타입마다 성능과 가격이 다르다.

### 왜 필요한가

EC2는 기본적으로 휘발성 스토리지만 가진다.

**Instance Store (임시 스토리지):**
- EC2 호스트 서버의 물리 디스크
- 인스턴스 중지 시 데이터 삭제
- 매우 빠르지만 영구적이지 않음

**문제 상황:**

**데이터 보존:**
웹 서버를 운영한다. 로그 파일, 애플리케이션 데이터를 저장한다. 인스턴스를 중지하면 모든 데이터가 삭제된다.

**인스턴스 교체:**
인스턴스 타입을 변경한다 (t3.medium → t3.large). 데이터를 옮겨야 한다. 복잡하다.

**EBS의 해결:**
- 영구 스토리지
- 인스턴스와 독립적
- 인스턴스를 중지/종료해도 데이터 보존
- 다른 인스턴스에 연결 가능

## 볼륨 타입

### gp3 (범용 SSD)

**가장 많이 사용한다.** 가격 대비 성능이 좋다.

**성능:**
- 기본 IOPS: 3,000
- 기본 처리량: 125 MB/s
- 최대 IOPS: 16,000
- 최대 처리량: 1,000 MB/s
- 크기: 1 GiB ~ 16 TiB

**특징:**
IOPS와 처리량을 독립적으로 조정한다.

**예시:**
- 볼륨 크기: 100 GiB
- IOPS: 10,000
- 처리량: 500 MB/s

크기와 상관없이 성능을 설정한다.

**가격:**
- 스토리지: $0.08/GB-월
- 추가 IOPS (3,000 초과): $0.005/IOPS-월
- 추가 처리량 (125 MB/s 초과): $0.04/MB/s-월

**예시 (100 GiB, 10,000 IOPS, 500 MB/s):**
- 스토리지: 100 × $0.08 = $8
- 추가 IOPS: 7,000 × $0.005 = $35
- 추가 처리량: 375 × $0.04 = $15
- 합계: $58/월

**사용 사례:**
- 웹 서버
- 애플리케이션 서버
- 개발/테스트 환경
- 데이터베이스 (중소규모)

### gp2 (구형 범용 SSD)

gp3의 이전 버전이다. 새로운 볼륨은 gp3를 사용한다.

**성능:**
- 기본 IOPS: 100 (최소)
- 볼륨 크기당 IOPS: 3 IOPS/GB
- 최대 IOPS: 16,000
- 처리량: 250 MB/s (볼륨 > 334 GiB)

**예시:**
- 100 GiB: 300 IOPS
- 1,000 GiB: 3,000 IOPS
- 5,334 GiB: 16,000 IOPS

크기와 IOPS가 연결되어 있다. 크기를 늘려야 IOPS가 증가한다.

**gp3 vs gp2:**
- gp3가 저렴하다
- gp3가 유연하다
- gp2는 레거시

**gp2에서 gp3로 마이그레이션:**
다운타임 없이 변경 가능하다.

```bash
aws ec2 modify-volume \
  --volume-id vol-12345678 \
  --volume-type gp3
```

### io2 (프로비저닝 IOPS SSD)

**매우 높은 성능이 필요할 때 사용한다.** 데이터베이스 워크로드에 적합하다.

**성능:**
- 최대 IOPS: 64,000 (Nitro 인스턴스), 32,000 (비-Nitro)
- IOPS/GB: 500:1 비율
- 처리량: 1,000 MB/s
- 크기: 4 GiB ~ 16 TiB

**특징:**
- 99.999% 내구성 (gp3는 99.8-99.9%)
- Multi-Attach 지원

**가격:**
- 스토리지: $0.125/GB-월
- IOPS: $0.065/IOPS-월 (32,000 이하), $0.046/IOPS-월 (32,000 초과)

**예시 (100 GiB, 50,000 IOPS):**
- 스토리지: 100 × $0.125 = $12.50
- IOPS (0-32,000): 32,000 × $0.065 = $2,080
- IOPS (32,001-50,000): 18,000 × $0.046 = $828
- 합계: $2,920.50/월

**매우 비싸다.** 꼭 필요한 경우에만 사용한다.

**사용 사례:**
- 대규모 데이터베이스 (Oracle, SQL Server)
- NoSQL 데이터베이스 (MongoDB, Cassandra)
- 미션 크리티컬 애플리케이션

### st1 (처리량 최적화 HDD)

**대용량 순차 읽기/쓰기에 적합하다.** IOPS는 낮지만 처리량이 높다.

**성능:**
- 기본 처리량: 40 MB/s/TB
- 최대 처리량: 500 MB/s
- 최대 IOPS: 500
- 크기: 125 GiB ~ 16 TiB

**가격:**
- 스토리지: $0.045/GB-월

gp3보다 저렴하다.

**사용 사례:**
- 빅데이터
- 데이터 웨어하우스
- 로그 처리
- 백업

**부트 볼륨으로 사용 불가:**
OS를 설치할 수 없다. SSD만 부트 볼륨이 가능하다.

### sc1 (Cold HDD)

**가장 저렴하다.** 자주 접근하지 않는 데이터를 저장한다.

**성능:**
- 기본 처리량: 12 MB/s/TB
- 최대 처리량: 250 MB/s
- 최대 IOPS: 250
- 크기: 125 GiB ~ 16 TiB

**가격:**
- 스토리지: $0.015/GB-월

**사용 사례:**
- 아카이브
- 장기 백업
- 접근 빈도가 매우 낮은 데이터

## 볼륨 생성 및 연결

### 볼륨 생성

**콘솔:**
1. EC2 콘솔 → Volumes
2. "Create Volume" 클릭
3. 타입 선택 (gp3)
4. 크기 입력 (100 GiB)
5. 가용 영역 선택 (EC2와 같은 AZ)
6. IOPS, 처리량 설정
7. 암호화 활성화
8. 생성

**CLI:**
```bash
aws ec2 create-volume \
  --volume-type gp3 \
  --size 100 \
  --iops 3000 \
  --throughput 125 \
  --availability-zone us-west-2a \
  --encrypted \
  --tag-specifications 'ResourceType=volume,Tags=[{Key=Name,Value=my-volume}]'
```

**주의: 가용 영역**
볼륨과 EC2는 같은 가용 영역에 있어야 한다.

- EC2: us-west-2a
- 볼륨: us-west-2a (OK)
- 볼륨: us-west-2b (연결 불가)

### 볼륨 연결

**CLI:**
```bash
aws ec2 attach-volume \
  --volume-id vol-12345678 \
  --instance-id i-12345678 \
  --device /dev/sdf
```

**Device 이름:**
- `/dev/sdf` ~ `/dev/sdp`: 추가 볼륨
- `/dev/sda1` 또는 `/dev/xvda`: 루트 볼륨 (보통 자동)

**Linux에서 확인:**
```bash
lsblk
```

출력:
```
NAME    MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT
xvda    202:0    0    8G  0 disk
└─xvda1 202:1    0    8G  0 part /
xvdf    202:80   0  100G  0 disk
```

`xvdf`가 새로 연결된 볼륨이다.

### 파일 시스템 생성 및 마운트

**포맷:**
```bash
sudo mkfs -t ext4 /dev/xvdf
```

ext4 파일 시스템을 생성한다.

**마운트:**
```bash
sudo mkdir /data
sudo mount /dev/xvdf /data
```

`/data` 디렉토리에 마운트한다.

**자동 마운트 (재부팅 시):**
```bash
# UUID 확인
sudo blkid /dev/xvdf

# /etc/fstab 수정
sudo vi /etc/fstab

# 추가
UUID=12345678-1234-1234-1234-123456789012  /data  ext4  defaults,nofail  0  2
```

재부팅해도 자동으로 마운트된다.

## 스냅샷

### 스냅샷 생성

볼륨의 특정 시점 백업이다.

**생성:**
```bash
aws ec2 create-snapshot \
  --volume-id vol-12345678 \
  --description "Daily backup 2026-01-18" \
  --tag-specifications 'ResourceType=snapshot,Tags=[{Key=Name,Value=daily-backup}]'
```

**증분 백업:**
첫 스냅샷은 전체 데이터를 백업한다. 이후 스냅샷은 변경된 블록만 백업한다.

**예시:**
- 1차 스냅샷: 100 GiB 볼륨 → 100 GiB 백업
- 2차 스냅샷: 5 GiB 변경 → 5 GiB만 백업
- 3차 스냅샷: 3 GiB 변경 → 3 GiB만 백업

비용이 절감된다.

**스냅샷 중 볼륨 사용:**
스냅샷을 만드는 동안 볼륨을 계속 사용할 수 있다. 다운타임이 없다. 하지만 성능이 약간 떨어진다.

### 스냅샷 복원

스냅샷에서 새 볼륨을 만든다.

**복원:**
```bash
aws ec2 create-volume \
  --snapshot-id snap-12345678 \
  --availability-zone us-west-2a \
  --volume-type gp3 \
  --iops 3000
```

**다른 가용 영역:**
스냅샷은 S3에 저장된다. 리전 내 모든 가용 영역에서 복원할 수 있다.

- 원본 볼륨: us-west-2a
- 스냅샷: S3 (리전 레벨)
- 복원 볼륨: us-west-2b (가능)

**다른 리전:**
스냅샷을 다른 리전으로 복사한다.

```bash
aws ec2 copy-snapshot \
  --source-region us-west-2 \
  --source-snapshot-id snap-12345678 \
  --destination-region us-east-1 \
  --description "Copy to us-east-1"
```

재해 복구에 유용하다.

### 스냅샷 삭제

오래된 스냅샷을 삭제한다. 비용을 절감한다.

```bash
aws ec2 delete-snapshot --snapshot-id snap-12345678
```

**증분 백업의 특징:**
중간 스냅샷을 삭제해도 다른 스냅샷에 영향을 주지 않는다. AWS가 자동으로 관리한다.

**예시:**
- 스냅샷 1: 100 GiB
- 스냅샷 2: +5 GiB
- 스냅샷 3: +3 GiB

스냅샷 2를 삭제해도 스냅샷 3은 정상 동작한다. AWS가 필요한 블록을 유지한다.

## 볼륨 확장

### 크기 증가

볼륨 크기를 늘린다. 다운타임 없이 가능하다.

**확장:**
```bash
aws ec2 modify-volume \
  --volume-id vol-12345678 \
  --size 200
```

100 GiB → 200 GiB로 증가한다.

**파일 시스템 확장:**
OS에서 파일 시스템을 확장해야 한다.

**Linux (ext4):**
```bash
# 파티션 확장
sudo growpart /dev/xvdf 1

# 파일 시스템 확장
sudo resize2fs /dev/xvdf1
```

**확인:**
```bash
df -h
```

크기가 증가했는지 확인한다.

### IOPS/처리량 증가

gp3 볼륨의 IOPS와 처리량을 늘린다.

```bash
aws ec2 modify-volume \
  --volume-id vol-12345678 \
  --iops 10000 \
  --throughput 500
```

3,000 IOPS → 10,000 IOPS로 증가한다. 다운타임 없다.

**제한:**
- 6시간마다 한 번씩 수정 가능
- 크기 감소는 불가능
- 타입 변경 후 6시간 대기

## 암호화

### 암호화 활성화

**볼륨 생성 시:**
```bash
aws ec2 create-volume \
  --volume-type gp3 \
  --size 100 \
  --encrypted \
  --kms-key-id arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012
```

**기본 KMS 키 사용:**
`--kms-key-id` 생략 시 AWS 관리형 키를 사용한다.

**암호화 내용:**
- 볼륨 내 데이터
- 볼륨과 인스턴스 간 전송 데이터
- 스냅샷
- 스냅샷에서 생성된 볼륨

**성능 영향:**
거의 없다. 암호화는 하드웨어 레벨에서 처리된다.

### 암호화되지 않은 볼륨 암호화

기존 볼륨을 암호화한다.

**방법:**
1. 스냅샷 생성
2. 스냅샷 복사 (암호화 활성화)
3. 암호화된 스냅샷에서 볼륨 생성
4. 새 볼륨을 EC2에 연결
5. 이전 볼륨 분리 및 삭제

**스냅샷 복사 (암호화):**
```bash
aws ec2 copy-snapshot \
  --source-region us-west-2 \
  --source-snapshot-id snap-12345678 \
  --encrypted \
  --kms-key-id arn:aws:kms:us-west-2:123456789012:key/...
```

## Multi-Attach

하나의 EBS 볼륨을 여러 EC2에 연결한다.

**지원 볼륨:**
- io2만 지원
- 같은 가용 영역에 있어야 함
- 최대 16개 인스턴스

**사용 사례:**
- 클러스터 파일 시스템
- 고가용성 애플리케이션

**주의:**
일반 파일 시스템 (ext4, XFS)는 Multi-Attach를 지원하지 않는다. 클러스터 파일 시스템 (GFS2, OCFS2)을 사용해야 한다.

**활성화:**
```bash
aws ec2 modify-volume-attribute \
  --volume-id vol-12345678 \
  --multi-attach-enabled
```

**연결:**
```bash
aws ec2 attach-volume \
  --volume-id vol-12345678 \
  --instance-id i-11111111 \
  --device /dev/sdf

aws ec2 attach-volume \
  --volume-id vol-12345678 \
  --instance-id i-22222222 \
  --device /dev/sdf
```

두 인스턴스가 같은 볼륨에 접근한다.

## 성능 최적화

### IOPS 계산

애플리케이션에 필요한 IOPS를 계산한다.

**예시: MySQL**
- 읽기: 5,000 쿼리/초
- 쓰기: 1,000 쿼리/초
- 읽기당 IOPS: 10
- 쓰기당 IOPS: 20

**필요 IOPS:**
- 읽기: 5,000 × 10 = 50,000
- 쓰기: 1,000 × 20 = 20,000
- 합계: 70,000

io2 볼륨이 필요하다 (gp3는 최대 16,000).

### 처리량 계산

**예시: 로그 서버**
- 초당 로그: 1,000개
- 로그 크기: 1 KB
- 총 처리량: 1,000 KB/s = 약 1 MB/s

gp3 기본 처리량 (125 MB/s)으로 충분하다.

### 인스턴스 타입 고려

EBS 성능은 인스턴스 타입에도 영향을 받는다.

**EBS Optimized:**
EBS 전용 네트워크 대역폭을 제공한다. 대부분의 인스턴스 타입은 기본적으로 활성화되어 있다.

**대역폭:**
- t3.medium: 2,085 Mbps (약 260 MB/s)
- m5.large: 4,750 Mbps (약 593 MB/s)
- m5.4xlarge: 18,750 Mbps (약 2,343 MB/s)

볼륨 성능이 높아도 인스턴스 대역폭이 부족하면 성능이 제한된다.

## 비용 최적화

### 적절한 타입 선택

**예시: 웹 서버**
- 트래픽: 중간
- IOPS 요구: 3,000 이하
- 크기: 100 GiB

**gp3:**
- 비용: $8/월
- 성능: 충분

**io2 (50,000 IOPS):**
- 비용: $2,920/월
- 성능: 과도함

gp3를 사용한다. 365배 저렴하다.

### 오래된 스냅샷 삭제

스냅샷은 S3에 저장된다. 비용이 발생한다.

**스냅샷 비용:**
$0.05/GB-월

**예시:**
- 100 GiB 볼륨
- 매일 스냅샷 (30일 보관)
- 일일 변경: 5 GiB

**비용:**
- 첫 스냅샷: 100 GiB
- 29개 증분 스냅샷: 29 × 5 = 145 GiB
- 합계: 245 GiB × $0.05 = $12.25/월

**최적화:**
- 보관 기간 단축 (30일 → 7일)
- 주간 스냅샷만 유지
- Lifecycle Manager 사용

### gp2 → gp3 마이그레이션

gp2를 사용 중이면 gp3로 변경한다.

**비용 비교 (100 GiB):**
- gp2: $10/월
- gp3: $8/월

20% 저렴하다. 성능도 더 좋다.

```bash
aws ec2 modify-volume \
  --volume-id vol-12345678 \
  --volume-type gp3
```

## 참고

- AWS EBS 개발자 가이드: https://docs.aws.amazon.com/ebs/
- EBS 요금: https://aws.amazon.com/ebs/pricing/
- EBS 볼륨 타입: https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html
- EBS 스냅샷: https://docs.aws.amazon.com/ebs/latest/userguide/EBSSnapshots.html

