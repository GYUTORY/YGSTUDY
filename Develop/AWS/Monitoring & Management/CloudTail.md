

# 🔍 AWS CloudTrail 개념 및 설명

## 1️⃣ AWS CloudTrail이란?
**AWS CloudTrail**은 AWS 계정 내에서 발생하는 **모든 API 호출을 추적**하고 **로그를 저장하는 서비스**입니다.  
이를 통해 보안 감사, 문제 해결, 규정 준수를 위한 기록을 남길 수 있습니다.

> **CloudTrail은 AWS에서 발생하는 모든 API 호출을 기록하여 "누가, 언제, 어떤 작업을 했는지" 추적할 수 있도록 해줍니다.**

---

## 2️⃣ CloudTrail의 주요 기능
### ✅ 1. AWS API 호출 로깅
- **AWS 계정에서 수행된 모든 API 호출을 자동으로 기록**합니다.
- 콘솔, SDK, CLI를 통한 요청 모두 추적됩니다.

### ✅ 2. 로그 저장 및 분석
- 로그 데이터는 기본적으로 **S3 버킷에 저장**되며, 이를 활용해 분석이 가능합니다.
- **CloudWatch Logs 및 AWS Athena**를 사용해 데이터를 쿼리할 수도 있습니다.

### ✅ 3. 실시간 보안 모니터링
- **CloudTrail Insights**를 사용하면 비정상적인 API 활동을 감지하고 알림을 받을 수 있습니다.
- 예를 들어, **EC2 인스턴스가 갑자기 대량으로 생성되거나, IAM 권한이 반복적으로 변경될 경우 감지 가능**

### ✅ 4. 다중 계정 및 리전 관리
- **AWS Organizations**를 활용하면 여러 개의 AWS 계정에 대한 CloudTrail을 중앙에서 관리할 수 있습니다.

---

## 3️⃣ CloudTrail 이벤트 유형

### ✨ CloudTrail 이벤트는 크게 3가지 유형으로 나뉩니다.

#### 1. **관리 이벤트 (Management Events)**
- AWS 리소스를 **생성, 수정, 삭제**하는 API 호출을 기록합니다.
- 예시: `RunInstances`, `TerminateInstances`, `CreateBucket`, `DeleteUser`

#### 2. **데이터 이벤트 (Data Events)**
- S3 객체 수준의 액세스 및 Lambda 함수 실행과 관련된 API 호출을 기록합니다.
- 기본적으로 비활성화되어 있으며, 활성화해야 기록됩니다.
- 예시: `GetObject`, `PutObject`, `InvokeFunction`

#### 3. **인사이트 이벤트 (CloudTrail Insights)**
- 일반적인 API 호출 패턴에서 벗어난 **비정상적인 활동을 감지**합니다.
- 예시: IAM 사용자가 갑자기 수백 개의 보안 그룹을 삭제하는 경우 감지 가능

---

## 4️⃣ CloudTrail 로그 저장 방식

### ✅ 기본적으로 CloudTrail 로그는 **S3 버킷**에 저장됩니다.
- CloudTrail 생성 시, **S3 버킷을 지정하여 로그를 저장**할 수 있습니다.
- **SNS(Simple Notification Service)** 와 연동하면 로그가 기록될 때마다 알림을 받을 수도 있습니다.

### ✅ CloudTrail 로그를 CloudWatch Logs로 전송 가능
- CloudWatch Logs와 연동하면 **로그 데이터를 쿼리 및 시각화 가능**

### ✅ AWS Athena를 이용한 로그 분석
- Athena와 연동하면 **SQL 쿼리로 CloudTrail 로그를 분석**할 수 있음

---

## 5️⃣ CloudTrail 설정 방법

### ✨ AWS CLI를 이용한 CloudTrail 생성
```bash
aws cloudtrail create-trail     --name MyCloudTrail     --s3-bucket-name my-cloudtrail-bucket     --is-multi-region-trail
```
> 위 명령어는 "MyCloudTrail"이라는 CloudTrail을 생성하고, S3 버킷에 저장합니다.

### ✨ CloudTrail 이벤트 로그 확인
```bash
aws cloudtrail lookup-events --max-results 5
```
> 위 명령어를 실행하면 최근 5개의 이벤트 로그를 확인할 수 있습니다.

---

## 6️⃣ CloudTrail 로그 분석 예제

### ✅ AWS Athena를 사용하여 특정 사용자 활동 조회
```sql
SELECT eventTime, eventName, userIdentity.username 
FROM cloudtrail_logs 
WHERE userIdentity.username = 'admin_user' 
ORDER BY eventTime DESC 
LIMIT 10;
```
> 위 쿼리는 `admin_user`가 수행한 최근 10개의 이벤트를 조회합니다.

---

## 7️⃣ CloudTrail 보안 및 모니터링

### ✅ CloudTrail Logs에 대한 암호화
- **AWS Key Management Service (KMS)**를 사용하여 CloudTrail 로그를 암호화할 수 있음

### ✅ CloudTrail 로그 무결성 검증
- **로그 파일 다이제스트**를 통해 로그 데이터가 변조되지 않았는지 검증 가능

### ✅ CloudWatch Logs와 연동하여 경고 설정
- 특정 API 호출이 발생하면 **CloudWatch 경고를 생성하여 알림을 받을 수 있음**

---

## 8️⃣ CloudTrail 요금 계산

- CloudTrail은 **기본적인 관리 이벤트 로깅은 무료**
- 데이터 이벤트 및 Insights 기능을 활성화하면 추가 비용이 발생
- **S3 저장소 및 CloudWatch Logs 사용량에 따라 요금 부과됨**

