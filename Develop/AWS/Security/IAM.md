# AWS IAM (Identity and Access Management) 완벽 가이드

## 📋 목차
- [IAM이란?](#iam이란)
- [핵심 개념](#핵심-개념)
- [실제 사용법](#실제-사용법)
- [보안 강화](#보안-강화)
- [실무 팁](#실무-팁)

---

## IAM이란?

### 🎯 IAM의 정의
IAM은 **Identity and Access Management**의 줄임말로, AWS 계정 내에서 누가 어떤 리소스에 접근할 수 있는지를 관리하는 서비스입니다.

쉽게 비유하면, **아파트 관리 시스템**과 같습니다:
- 각 세대주(사용자)에게 열쇠(권한)를 나눠주는 것
- 공용시설(리소스)에 대한 접근을 제한하는 것
- 보안카드(MFA)로 추가 보안을 제공하는 것

### 🔍 왜 IAM이 필요한가?

**문제 상황:**
```javascript
// 만약 모든 개발자가 모든 AWS 리소스에 접근할 수 있다면?
const developer1 = {
  name: "김개발",
  access: "모든 AWS 서비스" // 위험!
};

const developer2 = {
  name: "이개발", 
  access: "모든 AWS 서비스" // 위험!
};
```

**IAM 적용 후:**
```javascript
// 각자 필요한 권한만 부여
const developer1 = {
  name: "김개발",
  access: ["S3 읽기", "EC2 시작/중지"] // 필요한 것만
};

const developer2 = {
  name: "이개발",
  access: ["RDS 관리", "CloudWatch 로그"] // 필요한 것만
};
```

---

## 핵심 개념

### 👤 사용자 (User)
AWS 계정에서 실제로 작업하는 개인이나 애플리케이션입니다.

**예시:**
```javascript
// 사용자 정의
const user = {
  name: "frontend-developer",
  type: "개발자",
  permissions: ["S3 읽기", "CloudFront 배포"],
  accessMethod: ["콘솔 로그인", "API 키"]
};
```

### 👥 그룹 (Group)
비슷한 역할을 하는 사용자들을 묶어놓은 집합입니다.

**예시:**
```javascript
// 그룹 정의
const frontendTeam = {
  name: "프론트엔드팀",
  members: ["김개발", "이개발", "박개발"],
  permissions: ["S3 읽기", "CloudFront 배포", "Route53 관리"],
  description: "웹사이트 프론트엔드 개발 및 배포 담당"
};

// 그룹에 사용자 추가
frontendTeam.addMember("새로운개발자");
```

### 🎭 역할 (Role)
특정 작업을 수행할 때 임시로 부여되는 권한의 집합입니다.

**실제 사용 예시:**
```javascript
// EC2 인스턴스가 S3에 접근하는 역할
const ec2ToS3Role = {
  name: "EC2-S3-Access-Role",
  trustedEntity: "EC2", // EC2만 이 역할을 사용할 수 있음
  permissions: ["s3:GetObject", "s3:PutObject"],
  resources: ["arn:aws:s3:::my-app-bucket/*"]
};

// Lambda 함수가 DynamoDB에 접근하는 역할
const lambdaToDynamoRole = {
  name: "Lambda-DynamoDB-Role", 
  trustedEntity: "Lambda",
  permissions: ["dynamodb:GetItem", "dynamodb:PutItem"],
  resources: ["arn:aws:dynamodb:*:*:table/UserTable"]
};
```

### 📜 정책 (Policy)
권한을 정의하는 JSON 문서입니다.

**정책 구조:**
```javascript
// 정책의 기본 구조
const policy = {
  Version: "2012-10-17", // 정책 언어 버전
  Statement: [
    {
      Sid: "S3ReadAccess", // 정책 식별자 (선택사항)
      Effect: "Allow", // Allow 또는 Deny
      Principal: "*", // 누구에게 적용할지
      Action: ["s3:GetObject", "s3:ListBucket"], // 어떤 작업을 허용할지
      Resource: ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/*"] // 어떤 리소스에 적용할지
    }
  ]
};
```

**실제 정책 예시들:**

1. **S3 버킷 읽기 전용 정책:**
```javascript
const s3ReadOnlyPolicy = {
  Version: "2012-10-17",
  Statement: [
    {
      Effect: "Allow",
      Action: [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      Resource: [
        "arn:aws:s3:::my-company-bucket",
        "arn:aws:s3:::my-company-bucket/*"
      ]
    }
  ]
};
```

2. **EC2 인스턴스 관리 정책:**
```javascript
const ec2ManagementPolicy = {
  Version: "2012-10-17", 
  Statement: [
    {
      Effect: "Allow",
      Action: [
        "ec2:DescribeInstances",
        "ec2:StartInstances", 
        "ec2:StopInstances",
        "ec2:TerminateInstances"
      ],
      Resource: "*"
    }
  ]
};
```

3. **조건부 접근 정책 (IP 제한):**
```javascript
const conditionalAccessPolicy = {
  Version: "2012-10-17",
  Statement: [
    {
      Effect: "Allow",
      Action: "s3:GetObject",
      Resource: "arn:aws:s3:::secure-bucket/*",
      Condition: {
        IpAddress: {
          "aws:SourceIp": ["192.168.1.0/24", "10.0.0.0/8"]
        }
      }
    }
  ]
};
```

---

## 실제 사용법

### 🛠️ 사용자 생성 및 관리

**1단계: 사용자 생성**
```javascript
// AWS SDK를 사용한 사용자 생성 예시
const AWS = require('aws-sdk');
const iam = new AWS.IAM();

const createUser = async (userName) => {
  const params = {
    UserName: userName,
    Path: '/developers/' // 사용자 경로 설정
  };
  
  try {
    const result = await iam.createUser(params).promise();
    console.log('사용자 생성 완료:', result.User.UserName);
    return result.User;
  } catch (error) {
    console.error('사용자 생성 실패:', error);
  }
};
```

**2단계: 그룹 생성 및 사용자 추가**
```javascript
const createGroupAndAddUser = async (groupName, userName) => {
  // 그룹 생성
  const createGroupParams = {
    GroupName: groupName,
    Path: '/teams/'
  };
  
  try {
    await iam.createGroup(createGroupParams).promise();
    console.log('그룹 생성 완료:', groupName);
    
    // 사용자를 그룹에 추가
    const addUserParams = {
      GroupName: groupName,
      UserName: userName
    };
    
    await iam.addUserToGroup(addUserParams).promise();
    console.log('사용자를 그룹에 추가 완료');
  } catch (error) {
    console.error('그룹 생성 또는 사용자 추가 실패:', error);
  }
};
```

**3단계: 정책 연결**
```javascript
const attachPolicyToGroup = async (groupName, policyArn) => {
  const params = {
    GroupName: groupName,
    PolicyArn: policyArn
  };
  
  try {
    await iam.attachGroupPolicy(params).promise();
    console.log('정책 연결 완료');
  } catch (error) {
    console.error('정책 연결 실패:', error);
  }
};

// 사용 예시
attachPolicyToGroup('frontend-team', 'arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess');
```

### 🔐 역할 생성 및 사용

**EC2 인스턴스용 역할 생성:**
```javascript
const createEC2Role = async (roleName) => {
  // 신뢰 관계 정책 (Trust Policy)
  const trustPolicy = {
    Version: "2012-10-17",
    Statement: [
      {
        Effect: "Allow",
        Principal: {
          Service: "ec2.amazonaws.com"
        },
        Action: "sts:AssumeRole"
      }
    ]
  };
  
  const params = {
    RoleName: roleName,
    AssumeRolePolicyDocument: JSON.stringify(trustPolicy),
    Description: "EC2 인스턴스가 S3에 접근하기 위한 역할"
  };
  
  try {
    const result = await iam.createRole(params).promise();
    console.log('역할 생성 완료:', result.Role.RoleName);
    
    // S3 접근 정책 연결
    await iam.attachRolePolicy({
      RoleName: roleName,
      PolicyArn: 'arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess'
    }).promise();
    
    return result.Role;
  } catch (error) {
    console.error('역할 생성 실패:', error);
  }
};
```

**Lambda 함수용 역할 생성:**
```javascript
const createLambdaRole = async (roleName) => {
  const trustPolicy = {
    Version: "2012-10-17",
    Statement: [
      {
        Effect: "Allow",
        Principal: {
          Service: "lambda.amazonaws.com"
        },
        Action: "sts:AssumeRole"
      }
    ]
  };
  
  const params = {
    RoleName: roleName,
    AssumeRolePolicyDocument: JSON.stringify(trustPolicy),
    Description: "Lambda 함수 실행을 위한 역할"
  };
  
  try {
    const result = await iam.createRole(params).promise();
    
    // Lambda 기본 실행 정책 연결
    await iam.attachRolePolicy({
      RoleName: roleName,
      PolicyArn: 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
    }).promise();
    
    return result.Role;
  } catch (error) {
    console.error('Lambda 역할 생성 실패:', error);
  }
};
```

---

## 보안 강화

### 🔐 MFA (Multi-Factor Authentication)

**MFA 설정 확인:**
```javascript
const checkMFAStatus = async (userName) => {
  const params = {
    UserName: userName
  };
  
  try {
    const result = await iam.listMFADevices(params).promise();
    
    if (result.MFADevices.length > 0) {
      console.log('MFA가 설정되어 있습니다:', result.MFADevices[0].SerialNumber);
      return true;
    } else {
      console.log('MFA가 설정되어 있지 않습니다.');
      return false;
    }
  } catch (error) {
    console.error('MFA 상태 확인 실패:', error);
  }
};
```

**MFA 강제 설정 정책:**
```javascript
const mfaRequiredPolicy = {
  Version: "2012-10-17",
  Statement: [
    {
      Sid: "DenyAllExceptListedIfNoMFA",
      Effect: "Deny",
      NotAction: [
        "iam:CreateVirtualMFADevice",
        "iam:EnableMFADevice", 
        "iam:GetUser",
        "iam:ListMFADevices",
        "iam:ListVirtualMFADevices",
        "iam:ResyncMFADevice"
      ],
      Resource: "*",
      Condition: {
        BoolIfExists: {
          "aws:MultiFactorAuthPresent": "false"
        }
      }
    }
  ]
};
```

### 🔍 액세스 키 관리

**액세스 키 생성:**
```javascript
const createAccessKey = async (userName) => {
  const params = {
    UserName: userName
  };
  
  try {
    const result = await iam.createAccessKey(params).promise();
    console.log('액세스 키 생성 완료');
    console.log('Access Key ID:', result.AccessKey.AccessKeyId);
    console.log('Secret Access Key:', result.AccessKey.SecretAccessKey);
    
    // 보안: Secret Access Key는 한 번만 표시되므로 안전한 곳에 저장해야 함
    return result.AccessKey;
  } catch (error) {
    console.error('액세스 키 생성 실패:', error);
  }
};
```

**오래된 액세스 키 비활성화:**
```javascript
const deactivateOldAccessKeys = async (userName, daysOld = 90) => {
  const params = {
    UserName: userName
  };
  
  try {
    const result = await iam.listAccessKeys(params).promise();
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - daysOld);
    
    for (const key of result.AccessKeyMetadata) {
      if (key.CreateDate < cutoffDate && key.Status === 'Active') {
        await iam.updateAccessKey({
          UserName: userName,
          AccessKeyId: key.AccessKeyId,
          Status: 'Inactive'
        }).promise();
        console.log(`액세스 키 비활성화: ${key.AccessKeyId}`);
      }
    }
  } catch (error) {
    console.error('액세스 키 관리 실패:', error);
  }
};
```

---

## 실무 팁

### 📊 권한 최적화

**사용자별 권한 분석:**
```javascript
const analyzeUserPermissions = async (userName) => {
  try {
    // 사용자가 속한 그룹 조회
    const groups = await iam.listGroupsForUser({ UserName: userName }).promise();
    
    // 직접 연결된 정책 조회
    const attachedPolicies = await iam.listAttachedUserPolicies({ UserName: userName }).promise();
    
    // 인라인 정책 조회
    const inlinePolicies = await iam.listUserPolicies({ UserName: userName }).promise();
    
    const permissions = {
      userName: userName,
      groups: groups.Groups.map(g => g.GroupName),
      attachedPolicies: attachedPolicies.AttachedPolicies.map(p => p.PolicyName),
      inlinePolicies: inlinePolicies.PolicyNames,
      totalPolicies: attachedPolicies.AttachedPolicies.length + inlinePolicies.PolicyNames.length
    };
    
    console.log('권한 분석 결과:', permissions);
    return permissions;
  } catch (error) {
    console.error('권한 분석 실패:', error);
  }
};
```

### 🚨 보안 모니터링

**비정상적인 로그인 시도 감지:**
```javascript
const monitorLoginAttempts = async () => {
  const cloudtrail = new AWS.CloudTrail();
  
  const params = {
    StartTime: new Date(Date.now() - 24 * 60 * 60 * 1000), // 24시간 전
    EndTime: new Date(),
    LookupAttributes: [
      {
        AttributeKey: 'EventName',
        AttributeValue: 'ConsoleLogin'
      }
    ]
  };
  
  try {
    const result = await cloudtrail.lookupEvents(params).promise();
    
    const failedLogins = result.Events.filter(event => 
      event.CloudTrailEvent && 
      JSON.parse(event.CloudTrailEvent).errorMessage
    );
    
    if (failedLogins.length > 0) {
      console.log('실패한 로그인 시도 발견:', failedLogins.length);
      failedLogins.forEach(login => {
        const event = JSON.parse(login.CloudTrailEvent);
        console.log(`- 사용자: ${event.userIdentity.userName}, 시간: ${login.EventTime}`);
      });
    }
  } catch (error) {
    console.error('로그인 모니터링 실패:', error);
  }
};
```

### 🔄 정책 버전 관리

**정책 변경 이력 추적:**
```javascript
const trackPolicyChanges = async (policyArn) => {
  try {
    const versions = await iam.listPolicyVersions({ PolicyArn: policyArn }).promise();
    
    console.log('정책 버전 목록:');
    versions.Versions.forEach(version => {
      console.log(`- 버전: ${version.VersionId}`);
      console.log(`  생성일: ${version.CreateDate}`);
      console.log(`  기본 버전: ${version.IsDefaultVersion}`);
      console.log('---');
    });
    
    return versions.Versions;
  } catch (error) {
    console.error('정책 버전 조회 실패:', error);
  }
};
```

---

## 📚 추가 학습 자료

- [AWS IAM 공식 문서](https://docs.aws.amazon.com/ko_kr/IAM/latest/UserGuide/introduction.html)
- [IAM 정책 시뮬레이터](https://policysim.aws.amazon.com/)
- [AWS 정책 생성기](https://awspolicygen.s3.amazonaws.com/policygen.html)
- [IAM Best Practices](https://docs.aws.amazon.com/ko_kr/IAM/latest/UserGuide/best-practices.html)

---

## 💡 마무리

IAM은 AWS 보안의 핵심입니다. 처음에는 복잡해 보일 수 있지만, 단계별로 학습하고 실제로 사용해보면서 익숙해지면 됩니다. 

가장 중요한 것은 **최소 권한 원칙**을 지키는 것입니다. 사용자에게 꼭 필요한 권한만 부여하고, 정기적으로 권한을 검토하여 보안을 유지하세요.

실무에서는 IAM을 통해 팀원들의 작업 효율성을 높이면서도 보안을 강화할 수 있습니다. 이 가이드가 AWS IAM을 이해하고 활용하는 데 도움이 되길 바랍니다! 🚀


