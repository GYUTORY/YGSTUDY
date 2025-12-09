---
title: SQL Injection (SQL 인젝션) 
tags: [database, security, sql-injection, web-security, owasp]
updated: 2025-12-09
---

# SQL Injection (SQL 인젝션)

## 정의

SQL 인젝션은 공격자가 웹 애플리케이션의 데이터베이스 쿼리를 조작할 수 있도록 하는 보안 취약점입니다. OWASP Top 10에서 가장 위험한 웹 애플리케이션 보안 취약점 중 하나입니다.

### 발생 원인
- 사용자 입력값의 불충분한 검증
- 동적 SQL 쿼리 생성 시 문자열 연결 사용
- 데이터베이스 오류 메시지의 과도한 노출
- 최소 권한 원칙 미준수

## 공격 방식

### 1. 기본 SQL 인젝션

```sql
-- 원본 쿼리
SELECT * FROM users WHERE username = '$username' AND password = '$password';

-- 공격자 입력
username: admin' --
password: anything

-- 변형된 쿼리
SELECT * FROM users WHERE username = 'admin' --' AND password = 'anything';
-- 패스워드 체크가 주석 처리되어 인증 우회
```

### 2. UNION 기반 공격

```sql
-- 원본 쿼리
SELECT product_name, price FROM products WHERE category = '$category';

-- 공격자 입력
category: Electronics' UNION SELECT username, password FROM users --

-- 변형된 쿼리
SELECT product_name, price FROM products WHERE category = 'Electronics' 
UNION SELECT username, password FROM users --';
-- 사용자 정보가 함께 조회됨
```

### 3. 블라인드 SQL 인젝션

오류 메시지가 표시되지 않아도 참/거짓 결과로 데이터를 추출합니다.

```sql
-- 조건부 응답
SELECT * FROM users WHERE id = 1 AND (SELECT LENGTH(password) FROM users WHERE username='admin') = 8;

-- 시간 기반
SELECT * FROM users WHERE id = 1 AND IF(LENGTH(password)=8, SLEEP(5), 0);
```

## 방어 방법

### 1. Prepared Statement (권장)

**Node.js (MySQL):**
```javascript
// 취약한 코드
const query = `SELECT * FROM users WHERE id = ${userId}`;
connection.query(query);

// 안전한 코드
const query = 'SELECT * FROM users WHERE id = ?';
connection.query(query, [userId]);
```

**Node.js (PostgreSQL):**
```javascript
const query = 'SELECT * FROM users WHERE username = $1 AND email = $2';
client.query(query, [username, email]);
```

### 2. ORM 사용

```javascript
// Sequelize
const users = await User.findAll({
  where: {
    age: { [Op.gt]: 30 }
  }
});

// TypeORM
const users = await userRepository.find({
  where: { age: MoreThan(30) }
});
```

### 3. 입력 검증

```javascript
function validateInput(input) {
  // Whitelist 방식
  if (!/^[a-zA-Z0-9_]+$/.test(input)) {
    throw new Error('Invalid input');
  }
  return input;
}

// 숫자 타입 검증
function validateNumericId(id) {
  const numId = parseInt(id, 10);
  if (isNaN(numId) || numId <= 0) {
    throw new Error('Invalid ID');
  }
  return numId;
}
```

### 4. 이스케이핑

```javascript
const mysql = require('mysql');
const connection = mysql.createConnection(config);

// MySQL escape 함수 사용
const safeUsername = connection.escape(username);
const query = `SELECT * FROM users WHERE username = ${safeUsername}`;
```

## 실전 보안 구현

### 통합 보안 미들웨어

```javascript
const express = require('express');
const app = express();

// SQL Injection 방어 미들웨어
function sqlInjectionProtection(req, res, next) {
  const sqlPatterns = [
    /(\bUNION\b|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b)/gi,
    /(-{2}|\/\*|\*\/|;|'|")/g,
    /(\bOR\b.*=.*\bOR\b)/gi,
    /(\bAND\b.*=.*\bAND\b)/gi
  ];

  const checkInput = (obj) => {
    for (const key in obj) {
      const value = String(obj[key]);
      for (const pattern of sqlPatterns) {
        if (pattern.test(value)) {
          return true;
        }
      }
    }
    return false;
  };

  if (checkInput(req.query) || checkInput(req.body) || checkInput(req.params)) {
    return res.status(400).json({ error: 'Invalid input detected' });
  }

  next();
}

app.use(sqlInjectionProtection);
```

### 데이터베이스 권한 관리

```sql
-- 최소 권한 원칙 적용
-- 애플리케이션용 사용자는 필요한 권한만 부여
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT, INSERT, UPDATE ON mydb.users TO 'app_user'@'localhost';
GRANT SELECT, INSERT, UPDATE ON mydb.orders TO 'app_user'@'localhost';

-- 읽기 전용 사용자
CREATE USER 'readonly_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT ON mydb.* TO 'readonly_user'@'localhost';

-- DROP, ALTER 등 위험한 권한은 부여하지 않음
```

## 취약점 탐지

### 자동화된 스캔

```javascript
class SQLInjectionScanner {
  constructor() {
    this.testPayloads = [
      "' OR '1'='1",
      "'; DROP TABLE users; --",
      "' UNION SELECT NULL, NULL, NULL --",
      "1' AND '1'='1",
      "1' AND '1'='2"
    ];
  }

  async scanEndpoint(url, params) {
    const vulnerabilities = [];

    for (const payload of this.testPayloads) {
      for (const key in params) {
        const testParams = { ...params, [key]: payload };
        const response = await this.sendRequest(url, testParams);

        if (this.detectVulnerability(response)) {
          vulnerabilities.push({
            parameter: key,
            payload,
            evidence: response.body.substring(0, 200)
          });
        }
      }
    }

    return vulnerabilities;
  }

  detectVulnerability(response) {
    const sqlErrorPatterns = [
      /mysql_fetch_array\(\)/i,
      /ORA-01756/i,
      /Microsoft OLE DB Provider/i,
      /PostgreSQL query failed/i
    ];

    return sqlErrorPatterns.some(pattern => pattern.test(response.body));
  }
}
```

## 참고

### 방어 전략 비교

| 방법 | 보안 수준 | 구현 난이도 | 성능 | 권장도 |
|------|----------|------------|------|--------|
| Prepared Statement | 높음 | 쉬움 | 좋음 | 강력 권장 |
| ORM | 중간-높음 | 쉬움 | 보통 | 권장 |
| Escaping | 낮음 | 쉬움 | 좋음 | 보조 수단 |
| 입력 검증 | 중간 | 보통 | 좋음 | 필수 |

### 관련 자료
- [OWASP SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection)
- [CWE-89: SQL Injection](https://cwe.mitre.org/data/definitions/89.html)
- [PortSwigger SQL Injection](https://portswigger.net/web-security/sql-injection)
