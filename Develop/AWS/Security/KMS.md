---
title: AWS KMS Key Management Service
tags: [aws, security, kms]
updated: 2025-08-10
---
# AWS KMS (Key Management Service)

## 배경

AWS KMS는 클라우드 환경에서 암호화 키를 안전하게 생성, 저장, 관리하는 서비스입니다. 데이터 보안을 위해 암호화가 필요하지만, 암호화 키 자체를 안전하게 관리하는 것은 복잡한 작업입니다. KMS는 이러한 키 관리의 복잡성을 대신 처리해줍니다.


### 암호화란?
암호화는 데이터를 읽을 수 없는 형태로 변환하는 과정입니다. 예를 들어, "안녕하세요"라는 텍스트를 특정 규칙에 따라 "x7f9a2b" 같은 형태로 변환하는 것입니다.

### 키(Key)란?
암호화와 복호화에 사용되는 비밀 정보입니다. 마치 집 열쇠처럼, 올바른 키가 있어야만 데이터에 접근할 수 있습니다.

### 대칭키 vs 비대칭키
- **대칭키**: 암호화와 복호화에 같은 키를 사용 (일반적인 방식)
- **비대칭키**: 공개키와 개인키 쌍을 사용 (특수한 용도)

암호화는 데이터를 읽을 수 없는 형태로 변환하는 과정입니다. 예를 들어, "안녕하세요"라는 텍스트를 특정 규칙에 따라 "x7f9a2b" 같은 형태로 변환하는 것입니다.

- 대칭키와 비대칭키 생성 지원
- 키 활성화/비활성화, 삭제, 교체(로테이션) 기능

- KMS API를 통한 직접 암호화/복호화
- S3, EBS, RDS 등 AWS 서비스와 연동하여 자동 암호화

- IAM 정책, 키 정책, 그랜트를 통한 세분화된 권한 관리
- 누가 어떤 키를 언제 사용할 수 있는지 제어

- CloudTrail과 연동하여 모든 키 사용 이력 추적
- 보안 감사 및 규정 준수 지원

1. 애플리케이션이 KMS에 데이터 키 생성을 요청
2. KMS가 CMK로 암호화된 데이터 키와 평문 데이터 키를 반환
3. 애플리케이션이 평문 데이터 키로 데이터를 암호화
4. 암호화된 데이터와 암호화된 데이터 키를 함께 저장

1. 애플리케이션이 암호화된 데이터 키를 KMS에 전달
2. KMS가 CMK로 복호화하여 평문 데이터 키를 반환
3. 애플리케이션이 평문 데이터 키로 데이터를 복호화


### AWS 관리형 키
AWS가 자동으로 생성하고 관리하는 키입니다. 별도의 관리가 필요 없지만, 세부적인 제어는 제한적입니다.

### 고객 관리형 키
사용자가 직접 생성하고 관리하는 키입니다. 키 정책, 로테이션, 삭제 등 모든 설정을 제어할 수 있습니다.

사용자가 직접 생성하고 관리하는 키입니다. 키 정책, 로테이션, 삭제 등 모든 설정을 제어할 수 있습니다.


### 키 삭제
키를 삭제하면 해당 키로 암호화된 데이터는 영구적으로 복구할 수 없습니다. 삭제 전 7~30일의 대기 기간을 설정할 수 있습니다.

### 키 로테이션
정기적으로 키를 교체하여 보안을 강화할 수 있습니다. 고객 관리형 키는 자동 로테이션을 설정할 수 있습니다.

### 권한 관리
키에 접근할 수 있는 사용자나 서비스를 최소화하는 것이 중요합니다. IAM, 키 정책, 그랜트를 통해 철저히 관리해야 합니다.

키를 삭제하면 해당 키로 암호화된 데이터는 영구적으로 복구할 수 없습니다. 삭제 전 7~30일의 대기 기간을 설정할 수 있습니다.

정기적으로 키를 교체하여 보안을 강화할 수 있습니다. 고객 관리형 키는 자동 로테이션을 설정할 수 있습니다.

키에 접근할 수 있는 사용자나 서비스를 최소화하는 것이 중요합니다. IAM, 키 정책, 그랜트를 통해 철저히 관리해야 합니다.


```javascript
import { KMSClient, GenerateDataKeyCommand } from '@aws-sdk/client-kms';
import crypto from 'crypto';

const kmsClient = new KMSClient({ region: 'ap-northeast-2' });

// 데이터 키 생성
async function generateDataKey(keyId) {
  const command = new GenerateDataKeyCommand({
    KeyId: keyId,
    KeySpec: 'AES_256'
  });
  
  const response = await kmsClient.send(command);
  return {
    plaintextKey: response.Plaintext,
    encryptedKey: response.CiphertextBlob
  };
}

// AES 암호화
function encryptWithAES(plaintext, key) {
  const iv = crypto.randomBytes(16);
  const cipher = crypto.createCipher('aes-256-cbc', key);
  let encrypted = cipher.update(plaintext, 'utf-8', 'hex');
  encrypted += cipher.final('hex');
  
  return {
    encrypted: encrypted,
    iv: iv.toString('hex')
  };
}

// AES 복호화
function decryptWithAES(encrypted, key, iv) {
  const decipher = crypto.createDecipher('aes-256-cbc', key);
  let decrypted = decipher.update(encrypted, 'hex', 'utf-8');
  decrypted += decipher.final('utf-8');
  
  return decrypted;
}

// 사용 예시
async function dataKeyExample() {
  const keyId = 'arn:aws:kms:ap-northeast-2:123456789012:key/abcd1234-5678-90ef-ghij-klmnopqrstuv';
  const originalData = '중요한 비밀 데이터';
  
  try {
    // 데이터 키 생성
    const { plaintextKey, encryptedKey } = await generateDataKey(keyId);
    
    // 데이터 암호화
    const { encrypted, iv } = encryptWithAES(originalData, plaintextKey);
    
    // 암호화된 데이터와 키를 저장
    const dataToStore = {
      encryptedData: encrypted,
      encryptedKey: encryptedKey.toString('base64'),
      iv: iv
    };
    
    console.log('저장할 데이터:', dataToStore);
    
    // 복호화 과정 (나중에)
    const retrievedKey = Buffer.from(dataToStore.encryptedKey, 'base64');
    const decryptedKey = await decryptData(retrievedKey);
    const decryptedData = decryptWithAES(dataToStore.encryptedData, decryptedKey, dataToStore.iv);
    
    console.log('복호화된 데이터:', decryptedData);
  } catch (error) {
    console.error('오류:', error);
  }
}
```

- **키 생성/보관**: 월별 소액 과금
- **암호화/복호화 요청**: 요청 건수에 따라 과금
- **AWS Free Tier**: 월 20,000건 무료 제공

- 리전 단위로 키 관리 (리전 간 복제 불가)
- 대량의 암호화/복호화 요청 시 비용 증가
- 일부 특수한 암호화 요구사항은 지원하지 않음







암호화는 데이터를 읽을 수 없는 형태로 변환하는 과정입니다. 예를 들어, "안녕하세요"라는 텍스트를 특정 규칙에 따라 "x7f9a2b" 같은 형태로 변환하는 것입니다.

사용자가 직접 생성하고 관리하는 키입니다. 키 정책, 로테이션, 삭제 등 모든 설정을 제어할 수 있습니다.

사용자가 직접 생성하고 관리하는 키입니다. 키 정책, 로테이션, 삭제 등 모든 설정을 제어할 수 있습니다.


키를 삭제하면 해당 키로 암호화된 데이터는 영구적으로 복구할 수 없습니다. 삭제 전 7~30일의 대기 기간을 설정할 수 있습니다.

정기적으로 키를 교체하여 보안을 강화할 수 있습니다. 고객 관리형 키는 자동 로테이션을 설정할 수 있습니다.

키에 접근할 수 있는 사용자나 서비스를 최소화하는 것이 중요합니다. IAM, 키 정책, 그랜트를 통해 철저히 관리해야 합니다.

키를 삭제하면 해당 키로 암호화된 데이터는 영구적으로 복구할 수 없습니다. 삭제 전 7~30일의 대기 기간을 설정할 수 있습니다.

정기적으로 키를 교체하여 보안을 강화할 수 있습니다. 고객 관리형 키는 자동 로테이션을 설정할 수 있습니다.

키에 접근할 수 있는 사용자나 서비스를 최소화하는 것이 중요합니다. IAM, 키 정책, 그랜트를 통해 철저히 관리해야 합니다.


```javascript
import { KMSClient, GenerateDataKeyCommand } from '@aws-sdk/client-kms';
import crypto from 'crypto';

const kmsClient = new KMSClient({ region: 'ap-northeast-2' });

// 데이터 키 생성
async function generateDataKey(keyId) {
  const command = new GenerateDataKeyCommand({
    KeyId: keyId,
    KeySpec: 'AES_256'
  });
  
  const response = await kmsClient.send(command);
  return {
    plaintextKey: response.Plaintext,
    encryptedKey: response.CiphertextBlob
  };
}

// AES 암호화
function encryptWithAES(plaintext, key) {
  const iv = crypto.randomBytes(16);
  const cipher = crypto.createCipher('aes-256-cbc', key);
  let encrypted = cipher.update(plaintext, 'utf-8', 'hex');
  encrypted += cipher.final('hex');
  
  return {
    encrypted: encrypted,
    iv: iv.toString('hex')
  };
}

// AES 복호화
function decryptWithAES(encrypted, key, iv) {
  const decipher = crypto.createDecipher('aes-256-cbc', key);
  let decrypted = decipher.update(encrypted, 'hex', 'utf-8');
  decrypted += decipher.final('utf-8');
  
  return decrypted;
}

// 사용 예시
async function dataKeyExample() {
  const keyId = 'arn:aws:kms:ap-northeast-2:123456789012:key/abcd1234-5678-90ef-ghij-klmnopqrstuv';
  const originalData = '중요한 비밀 데이터';
  
  try {
    // 데이터 키 생성
    const { plaintextKey, encryptedKey } = await generateDataKey(keyId);
    
    // 데이터 암호화
    const { encrypted, iv } = encryptWithAES(originalData, plaintextKey);
    
    // 암호화된 데이터와 키를 저장
    const dataToStore = {
      encryptedData: encrypted,
      encryptedKey: encryptedKey.toString('base64'),
      iv: iv
    };
    
    console.log('저장할 데이터:', dataToStore);
    
    // 복호화 과정 (나중에)
    const retrievedKey = Buffer.from(dataToStore.encryptedKey, 'base64');
    const decryptedKey = await decryptData(retrievedKey);
    const decryptedData = decryptWithAES(dataToStore.encryptedData, decryptedKey, dataToStore.iv);
    
    console.log('복호화된 데이터:', decryptedData);
  } catch (error) {
    console.error('오류:', error);
  }
}
```

- **키 생성/보관**: 월별 소액 과금
- **암호화/복호화 요청**: 요청 건수에 따라 과금
- **AWS Free Tier**: 월 20,000건 무료 제공

- 리전 단위로 키 관리 (리전 간 복제 불가)
- 대량의 암호화/복호화 요청 시 비용 증가
- 일부 특수한 암호화 요구사항은 지원하지 않음











## KMS의 주요 기능

## KMS 구조와 용어

### CMK (Customer Master Key)
KMS에서 관리하는 주요 암호화 키입니다. 실제 데이터를 직접 암호화하지 않고, 데이터 키를 암호화하는 데 사용됩니다.

### 데이터 키 (Data Key)
실제 데이터를 암호화/복호화하는 데 사용되는 키입니다. CMK로 암호화되어 안전하게 저장됩니다.

### 키 정책 (Key Policy)
각 키에 적용되는 정책으로, 누가 어떤 작업을 수행할 수 있는지 정의합니다.

### 그랜트 (Grant)
특정 사용자나 서비스에 일시적으로 키 사용 권한을 부여하는 기능입니다.

## KMS 동작 원리

## AWS 서비스와의 연동

### S3 버킷 암호화
S3 버킷에 KMS 키를 설정하면, 업로드되는 모든 객체가 자동으로 암호화됩니다.

### EBS 볼륨 암호화
EC2 인스턴스의 EBS 볼륨을 KMS로 암호화할 수 있습니다. 스냅샷과 복제본도 자동으로 암호화됩니다.

### RDS 암호화
데이터베이스 인스턴스 생성 시 KMS 키를 지정하여 데이터를 암호화할 수 있습니다.

### Lambda 환경 변수 암호화
Lambda 함수의 환경 변수를 KMS로 암호화하여 저장할 수 있습니다.

## JavaScript 예시

### AWS SDK v3를 사용한 KMS 암호화/복호화

```javascript
import { KMSClient, EncryptCommand, DecryptCommand } from '@aws-sdk/client-kms';

const kmsClient = new KMSClient({ region: 'ap-northeast-2' });

// 데이터 암호화
async function encryptData(keyId, plaintext) {
  const command = new EncryptCommand({
    KeyId: keyId,
    Plaintext: Buffer.from(plaintext, 'utf-8')
  });
  
  const response = await kmsClient.send(command);
  return response.CiphertextBlob;
}

// 데이터 복호화
async function decryptData(ciphertextBlob) {
  const command = new DecryptCommand({
    CiphertextBlob: ciphertextBlob
  });
  
  const response = await kmsClient.send(command);
  return Buffer.from(response.Plaintext).toString('utf-8');
}

// 사용 예시
async function example() {
  const keyId = 'arn:aws:kms:ap-northeast-2:123456789012:key/abcd1234-5678-90ef-ghij-klmnopqrstuv';
  const originalText = '안녕하세요, 이것은 테스트 데이터입니다.';
  
  try {
    // 암호화
    const encryptedData = await encryptData(keyId, originalText);
    console.log('암호화된 데이터:', encryptedData);
    
    // 복호화
    const decryptedText = await decryptData(encryptedData);
    console.log('복호화된 데이터:', decryptedText);
  } catch (error) {
    console.error('오류:', error);
  }
}
```

