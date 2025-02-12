# AWS EC2 T 시리즈 (Burstable Performance Instances)

## ✨ AWS EC2 T 시리즈란?
AWS EC2 T 시리즈는 **버스트 성능을 지원하는 범용 인스턴스**로,  
일반적인 상태에서는 적절한 성능을 유지하다가,  
필요할 때 순간적으로 CPU 성능을 높일 수 있는 **저비용, 고효율** 인스턴스입니다.

---

## 📌 AWS EC2 T 시리즈의 특징
### 1️⃣ **버스트 가능한 성능 (Burstable Performance)**
- 기본적인 CPU 성능 제공
- CPU 크레딧을 이용하여 순간적으로 성능을 높일 수 있음

### 2️⃣ **비용 효율적 (Cost-Effective)**
- 일정 수준 이하의 CPU 사용량에서는 매우 저렴한 비용으로 운영 가능
- 웹 서버, 개발 환경 등 **간헐적으로 CPU를 사용하는 애플리케이션**에 적합

### 3️⃣ **다양한 옵션 제공**
- **T4g (ARM 기반, 비용 절감형)**
- **T3, T3a (x86 기반, 표준 성능)**
- **T2 (이전 세대, 여전히 사용 가능)**

---

## 🚀 AWS EC2 T 시리즈 작동 방식
### 👉🏻 **기본 개념**
1. **CPU 크레딧 (CPU Credits)**
    - EC2 T 시리즈 인스턴스는 CPU를 적게 사용하면 크레딧이 쌓임
    - 필요할 때 **버스트 모드(Burst Mode)**로 크레딧을 사용하여 CPU 성능을 증가시킴

2. **크레딧 소진 후 성능 제한**
    - 크레딧이 소진되면, 기본 성능 수준으로 제한됨
    - 일부 T 시리즈(예: T3 Unlimited 모드)는 추가 비용을 내고 크레딧 없이도 성능을 유지 가능

---

## 🔹 AWS EC2 T 시리즈의 인스턴스 유형

| 인스턴스 유형 | CPU | 메모리 (RAM) | 특징 |
|--------------|-----|-------------|-----------------|
| **T4g** | ARM 기반 | 0.5~32GB | 저비용, 고성능 |
| **T3** | x86 기반 | 0.5~32GB | 표준 성능, 대부분의 워크로드에 적합 |
| **T3a** | AMD 기반 | 0.5~32GB | T3보다 저렴, 약간 낮은 성능 |
| **T2** | x86 기반 | 0.5~32GB | 이전 세대, 여전히 사용 가능 |

---

## 🔥 AWS EC2 T 시리즈 사용 예제
T3.micro 인스턴스를 생성하는 예제입니다.

```python
import boto3

# AWS EC2 클라이언트 생성
ec2 = boto3.client('ec2', region_name='ap-northeast-2')

# T3.micro 인스턴스 생성
response = ec2.run_instances(
    ImageId='ami-12345678',  # AMI ID (운영체제 이미지)
    InstanceType='t3.micro',  # T3 인스턴스 선택
    MinCount=1,
    MaxCount=1,
    KeyName='my-key-pair',  # SSH 접속을 위한 키 페어
    SecurityGroupIds=['sg-12345678'],  # 보안 그룹 ID
    SubnetId='subnet-12345678'  # 서브넷 ID
)

# 생성된 인스턴스 정보 출력
instance_id = response['Instances'][0]['InstanceId']
print(f"새로운 T3.micro EC2 인스턴스가 생성되었습니다: {instance_id}")
```

#### 📌 **코드 설명**
1. `boto3.client('ec2')`: AWS EC2 클라이언트를 생성합니다.
2. `run_instances()`: EC2 인스턴스를 생성합니다.
3. `InstanceType='t3.micro'`: T3.micro 인스턴스를 선택합니다.
4. `KeyName`: SSH 연결을 위한 키 페어를 설정합니다.
5. `print(instance_id)`: 생성된 인스턴스 ID를 출력합니다.

---

## 🔹 T 시리즈의 CPU 크레딧 시스템

```mermaid
graph TD;
    CPU 사용 낮음 -->|크레딧 적립| CPU 크레딧 풀
    CPU 사용 높음 -->|크레딧 소비| CPU 크레딧 풀
    CPU 크레딧 풀 -->|버스트 성능 활성화| 인스턴스 성능 증가
```

### 💡 **CPU 크레딧 개념**
1. **CPU를 적게 사용하면 크레딧이 쌓인다.**
2. **CPU를 많이 사용할 때, 크레딧을 사용하여 성능을 높인다.**
3. **크레딧이 소진되면 기본 성능으로 복귀한다.**

---

## ✅ AWS EC2 T 시리즈 사용 사례

### 1️⃣ **웹 서버 및 블로그 호스팅**
- 트래픽이 일정하지 않은 웹 사이트, 개인 블로그 등에 적합

### 2️⃣ **개발 및 테스트 환경**
- 비용이 저렴하여 개발자가 빠르게 테스트할 수 있는 환경 구축 가능

### 3️⃣ **경량 애플리케이션**
- 데이터베이스 캐싱, API 서버, 메시징 큐 등의 경량 애플리케이션 운영 가능

---

## 🌟 AWS EC2 T 시리즈 관련 FAQ
### ❓ **Q: T3와 T3a의 차이는 무엇인가요?**
👉🏻 **T3는 Intel 기반**, **T3a는 AMD 기반**입니다.  
T3a는 T3보다 약간 저렴하지만, 성능이 미세하게 낮습니다.

### ❓ **Q: T3 인스턴스의 기본 CPU 성능은 어느 정도인가요?**
👉🏻 **기본적으로 저전력 CPU 성능을 유지**하며, 크레딧을 사용하여 성능을 일시적으로 높일 수 있습니다.

### ❓ **Q: T 시리즈 인스턴스에서 크레딧을 초과하면 어떻게 되나요?**
👉🏻 **크레딧이 소진되면 CPU 성능이 제한**됩니다.  
하지만 **T3 Unlimited 옵션**을 활성화하면 추가 비용을 내고 성능을 계속 유지할 수 있습니다.

```python
# T3 인스턴스 Unlimited 모드 활성화
ec2.modify_instance_credit_specification(
    InstanceCreditSpecifications=[
        {
            'InstanceId': 'i-1234567890abcdef0',
            'CpuCredits': 'unlimited'
        }
    ]
)
```

---

## 🔗 참고 자료
- [AWS 공식 문서 - EC2 T 시리즈](https://aws.amazon.com/ec2/instance-types/t3/)
- [Boto3 라이브러리 - EC2](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html)

---

## 🎯 결론
AWS EC2 T 시리즈는 **비용 효율적인 인스턴스 유형**으로,  
**웹 서버, 개발 환경, 저부하 애플리케이션** 등에 적합합니다.  
특히, **CPU 크레딧을 활용하여 순간적인 성능 증가가 필요한 경우** 매우 유용합니다! 🚀
