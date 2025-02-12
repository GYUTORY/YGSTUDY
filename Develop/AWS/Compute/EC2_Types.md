
## 📌 AWS EC2 인스턴스 유형
AWS에서는 다양한 **EC2 인스턴스 유형**을 제공하며, 크게 다음과 같은 카테고리로 나눌 수 있습니다.

| **인스턴스 유형** | **특징** | **대표적인 용도** |
|------------------|---------|----------------|
| 범용 (General Purpose) | CPU, 메모리, 네트워크 성능 균형 | 웹 서버, 애플리케이션 서버 |
| 컴퓨팅 최적화 (Compute Optimized) | 고성능 CPU 제공 | 고성능 연산 작업 (예: 게임 서버) |
| 메모리 최적화 (Memory Optimized) | 높은 RAM 제공 | 대용량 인메모리 데이터베이스 |
| 스토리지 최적화 (Storage Optimized) | 고속 디스크 I/O 제공 | 빅데이터, 로그 분석 |
| 가속 컴퓨팅 (Accelerated Computing) | GPU 또는 FPGA 제공 | AI, 머신러닝, 그래픽 렌더링 |

---

## 🔹 1️⃣ 범용 (General Purpose) 인스턴스
범용 인스턴스는 **CPU, 메모리, 네트워크 성능이 균형 있게 제공되는 유형**입니다.

### **✅ 대표적인 인스턴스**
- **T 시리즈 (T3, T3a, T2)**:
    - 🟢 버스트 가능 (Burstable) 성능 제공
    - 평소에는 낮은 성능을 사용하고 필요할 때 순간적으로 CPU 성능 증가
- **M 시리즈 (M6g, M5, M4)**:
    - 🟢 다양한 애플리케이션을 실행할 수 있는 범용 인스턴스
    - 웹 서버, 데이터베이스 서버에 적합

```python
import boto3

# AWS EC2 클라이언트 생성
ec2 = boto3.client('ec2', region_name='ap-northeast-2')

# 범용 EC2 인스턴스 생성 (T3.micro)
response = ec2.run_instances(
    ImageId='ami-12345678',  # AMI ID
    InstanceType='t3.micro',  # 범용 인스턴스 유형
    MinCount=1,
    MaxCount=1,
    KeyName='my-key-pair',
    SecurityGroupIds=['sg-12345678']
)

# 생성된 인스턴스 ID 출력
instance_id = response['Instances'][0]['InstanceId']
print(f"생성된 인스턴스 ID: {instance_id}")
```

---

## 🔹 2️⃣ 컴퓨팅 최적화 (Compute Optimized) 인스턴스
고성능 CPU를 제공하여 **컴퓨팅 성능이 중요한 애플리케이션**에 적합한 유형입니다.

### **✅ 대표적인 인스턴스**
- **C 시리즈 (C6g, C5, C4)**:
    - 고성능 연산 작업이 필요한 환경 (예: 과학 계산, 비디오 트랜스코딩)
    - CPU 집약적인 애플리케이션 (예: 고성능 웹 서버, 게임 서버)

```python
# 컴퓨팅 최적화 EC2 인스턴스 생성 (C5.large)
response = ec2.run_instances(
    ImageId='ami-12345678',
    InstanceType='c5.large',
    MinCount=1,
    MaxCount=1,
    KeyName='my-key-pair',
    SecurityGroupIds=['sg-12345678']
)

instance_id = response['Instances'][0]['InstanceId']
print(f"생성된 컴퓨팅 최적화 인스턴스 ID: {instance_id}")
```

---

## 🔹 3️⃣ 메모리 최적화 (Memory Optimized) 인스턴스
RAM이 많아 **대규모 데이터 처리 및 캐싱 작업**에 최적화된 인스턴스입니다.

### **✅ 대표적인 인스턴스**
- **R 시리즈 (R6g, R5, R4)**:
    - 인메모리 데이터베이스 (Redis, Memcached) 운영에 적합
- **X 시리즈 (X1, X2)**:
    - 고성능 SAP, 인메모리 애플리케이션에 적합

```python
# 메모리 최적화 EC2 인스턴스 생성 (R5.large)
response = ec2.run_instances(
    ImageId='ami-12345678',
    InstanceType='r5.large',
    MinCount=1,
    MaxCount=1,
    KeyName='my-key-pair',
    SecurityGroupIds=['sg-12345678']
)

instance_id = response['Instances'][0]['InstanceId']
print(f"생성된 메모리 최적화 인스턴스 ID: {instance_id}")
```

---

## 🔹 4️⃣ 스토리지 최적화 (Storage Optimized) 인스턴스
고속 디스크 I/O 성능을 제공하여 **빅데이터 및 로그 분석**에 적합합니다.

### **✅ 대표적인 인스턴스**
- **I 시리즈 (I3, I4)**:
    - NVMe SSD를 통한 빠른 데이터 접근
- **D 시리즈 (D2)**:
    - 대용량 데이터 저장 및 분석에 최적

```python
# 스토리지 최적화 EC2 인스턴스 생성 (I3.large)
response = ec2.run_instances(
    ImageId='ami-12345678',
    InstanceType='i3.large',
    MinCount=1,
    MaxCount=1,
    KeyName='my-key-pair',
    SecurityGroupIds=['sg-12345678']
)

instance_id = response['Instances'][0]['InstanceId']
print(f"생성된 스토리지 최적화 인스턴스 ID: {instance_id}")
```

---

## 🔹 5️⃣ 가속 컴퓨팅 (Accelerated Computing) 인스턴스
GPU 또는 FPGA를 사용하여 **머신러닝, AI, 그래픽 처리** 등에 최적화된 인스턴스입니다.

### **✅ 대표적인 인스턴스**
- **P 시리즈 (P4, P3)**:
    - GPU를 활용한 머신러닝 및 딥러닝 모델 학습에 적합
- **G 시리즈 (G5, G4)**:
    - 그래픽 렌더링 및 동영상 처리에 최적

```python
# 가속 컴퓨팅 EC2 인스턴스 생성 (G4.large)
response = ec2.run_instances(
    ImageId='ami-12345678',
    InstanceType='g4.large',
    MinCount=1,
    MaxCount=1,
    KeyName='my-key-pair',
    SecurityGroupIds=['sg-12345678']
)

instance_id = response['Instances'][0]['InstanceId']
print(f"생성된 가속 컴퓨팅 인스턴스 ID: {instance_id}")
```

---

## 🔗 참고 자료
- [AWS 공식 문서 - EC2 인스턴스 유형](https://aws.amazon.com/ec2/instance-types/)
- [Boto3 라이브러리 - EC2](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html)

---

## 🎯 결론
AWS EC2 인스턴스는 다양한 유형으로 제공되며, **애플리케이션 특성에 맞게 선택하는 것이 중요합니다**.  
**비용, 성능, 확장성을 고려하여 최적의 인스턴스를 선택하세요!** 🚀
