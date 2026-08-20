---
title: 모듈 패턴 (Module Pattern)
tags: [design-patterns, javascript, architecture]
updated: 2025-11-30
---

# 모듈 패턴 (Module Pattern)

## 목차

1. [배경](#배경)
   - [왜 모듈 패턴이 필요한가?](#왜-모듈-패턴이-필요한가)
   - [모듈 패턴의 핵심 개념](#모듈-패턴의-핵심-개념)
2. [핵심](#핵심)
   - [CommonJS 모듈 시스템](#1-commonjs-모듈-시스템)
   - [ES6 모듈 시스템](#2-es6-모듈-시스템)
   - [고급 모듈 패턴](#3-고급-모듈-패턴)
3. [실제 프로젝트에서의 모듈 패턴 활용](#실제-프로젝트에서의-모듈-패턴-활용)
   - [전자상거래 플랫폼 구축 사례](#1-전자상거래-플랫폼-구축-사례)
   - [모듈 패턴의 실제 활용 사례](#2-모듈-패턴의-실제-활용-사례)
4. [모듈 패턴 운영 가이드](#모듈-패턴-운영-가이드)
   - [성능 최적화 전략](#성능-최적화-전략)
   - [에러 처리 및 복구 전략](#에러-처리-및-복구-전략)
5. [모듈 시스템 비교 및 선택 가이드](#모듈-시스템-비교-및-선택-가이드)
6. [결론](#결론)
7. [참조 자료](#참조-자료)

---

## 배경

모듈 패턴은 현대 소프트웨어 개발에서 빠질 수 없는 디자인 패턴이다. JavaScript 생태계에서 특히 중요한데, JavaScript가 원래 모듈 시스템 없이 설계된 언어이기 때문이다.

### 왜 모듈 패턴이 필요한가?

초기 JavaScript 개발자는 모든 코드를 전역 스코프에 써야 했다. 그래서 이런 문제가 생겼다.

**전역 네임스페이스 오염**

```javascript
// ❌ 문제가 있는 코드: 전역 스코프에 모든 것이 노출됨
var userService = { /* ... */ };
var productService = { /* ... */ };
var orderService = { /* ... */ };

// 문제점:
// - 변수명 충돌 위험
// - 메모리 누수 가능성
// - 디버깅 어려움
```

**코드 의존성의 복잡성**

- 어떤 함수가 어떤 변수에 의존하는지 파악하기 어려움
- 코드 실행 순서에 대한 명확한 제어 부족
- 라이브러리 간 충돌 가능성

**유지보수의 어려움**

- 기능별 코드 분리 불가능
- 개별 기능 테스트의 복잡성
- 코드 재사용성 저하

### 모듈 패턴의 핵심 개념

#### 모듈(Module)

모듈은 독립된 기능 단위를 담은 파일이다. 각 모듈은 자기 스코프를 가지고, 명시적으로 내보내지 않은 코드는 밖에서 접근할 수 없다. **정보 은닉(Information Hiding)** 원칙을 코드로 옮긴 것이다.

#### Export와 Import

- **Export**: 모듈의 공개 인터페이스를 정의하는 메커니즘
- **Import**: 다른 모듈의 기능을 현재 모듈로 가져오는 메커니즘

이 둘로 모듈 간 의존 관계가 분명하게 잡힌다.

#### 스코프 격리

모듈 안의 변수와 함수는 기본이 **private**이고, 명시적으로 export한 것만 **public**이 된다. 캡슐화는 여기서 나온다.

#### 의존성 관리

모듈 시스템은 의존성 그래프를 뚜렷하게 만든다. 어떤 모듈이 어떤 모듈에 기대는지, 그 의존이 어느 방향으로 흐르는지 눈으로 확인할 수 있다.

## 핵심

### 1. CommonJS 모듈 시스템

CommonJS는 Node.js가 기본으로 쓰는 모듈 시스템이다. **동기적 로딩**과 **런타임 모듈 해석**이 특징이다.

#### CommonJS의 동작 원리

CommonJS 모듈은 이런 과정을 거쳐 로드된다.

1. **파일 시스템에서 모듈 파일 읽기**
2. **모듈 코드를 함수로 래핑**
3. **module.exports 객체 생성**
4. **모듈 코드 실행**
5. **module.exports 반환**

```javascript
// Node.js가 내부적으로 수행하는 작업 (의사코드)
function require(modulePath) {
    // 1. 모듈 경로 해석
    const resolvedPath = resolveModulePath(modulePath);
    
    // 2. 캐시 확인 - 이미 로드된 모듈은 캐시에서 반환
    if (Module._cache[resolvedPath]) {
        return Module._cache[resolvedPath].exports;
    }
    
    // 3. 새 모듈 객체 생성
    const module = new Module(resolvedPath);
    Module._cache[resolvedPath] = module;
    
    // 4. 모듈 코드 실행
    module.load();
    
    // 5. module.exports 반환
    return module.exports;
}
```

> CommonJS는 모듈을 동기적으로 로드하고, 한 번 로드한 모듈은 캐시에 남아 재사용된다.

#### 실용적인 모듈 설계 패턴

**1. 객체 기반 모듈 내보내기**

```javascript
// utils/stringUtils.js - 문자열 유틸리티 모듈
const StringUtils = {
    // 문자열 정규화
    normalize(str) {
        return str.trim().toLowerCase();
    },
    
    // 이메일 유효성 검사
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },
    
    // 문자열 마스킹 (보안용)
    maskString(str, visibleChars = 4) {
        if (str.length <= visibleChars) return str;
        const visible = str.slice(-visibleChars);
        const masked = '*'.repeat(str.length - visibleChars);
        return masked + visible;
    },
    
    // 카멜케이스 변환
    toCamelCase(str) {
        return str.replace(/-([a-z])/g, (match, letter) => letter.toUpperCase());
    }
};

module.exports = StringUtils;
```

> 관련 기능을 객체 하나로 묶어서 네임스페이스 오염을 막는 게 장점이다.

**2. 클래스 기반 모듈**

```javascript
// models/User.js - 사용자 모델 클래스
class User {
    constructor(data) {
        this.id = data.id;
        this.name = data.name;
        this.email = data.email;
        this.createdAt = data.createdAt || new Date();
        this.isActive = data.isActive !== undefined ? data.isActive : true;
    }
    
    // 사용자 정보 검증
    validate() {
        const errors = [];
        
        if (!this.name || this.name.trim().length < 2) {
            errors.push('이름은 2자 이상이어야 합니다.');
        }
        
        if (!this.email || !this.isValidEmail()) {
            errors.push('유효한 이메일 주소를 입력해주세요.');
        }
        
        return {
            isValid: errors.length === 0,
            errors
        };
    }
    
    isValidEmail() {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(this.email);
    }
    
    // 사용자 정보 업데이트
    update(updateData) {
        Object.keys(updateData).forEach(key => {
            if (this.hasOwnProperty(key) && key !== 'id' && key !== 'createdAt') {
                this[key] = updateData[key];
            }
        });
        return this;
    }
    
    // JSON 직렬화
    toJSON() {
        return {
            id: this.id,
            name: this.name,
            email: this.email,
            createdAt: this.createdAt,
            isActive: this.isActive
        };
    }
}

module.exports = User;
```

> 객체지향 프로그래밍의 캡슐화와 상속을 쓸 수 있는 게 장점이다.

**3. 팩토리 함수 패턴**
```javascript
// services/LoggerFactory.js - 로거 팩토리
const LoggerFactory = {
    // 로거 타입별 생성
    createLogger(type = 'default') {
        const loggers = {
            console: new ConsoleLogger(),
            file: new FileLogger(),
            database: new DatabaseLogger(),
            default: new DefaultLogger()
        };
        
        return loggers[type] || loggers.default;
    },
    
    // 설정 기반 로거 생성
    createFromConfig(config) {
        const logger = this.createLogger(config.type);
        logger.setLevel(config.level || 'info');
        logger.setFormat(config.format || 'simple');
        return logger;
    }
};

// 개별 로거 클래스들
class ConsoleLogger {
    log(message, level = 'info') {
        const timestamp = new Date().toISOString();
        console.log(`[${level.toUpperCase()}] ${timestamp}: ${message}`);
    }
}

class FileLogger {
    log(message, level = 'info') {
        // 파일 로깅 구현
        console.log(`FILE [${level.toUpperCase()}]: ${message}`);
    }
}

module.exports = LoggerFactory;
```

#### 모듈 사용의 실제 사례

```javascript
// app.js - 메인 애플리케이션
const StringUtils = require('./utils/stringUtils');
const User = require('./models/User');
const LoggerFactory = require('./services/LoggerFactory');

// 로거 설정
const logger = LoggerFactory.createFromConfig({
    type: 'console',
    level: 'info',
    format: 'detailed'
});

// 사용자 생성 및 검증
function createUser(userData) {
    try {
        // 입력 데이터 정규화
        const normalizedData = {
            name: StringUtils.normalize(userData.name),
            email: StringUtils.normalize(userData.email)
        };
        
        // 사용자 객체 생성
        const user = new User(normalizedData);
        
        // 유효성 검사
        const validation = user.validate();
        if (!validation.isValid) {
            throw new Error(`유효성 검사 실패: ${validation.errors.join(', ')}`);
        }
        
        logger.log(`새 사용자 생성: ${user.email}`);
        return user;
        
    } catch (error) {
        logger.log(`사용자 생성 실패: ${error.message}`, 'error');
        throw error;
    }
}

// 사용 예시
const userData = {
    name: '  김철수  ',
    email: 'KIM@EXAMPLE.COM'
};

const newUser = createUser(userData);
console.log('생성된 사용자:', newUser.toJSON());
```

### 2. ES6 모듈 시스템

ES6 모듈 시스템은 JavaScript의 공식 모듈 표준이다. CommonJS와 달리 **정적 분석**이 되고 **트리 쉐이킹**을 지원하며, **비동기 로딩**이 기본이다.

#### ES6 모듈의 핵심 특징

##### 정적 분석 (Static Analysis)

- 모듈의 의존성이 코드 실행 전에 결정됨
- 번들러가 최적화를 수행할 수 있음
- 순환 의존성 문제를 컴파일 타임에 감지 가능

##### 트리 쉐이킹 (Tree Shaking)

- 사용하지 않는 코드를 자동으로 제거
- 번들 크기 최적화에 큰 도움

트리 쉐이킹은 자동이 아니라 **조건부**다. 번들러는 "이 모듈을 평가해도 부수효과가 없다"고 확신할 때만 지운다. 아래 중 하나라도 걸리면 안 쓰는 코드가 그대로 남는다.

- 모듈 최상단에서 뭔가를 실행한다(등록, 프로토타입 확장, 폴리필). 번들러는 그게 필요한지 판단할 수 없다.
- 패키지가 `package.json` 에 `"sideEffects": false` 를 선언하지 않았다.
- CommonJS 로 배포된 패키지다. `require` 는 동적이라 무엇을 쓰는지 정적으로 알 수 없다.
- 배럴 파일(`index.js` 에 전부 re-export)을 거쳐 import 한다. 하나만 가져와도 배럴이 통째로 평가되면서 딸린 부수효과가 함께 들어온다.

마지막 항목은 이 문서 뒤쪽의 "모듈 통합" 구조와 정면으로 부딪힌다. 진입점 하나로 몰아서 export 하면 import 문은 깔끔해지지만 **번들러가 잘라낼 수 있는 자리가 줄어든다.** 편의와 번들 크기를 맞바꾸는 것이라, 크기가 상관없는 서버 코드에서는 배럴이 이득이고 브라우저 번들에서는 손해다.

##### 비동기 로딩

- 모듈을 비동기적으로 로드 가능
- 코드 스플리팅과 지연 로딩 구현 용이

#### ES6 모듈의 다양한 내보내기 패턴

**1. 명명된 내보내기 (Named Exports)**
```javascript
// utils/dateUtils.js - 날짜 유틸리티 모듈
export function formatDate(date, format = 'YYYY-MM-DD') {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    
    return format
        .replace('YYYY', year)
        .replace('MM', month)
        .replace('DD', day);
}

export function addDays(date, days) {
    const result = new Date(date);
    result.setDate(result.getDate() + days);
    return result;
}

export function isWeekend(date) {
    const day = date.getDay();
    return day === 0 || day === 6; // 일요일(0) 또는 토요일(6)
}

export function getBusinessDays(startDate, endDate) {
    let count = 0;
    const current = new Date(startDate);
    
    while (current <= endDate) {
        if (!isWeekend(current)) {
            count++;
        }
        current.setDate(current.getDate() + 1);
    }
    
    return count;
}

// 상수도 내보낼 수 있음
export const DATE_FORMATS = {
    ISO: 'YYYY-MM-DD',
    KOREAN: 'YYYY년 MM월 DD일',
    US: 'MM/DD/YYYY'
};
```

**2. 기본 내보내기 (Default Export)**
```javascript
// services/EmailService.js - 이메일 서비스
class EmailService {
    constructor(config) {
        this.smtpHost = config.smtpHost;
        this.smtpPort = config.smtpPort;
        this.username = config.username;
        this.password = config.password;
        this.isConnected = false;
    }
    
    async connect() {
        if (this.isConnected) return;
        
        // SMTP 연결 로직
        console.log(`SMTP 서버 연결: ${this.smtpHost}:${this.smtpPort}`);
        this.isConnected = true;
    }
    
    async sendEmail(to, subject, body) {
        if (!this.isConnected) {
            await this.connect();
        }
        
        const emailData = {
            to,
            subject,
            body,
            timestamp: new Date().toISOString()
        };
        
        console.log('이메일 발송:', emailData);
        return { success: true, messageId: `msg_${Date.now()}` };
    }
    
    async sendBulkEmails(emails) {
        const results = [];
        
        for (const email of emails) {
            try {
                const result = await this.sendEmail(email.to, email.subject, email.body);
                results.push({ ...result, to: email.to });
            } catch (error) {
                results.push({ 
                    success: false, 
                    to: email.to, 
                    error: error.message 
                });
            }
        }
        
        return results;
    }
}

// 기본 내보내기
export default EmailService;
```

**3. 혼합 내보내기 (Mixed Exports)**
```javascript
// models/Product.js - 상품 모델
export class Product {
    constructor(data) {
        this.id = data.id;
        this.name = data.name;
        this.price = data.price;
        this.category = data.category;
        this.inStock = data.inStock || false;
        this.createdAt = data.createdAt || new Date();
    }
    
    // 가격 포맷팅
    getFormattedPrice() {
        return new Intl.NumberFormat('ko-KR', {
            style: 'currency',
            currency: 'KRW'
        }).format(this.price);
    }
    
    // 재고 상태 확인
    isAvailable() {
        return this.inStock && this.price > 0;
    }
    
    // 상품 정보 업데이트
    update(updateData) {
        Object.keys(updateData).forEach(key => {
            if (this.hasOwnProperty(key) && key !== 'id' && key !== 'createdAt') {
                this[key] = updateData[key];
            }
        });
        return this;
    }
    
    // JSON 직렬화
    toJSON() {
        return {
            id: this.id,
            name: this.name,
            price: this.price,
            formattedPrice: this.getFormattedPrice(),
            category: this.category,
            inStock: this.inStock,
            isAvailable: this.isAvailable(),
            createdAt: this.createdAt
        };
    }
}

// 유틸리티 함수들
export function validateProduct(productData) {
    const errors = [];
    
    if (!productData.name || productData.name.trim().length < 2) {
        errors.push('상품명은 2자 이상이어야 합니다.');
    }
    
    if (!productData.price || productData.price <= 0) {
        errors.push('가격은 0보다 커야 합니다.');
    }
    
    if (!productData.category) {
        errors.push('카테고리를 선택해주세요.');
    }
    
    return {
        isValid: errors.length === 0,
        errors
    };
}

export function calculateDiscount(price, discountRate) {
    if (discountRate < 0 || discountRate > 1) {
        throw new Error('할인율은 0과 1 사이의 값이어야 합니다.');
    }
    return price * (1 - discountRate);
}

export function sortProductsByPrice(products, ascending = true) {
    return [...products].sort((a, b) => {
        return ascending ? a.price - b.price : b.price - a.price;
    });
}

// 상수
export const PRODUCT_CATEGORIES = {
    ELECTRONICS: 'electronics',
    CLOTHING: 'clothing',
    BOOKS: 'books',
    HOME: 'home',
    SPORTS: 'sports'
};

// 기본 내보내기 (클래스)
export default Product;
```

#### ES6 모듈의 다양한 가져오기 패턴

```javascript
// main.js - 메인 애플리케이션
import Product, { 
    validateProduct, 
    calculateDiscount, 
    sortProductsByPrice,
    PRODUCT_CATEGORIES 
} from './models/Product.js';

import EmailService from './services/EmailService.js';
import { formatDate, addDays, getBusinessDays } from './utils/dateUtils.js';

// 이메일 서비스 설정
const emailService = new EmailService({
    smtpHost: 'smtp.gmail.com',
    smtpPort: 587,
    username: 'admin@example.com',
    password: 'password123'
});

// 상품 관리 시스템
class ProductManager {
    constructor() {
        this.products = [];
    }
    
    addProduct(productData) {
        const validation = validateProduct(productData);
        if (!validation.isValid) {
            throw new Error(`상품 검증 실패: ${validation.errors.join(', ')}`);
        }
        
        const product = new Product({
            ...productData,
            id: this.generateId()
        });
        
        this.products.push(product);
        return product;
    }
    
    getProductsByCategory(category) {
        return this.products.filter(product => product.category === category);
    }
    
    applyDiscount(category, discountRate) {
        const categoryProducts = this.getProductsByCategory(category);
        
        return categoryProducts.map(product => {
            const discountedPrice = calculateDiscount(product.price, discountRate);
            return product.update({ price: discountedPrice });
        });
    }
    
    async notifyLowStock() {
        const lowStockProducts = this.products.filter(product => !product.inStock);
        
        if (lowStockProducts.length > 0) {
            const emailBody = lowStockProducts
                .map(product => `- ${product.name} (${product.getFormattedPrice()})`)
                .join('\n');
            
            await emailService.sendEmail(
                'admin@example.com',
                '재고 부족 알림',
                `다음 상품들의 재고가 부족합니다:\n\n${emailBody}`
            );
        }
    }
    
    generateId() {
        return `prod_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}

// 사용 예시
const productManager = new ProductManager();

// 상품 추가
const laptop = productManager.addProduct({
    name: '맥북 프로 16인치',
    price: 3500000,
    category: PRODUCT_CATEGORIES.ELECTRONICS,
    inStock: true
});

const book = productManager.addProduct({
    name: 'JavaScript 가이드',
    price: 45000,
    category: PRODUCT_CATEGORIES.BOOKS,
    inStock: false
});

console.log('추가된 상품들:');
console.log(laptop.toJSON());
console.log(book.toJSON());

// 할인 적용
const discountedElectronics = productManager.applyDiscount(
    PRODUCT_CATEGORIES.ELECTRONICS, 
    0.1 // 10% 할인
);

console.log('할인된 전자제품들:', discountedElectronics);

// 재고 부족 알림
productManager.notifyLowStock();
```

### 3. 고급 모듈 패턴

실제 프로덕션에서는 단순히 모듈을 내보내는 것보다 정교한 패턴이 필요하다. 개발하면서 자주 쓰는 고급 패턴을 보자.

#### 싱글톤 패턴을 활용한 모듈

싱글톤 패턴은 애플리케이션 전체에서 인스턴스가 하나뿐이어야 하는 객체에 쓴다. 데이터베이스 연결, 설정 관리자, 로거가 대표적이다.

```javascript
// config/AppConfig.js - 애플리케이션 설정 관리자
class AppConfig {
    constructor() {
        if (AppConfig.instance) {
            return AppConfig.instance;
        }
        
        this.config = new Map();
        this.isLoaded = false;
        AppConfig.instance = this;
    }
    
    // 설정 로드
    async loadConfig() {
        if (this.isLoaded) return this.config;
        
        try {
            // 환경 변수에서 설정 로드
            this.config.set('database.host', process.env.DB_HOST || 'localhost');
            this.config.set('database.port', parseInt(process.env.DB_PORT) || 5432);
            this.config.set('database.name', process.env.DB_NAME || 'myapp');
            this.config.set('jwt.secret', process.env.JWT_SECRET || 'default-secret');
            this.config.set('jwt.expiresIn', process.env.JWT_EXPIRES_IN || '24h');
            this.config.set('server.port', parseInt(process.env.PORT) || 3000);
            this.config.set('server.env', process.env.NODE_ENV || 'development');
            
            this.isLoaded = true;
            console.log('애플리케이션 설정이 로드되었습니다.');
            
        } catch (error) {
            console.error('설정 로드 실패:', error);
            throw error;
        }
        
        return this.config;
    }
    
    // 설정 값 가져오기
    get(key, defaultValue = null) {
        return this.config.get(key) || defaultValue;
    }
    
    // 설정 값 설정하기
    set(key, value) {
        this.config.set(key, value);
    }
    
    // 모든 설정 가져오기
    getAll() {
        return Object.fromEntries(this.config);
    }
    
    // 설정 검증
    validate() {
        const requiredKeys = [
            'database.host',
            'database.port', 
            'database.name',
            'jwt.secret'
        ];
        
        const missing = requiredKeys.filter(key => !this.config.has(key));
        
        if (missing.length > 0) {
            throw new Error(`필수 설정이 누락되었습니다: ${missing.join(', ')}`);
        }
        
        return true;
    }
}

// 싱글톤 인스턴스 내보내기
const appConfig = new AppConfig();
export default appConfig;
```

#### 이 싱글톤이 하나라는 보장은 모듈 캐시에서 온다

`AppConfig.instance` 트릭이 붙어 있지만, 인스턴스를 실제로 하나로 묶는 것은 **모듈 캐시**다. 캐시가 갈라지면 싱글톤도 갈라진다. 갈라지는 경로가 셋 있다.

**같은 패키지가 두 번 설치된 경우.** 캐시 키는 해석된 파일 경로다. `node_modules/config` 와 `node_modules/a/node_modules/config` 는 다른 파일이라 인스턴스가 둘이 된다.

**지정자가 다른 경우.** 같은 파일이어도 ESM 에서 쿼리스트링이 붙으면 별개 모듈로 평가된다.

```javascript
const a = await import('./cfg.mjs');
const b = await import('./cfg.mjs?v=2');
a.default === b.default;   // false
```

**CJS 빌드와 ESM 빌드를 함께 배포한 경우.** `exports` 필드로 `import` 와 `require` 에 다른 파일을 물려 두면 한 프로세스에서 두 진입점이 모두 로드될 수 있다. 실제로 돌려 보면 이렇다.

```
import 한 것: ESM 빌드 | require 한 것: CJS 빌드
같은 객체인가? false | CJS 쪽에서 조회: undefined
```

ESM 쪽에서 설정을 넣고 CJS 쪽에서 읽으면 없는 값이 된다. 상태를 담은 모듈 싱글톤을 만들 거면 이 셋 중 어디에도 걸리지 않는지 봐야 하고, 확실히 하려면 `globalThis` 에 심볼 키로 붙들거나 애초에 인자로 넘긴다.

덧붙여 `new AppConfig()` 가 기존 인스턴스를 반환하는 트릭은 **`new` 인데 새 객체가 아니라는 점**이 함정이다. 상속하면 서브클래스 인스턴스를 만들어도 부모 인스턴스가 나온다. `validate()` 도 `loadConfig()` 전에 부르면 항상 실패하는데, 이 순서 의존을 강제하는 장치가 없다.

#### `get()` 이 `false` 와 `0` 을 기본값으로 덮어쓴다

```javascript
get(key, defaultValue = null) {
    return this.config.get(key) || defaultValue;
}
```

`||` 는 falsy 를 전부 걸러낸다. 저장된 값이 `false`, `0`, `''` 이면 있는데도 기본값이 나간다.

```javascript
cfg.set('feature.enabled', false);
cfg.get('feature.enabled', true);   // → true   기능이 켜진다
cfg.set('retry.count', 0);
cfg.get('retry.count', 3);          // → 3      재시도를 끄려던 설정
cfg.set('prefix', '');
cfg.get('prefix', 'app-');          // → 'app-'
```

설정값은 `false` 와 `0` 이 의미를 갖는 자리라, 이 실수가 **기능 플래그를 반대로 켜는** 형태로 나타난다. `has()` 로 분기하거나 `??` 를 쓴다.

```javascript
get(key, defaultValue = null) {
    return this.config.has(key) ? this.config.get(key) : defaultValue;
}
```

같은 문제가 `loadConfig()` 안에도 있다. `parseInt(process.env.DB_PORT) || 5432` 는 포트를 `0` 으로 지정하면 5432 가 되고, `parseInt('3000abc')` 는 조용히 `3000` 을 통과시킨다. 환경변수는 전부 문자열이라 변환 실패를 명시적으로 걸러야 한다.

#### 팩토리 패턴을 활용한 모듈

팩토리 패턴은 객체를 만드는 복잡한 과정을 숨긴다. 여러 타입의 객체를 만들어야 할 때 쓴다.

```javascript
// services/NotificationFactory.js - 알림 서비스 팩토리
class NotificationService {
    constructor(type, config) {
        this.type = type;
        this.config = config;
        this.isInitialized = false;
    }
    
    async initialize() {
        if (this.isInitialized) return;
        
        switch (this.type) {
            case 'email':
                await this.initializeEmailService();
                break;
            case 'sms':
                await this.initializeSMSService();
                break;
            case 'push':
                await this.initializePushService();
                break;
            default:
                throw new Error(`지원하지 않는 알림 타입: ${this.type}`);
        }
        
        this.isInitialized = true;
    }
    
    async initializeEmailService() {
        console.log('이메일 서비스 초기화 중...');
        // 실제 이메일 서비스 초기화 로직
    }
    
    async initializeSMSService() {
        console.log('SMS 서비스 초기화 중...');
        // 실제 SMS 서비스 초기화 로직
    }
    
    async initializePushService() {
        console.log('푸시 알림 서비스 초기화 중...');
        // 실제 푸시 알림 서비스 초기화 로직
    }
    
    async send(message, recipient) {
        if (!this.isInitialized) {
            await this.initialize();
        }
        
        const notification = {
            type: this.type,
            message,
            recipient,
            timestamp: new Date().toISOString(),
            status: 'pending'
        };
        
        try {
            const result = await this.deliverNotification(notification);
            notification.status = 'sent';
            notification.deliveryId = result.id;
            
            console.log(`${this.type} 알림 발송 성공:`, notification);
            return notification;
            
        } catch (error) {
            notification.status = 'failed';
            notification.error = error.message;
            
            console.error(`${this.type} 알림 발송 실패:`, notification);
            throw error;
        }
    }
    
    async deliverNotification(notification) {
        // 실제 알림 발송 로직 (타입별로 다름)
        return { id: `notif_${Date.now()}` };
    }
}

// 팩토리 함수들
export function createNotificationService(type, config = {}) {
    return new NotificationService(type, config);
}

export function createEmailService(config) {
    return createNotificationService('email', {
        smtpHost: 'smtp.gmail.com',
        smtpPort: 587,
        ...config
    });
}

export function createSMSService(config) {
    return createNotificationService('sms', {
        apiKey: process.env.SMS_API_KEY,
        ...config
    });
}

export function createPushService(config) {
    return createNotificationService('push', {
        firebaseConfig: process.env.FIREBASE_CONFIG,
        ...config
    });
}

// 미리 설정된 서비스들
export const emailService = createEmailService();
export const smsService = createSMSService();
export const pushService = createPushService();
```

#### 의존성 주입을 활용한 모듈

의존성 주입은 모듈 사이의 결합도를 낮추고 테스트하기 쉽게 만드는 중요한 패턴이다.

```javascript
// container/ServiceContainer.js - 서비스 컨테이너
class ServiceContainer {
    constructor() {
        this.services = new Map();
        this.singletons = new Map();
        this.factories = new Map();
    }
    
    // 서비스 등록
    register(name, factory, options = {}) {
        const { singleton = false, dependencies = [] } = options;
        
        this.services.set(name, {
            factory,
            singleton,
            dependencies
        });
    }
    
    // 팩토리 등록
    registerFactory(name, factory) {
        this.factories.set(name, factory);
    }
    
    // 서비스 해결
    resolve(name) {
        // 팩토리에서 먼저 확인
        if (this.factories.has(name)) {
            return this.factories.get(name)(this);
        }
        
        const service = this.services.get(name);
        if (!service) {
            throw new Error(`서비스 '${name}'이 등록되지 않았습니다.`);
        }
        
        // 싱글톤인 경우 캐시 확인
        if (service.singleton && this.singletons.has(name)) {
            return this.singletons.get(name);
        }
        
        // 의존성 해결
        const resolvedDependencies = service.dependencies.map(dep => this.resolve(dep));
        
        // 서비스 인스턴스 생성
        const instance = service.factory(...resolvedDependencies);
        
        // 싱글톤인 경우 캐시에 저장
        if (service.singleton) {
            this.singletons.set(name, instance);
        }
        
        return instance;
    }
    
    // 컨테이너 초기화
    async initialize() {
        console.log('서비스 컨테이너 초기화 중...');
        
        // 모든 서비스를 순서대로 초기화
        for (const [name, service] of this.services) {
            if (service.singleton) {
                await this.resolve(name);
            }
        }
        
        console.log('서비스 컨테이너 초기화 완료');
    }
}

// 서비스 등록 예시
const container = new ServiceContainer();

// 데이터베이스 서비스
container.register('database', (config) => {
    return {
        async connect() {
            console.log(`데이터베이스 연결: ${config.get('database.host')}`);
            return { connected: true };
        },
        async query(sql) {
            console.log(`쿼리 실행: ${sql}`);
            return [];
        }
    };
}, { singleton: true, dependencies: ['config'] });

// 사용자 서비스
container.register('userService', (database, logger) => {
    return {
        async createUser(userData) {
            logger.log('사용자 생성 요청');
            const result = await database.query('INSERT INTO users...');
            logger.log('사용자 생성 완료');
            return result;
        },
        
        async getUserById(id) {
            logger.log(`사용자 조회: ${id}`);
            const result = await database.query(`SELECT * FROM users WHERE id = ${id}`);
            return result[0];
        }
    };
}, { dependencies: ['database', 'logger'] });

// 로거 서비스
container.register('logger', () => {
    return {
        log(message) {
            console.log(`[LOG] ${new Date().toISOString()}: ${message}`);
        },
        error(message) {
            console.error(`[ERROR] ${new Date().toISOString()}: ${message}`);
        }
    };
}, { singleton: true });

// 설정 서비스
container.register('config', () => {
    return {
        get(key) {
            return process.env[key] || 'default-value';
        }
    };
}, { singleton: true });

export default container;
```

## 실제 프로젝트에서의 모듈 패턴 활용

### 1. 전자상거래 플랫폼 구축 사례

실제로 굴러가는 전자상거래 플랫폼을 만든다고 해보자. 이런 규모에서는 모듈 패턴이 코드 구조와 유지보수를 어떻게 끌어올리는지 눈에 잘 보인다.

#### 프로젝트 구조 설계

```
ecommerce-platform/
├── src/
│   ├── config/           # 설정 관련 모듈들
│   ├── models/           # 데이터 모델들
│   ├── services/         # 비즈니스 로직 서비스들
│   ├── controllers/      # API 컨트롤러들
│   ├── middleware/       # 미들웨어들
│   ├── utils/           # 유틸리티 함수들
│   └── routes/          # 라우트 정의들
```

#### 핵심 모듈들의 구현

**1. 설정 관리 모듈**
```javascript
// config/index.js - 중앙 설정 관리
import appConfig from './AppConfig.js';
import databaseConfig from './DatabaseConfig.js';
import redisConfig from './RedisConfig.js';

class ConfigManager {
    constructor() {
        this.configs = new Map();
        this.isInitialized = false;
    }
    
    async initialize() {
        if (this.isInitialized) return;
        
        try {
            // 각 설정 모듈 초기화
            await appConfig.loadConfig();
            await databaseConfig.loadConfig();
            await redisConfig.loadConfig();
            
            // 설정들을 중앙에서 관리
            this.configs.set('app', appConfig);
            this.configs.set('database', databaseConfig);
            this.configs.set('redis', redisConfig);
            
            this.isInitialized = true;
            console.log('모든 설정이 성공적으로 로드되었습니다.');
            
        } catch (error) {
            console.error('설정 초기화 실패:', error);
            throw error;
        }
    }
    
    get(section, key) {
        const config = this.configs.get(section);
        return config ? config.get(key) : null;
    }
    
    getAll(section) {
        const config = this.configs.get(section);
        return config ? config.getAll() : {};
    }
}

const configManager = new ConfigManager();
export default configManager;
```

**2. 상품 관리 모듈**
```javascript
// models/Product.js - 상품 모델
export class Product {
    constructor(data) {
        this.id = data.id;
        this.name = data.name;
        this.description = data.description;
        this.price = data.price;
        this.category = data.category;
        this.sku = data.sku;
        this.stock = data.stock || 0;
        this.isActive = data.isActive !== undefined ? data.isActive : true;
        this.images = data.images || [];
        this.tags = data.tags || [];
        this.createdAt = data.createdAt || new Date();
        this.updatedAt = data.updatedAt || new Date();
    }
    
    // 재고 확인
    isInStock() {
        return this.stock > 0 && this.isActive;
    }
    
    // 재고 차감
    reduceStock(quantity) {
        if (this.stock < quantity) {
            throw new Error('재고가 부족합니다.');
        }
        this.stock -= quantity;
        this.updatedAt = new Date();
        return this;
    }
    
    // 재고 추가
    addStock(quantity) {
        this.stock += quantity;
        this.updatedAt = new Date();
        return this;
    }
    
    // 가격 포맷팅
    getFormattedPrice() {
        return new Intl.NumberFormat('ko-KR', {
            style: 'currency',
            currency: 'KRW'
        }).format(this.price);
    }
    
    // 할인 가격 계산
    calculateDiscountedPrice(discountRate) {
        if (discountRate < 0 || discountRate > 1) {
            throw new Error('할인율은 0과 1 사이의 값이어야 합니다.');
        }
        return Math.round(this.price * (1 - discountRate));
    }
    
    // 상품 검증
    validate() {
        const errors = [];
        
        if (!this.name || this.name.trim().length < 2) {
            errors.push('상품명은 2자 이상이어야 합니다.');
        }
        
        if (!this.price || this.price <= 0) {
            errors.push('가격은 0보다 커야 합니다.');
        }
        
        if (!this.sku || this.sku.trim().length === 0) {
            errors.push('SKU는 필수입니다.');
        }
        
        if (this.stock < 0) {
            errors.push('재고는 음수일 수 없습니다.');
        }
        
        return {
            isValid: errors.length === 0,
            errors
        };
    }
    
    // JSON 직렬화
    toJSON() {
        return {
            id: this.id,
            name: this.name,
            description: this.description,
            price: this.price,
            formattedPrice: this.getFormattedPrice(),
            category: this.category,
            sku: this.sku,
            stock: this.stock,
            isInStock: this.isInStock(),
            isActive: this.isActive,
            images: this.images,
            tags: this.tags,
            createdAt: this.createdAt,
            updatedAt: this.updatedAt
        };
    }
}

// 상품 관련 유틸리티 함수들
export function validateProductData(productData) {
    const errors = [];
    
    if (!productData.name || productData.name.trim().length < 2) {
        errors.push('상품명은 2자 이상이어야 합니다.');
    }
    
    if (!productData.price || productData.price <= 0) {
        errors.push('가격은 0보다 커야 합니다.');
    }
    
    if (!productData.sku || productData.sku.trim().length === 0) {
        errors.push('SKU는 필수입니다.');
    }
    
    return {
        isValid: errors.length === 0,
        errors
    };
}

export function generateSKU(category, name) {
    const categoryCode = category.substring(0, 3).toUpperCase();
    const nameCode = name.substring(0, 3).toUpperCase();
    const timestamp = Date.now().toString().slice(-6);
    return `${categoryCode}-${nameCode}-${timestamp}`;
}

export function sortProductsByPrice(products, ascending = true) {
    return [...products].sort((a, b) => {
        return ascending ? a.price - b.price : b.price - a.price;
    });
}

export function filterProductsByCategory(products, category) {
    return products.filter(product => product.category === category);
}

export function searchProducts(products, searchTerm) {
    const term = searchTerm.toLowerCase();
    return products.filter(product => 
        product.name.toLowerCase().includes(term) ||
        product.description.toLowerCase().includes(term) ||
        product.tags.some(tag => tag.toLowerCase().includes(term))
    );
}
```

**3. 주문 처리 서비스**
```javascript
// services/OrderService.js - 주문 처리 서비스
import { Product } from '../models/Product.js';
import { User } from '../models/User.js';
import { emailService } from './NotificationFactory.js';
import container from '../container/ServiceContainer.js';

export class OrderService {
    constructor() {
        this.orders = new Map();
        this.logger = container.resolve('logger');
        this.database = container.resolve('database');
    }
    
    // 주문 생성
    async createOrder(userId, orderItems) {
        try {
            this.logger.log(`주문 생성 시작 - 사용자: ${userId}`);
            
            // 주문 검증
            await this.validateOrder(userId, orderItems);
            
            // 주문 객체 생성
            const order = {
                id: this.generateOrderId(),
                userId,
                items: orderItems,
                status: 'pending',
                totalAmount: this.calculateTotalAmount(orderItems),
                createdAt: new Date(),
                updatedAt: new Date()
            };
            
            // 재고 차감
            await this.reduceStockForItems(orderItems);
            
            // 주문 저장
            this.orders.set(order.id, order);
            await this.saveOrderToDatabase(order);
            
            // 사용자에게 주문 확인 이메일 발송
            await this.sendOrderConfirmationEmail(userId, order);
            
            this.logger.log(`주문 생성 완료 - 주문 ID: ${order.id}`);
            return order;
            
        } catch (error) {
            this.logger.error(`주문 생성 실패: ${error.message}`);
            throw error;
        }
    }
    
    // 주문 검증
    async validateOrder(userId, orderItems) {
        if (!userId) {
            throw new Error('사용자 ID가 필요합니다.');
        }
        
        if (!orderItems || orderItems.length === 0) {
            throw new Error('주문 항목이 필요합니다.');
        }
        
        // 각 주문 항목 검증
        for (const item of orderItems) {
            const product = await this.getProductById(item.productId);
            
            if (!product) {
                throw new Error(`상품을 찾을 수 없습니다: ${item.productId}`);
            }
            
            if (!product.isInStock()) {
                throw new Error(`상품이 품절되었습니다: ${product.name}`);
            }
            
            if (product.stock < item.quantity) {
                throw new Error(`재고가 부족합니다: ${product.name} (요청: ${item.quantity}, 재고: ${product.stock})`);
            }
        }
    }
    
    // 재고 차감
    async reduceStockForItems(orderItems) {
        for (const item of orderItems) {
            const product = await this.getProductById(item.productId);
            product.reduceStock(item.quantity);
            await this.updateProductInDatabase(product);
        }
    }
    
    // 총 금액 계산
    calculateTotalAmount(orderItems) {
        return orderItems.reduce((total, item) => {
            return total + (item.price * item.quantity);
        }, 0);
    }
    
    // 주문 확인 이메일 발송
    async sendOrderConfirmationEmail(userId, order) {
        try {
            const user = await this.getUserById(userId);
            const emailBody = this.generateOrderEmailBody(order);
            
            await emailService.send(
                `주문이 접수되었습니다 (주문번호: ${order.id})`,
                user.email,
                emailBody
            );
            
            this.logger.log(`주문 확인 이메일 발송 완료 - 사용자: ${user.email}`);
            
        } catch (error) {
            this.logger.error(`주문 확인 이메일 발송 실패: ${error.message}`);
            // 이메일 발송 실패는 주문 처리에 영향을 주지 않음
        }
    }
    
    // 주문 이메일 본문 생성
    generateOrderEmailBody(order) {
        const itemsList = order.items.map(item => 
            `- ${item.name} x ${item.quantity} = ${item.price * item.quantity}원`
        ).join('\n');
        
        return `
안녕하세요!

주문이 성공적으로 접수되었습니다.

주문번호: ${order.id}
주문일시: ${order.createdAt.toLocaleString('ko-KR')}

주문 내역:
${itemsList}

총 금액: ${order.totalAmount.toLocaleString()}원

감사합니다.
        `.trim();
    }
    
    // 주문 상태 업데이트
    async updateOrderStatus(orderId, status) {
        const order = this.orders.get(orderId);
        if (!order) {
            throw new Error('주문을 찾을 수 없습니다.');
        }
        
        order.status = status;
        order.updatedAt = new Date();
        
        await this.updateOrderInDatabase(order);
        this.logger.log(`주문 상태 업데이트 - 주문 ID: ${orderId}, 상태: ${status}`);
        
        return order;
    }
    
    // 주문 조회
    async getOrderById(orderId) {
        const order = this.orders.get(orderId);
        if (!order) {
            throw new Error('주문을 찾을 수 없습니다.');
        }
        return order;
    }
    
    // 사용자별 주문 조회
    async getOrdersByUserId(userId) {
        const userOrders = Array.from(this.orders.values())
            .filter(order => order.userId === userId)
            .sort((a, b) => b.createdAt - a.createdAt);
        
        return userOrders;
    }
    
    // 주문 ID 생성
    generateOrderId() {
        const timestamp = Date.now().toString();
        const random = Math.random().toString(36).substr(2, 5);
        return `ORD-${timestamp}-${random}`.toUpperCase();
    }
    
    // 데이터베이스 관련 메서드들 (실제 구현에서는 ORM 사용)
    async getProductById(productId) {
        // 실제로는 데이터베이스에서 조회
        return this.database.query(`SELECT * FROM products WHERE id = ?`, [productId]);
    }
    
    async getUserById(userId) {
        // 실제로는 데이터베이스에서 조회
        return this.database.query(`SELECT * FROM users WHERE id = ?`, [userId]);
    }
    
    async saveOrderToDatabase(order) {
        // 실제로는 데이터베이스에 저장
        return this.database.query(`INSERT INTO orders SET ?`, [order]);
    }
    
    async updateOrderInDatabase(order) {
        // 실제로는 데이터베이스 업데이트
        return this.database.query(`UPDATE orders SET ? WHERE id = ?`, [order, order.id]);
    }
    
    async updateProductInDatabase(product) {
        // 실제로는 데이터베이스 업데이트
        return this.database.query(`UPDATE products SET ? WHERE id = ?`, [product, product.id]);
    }
}

export default OrderService;
```

### 2. 모듈 패턴의 실제 활용 사례

#### 메인 애플리케이션에서의 모듈 통합

```javascript
// app.js - 메인 애플리케이션 진입점
import configManager from './config/index.js';
import container from './container/ServiceContainer.js';
import OrderService from './services/OrderService.js';
import { Product, generateSKU } from './models/Product.js';

class EcommerceApp {
    constructor() {
        this.isInitialized = false;
        this.orderService = null;
    }
    
    async initialize() {
        if (this.isInitialized) return;
        
        try {
            console.log('전자상거래 플랫폼 초기화 시작...');
            
            // 1. 설정 초기화
            await configManager.initialize();
            console.log('✓ 설정 초기화 완료');
            
            // 2. 서비스 컨테이너 초기화
            await container.initialize();
            console.log('✓ 서비스 컨테이너 초기화 완료');
            
            // 3. 주문 서비스 초기화
            this.orderService = new OrderService();
            console.log('✓ 주문 서비스 초기화 완료');
            
            this.isInitialized = true;
            console.log('🎉 전자상거래 플랫폼 초기화 완료!');
            
        } catch (error) {
            console.error('❌ 애플리케이션 초기화 실패:', error);
            throw error;
        }
    }
    
    // 주문 처리 API
    async processOrder(userId, orderItems) {
        if (!this.isInitialized) {
            throw new Error('애플리케이션이 초기화되지 않았습니다.');
        }
        
        return await this.orderService.createOrder(userId, orderItems);
    }
    
    // 주문 상태 업데이트 API
    async updateOrderStatus(orderId, status) {
        if (!this.isInitialized) {
            throw new Error('애플리케이션이 초기화되지 않았습니다.');
        }
        
        return await this.orderService.updateOrderStatus(orderId, status);
    }
    
    // 주문 조회 API
    async getOrder(orderId) {
        if (!this.isInitialized) {
            throw new Error('애플리케이션이 초기화되지 않았습니다.');
        }
        
        return await this.orderService.getOrderById(orderId);
    }
}

// 애플리케이션 인스턴스 생성 및 내보내기
const app = new EcommerceApp();
export default app;

// 애플리케이션 시작
async function startApp() {
    try {
        await app.initialize();
        
        // 샘플 주문 처리
        const sampleOrder = await app.processOrder('user123', [
            {
                productId: 'prod_001',
                name: '맥북 프로 16인치',
                price: 3500000,
                quantity: 1
            },
            {
                productId: 'prod_002', 
                name: '무선 마우스',
                price: 89000,
                quantity: 2
            }
        ]);
        
        console.log('샘플 주문 처리 완료:', sampleOrder);
        
    } catch (error) {
        console.error('애플리케이션 시작 실패:', error);
        process.exit(1);
    }
}

// 개발 환경에서만 자동 시작
if (process.env.NODE_ENV === 'development') {
    startApp();
}
```

## 모듈 패턴 운영

### 성능 최적화 전략

#### 동적 임포트를 활용한 코드 스플리팅

규모가 커지면 모듈을 전부 한 번에 로드하는 것보다 필요할 때 동적으로 로드하는 쪽이 낫다.

```javascript
// utils/moduleLoader.js - 지능형 모듈 로더
class ModuleLoader {
    constructor() {
        this.cache = new Map();
        this.loadingPromises = new Map();
    }
    
    // 동적 모듈 로드
    async loadModule(modulePath, options = {}) {
        const { 
            cache = true, 
            timeout = 5000, 
            retries = 3,
            fallback = null 
        } = options;
        
        // 캐시 확인
        if (cache && this.cache.has(modulePath)) {
            return this.cache.get(modulePath);
        }
        
        // 이미 로딩 중인 경우 기존 Promise 반환
        if (this.loadingPromises.has(modulePath)) {
            return this.loadingPromises.get(modulePath);
        }
        
        // 로딩 Promise 생성
        const loadingPromise = this.loadWithRetry(modulePath, retries, timeout);
        this.loadingPromises.set(modulePath, loadingPromise);
        
        try {
            const module = await loadingPromise;
            
            if (cache) {
                this.cache.set(modulePath, module);
            }
            
            this.loadingPromises.delete(modulePath);
            return module;
            
        } catch (error) {
            this.loadingPromises.delete(modulePath);
            
            if (fallback) {
                console.warn(`모듈 로드 실패, 폴백 사용: ${modulePath}`);
                return await this.loadModule(fallback, { cache, timeout, retries: 0 });
            }
            
            throw error;
        }
    }
    
    // 재시도 로직이 포함된 모듈 로드
    async loadWithRetry(modulePath, retries, timeout) {
        for (let attempt = 1; attempt <= retries; attempt++) {
            try {
                const module = await Promise.race([
                    import(modulePath),
                    new Promise((_, reject) => 
                        setTimeout(() => reject(new Error('로드 타임아웃')), timeout)
                    )
                ]);
                
                return module;
                
            } catch (error) {
                if (attempt === retries) {
                    throw new Error(`모듈 로드 실패 (${attempt}회 시도): ${error.message}`);
                }
                
                console.warn(`모듈 로드 재시도 ${attempt}/${retries}: ${modulePath}`);
                await this.delay(1000 * attempt); // 지수 백오프
            }
        }
    }
    
    // 조건부 모듈 로드
    async loadConditionalModule(condition, moduleMap) {
        const modulePath = moduleMap[condition];
        
        if (!modulePath) {
            throw new Error(`지원하지 않는 조건: ${condition}`);
        }
        
        return await this.loadModule(modulePath);
    }
    
    // 모듈 프리로딩
    async preloadModules(modulePaths) {
        const preloadPromises = modulePaths.map(path => 
            this.loadModule(path, { cache: true })
        );
        
        try {
            await Promise.allSettled(preloadPromises);
            console.log('모듈 프리로딩 완료');
        } catch (error) {
            console.warn('일부 모듈 프리로딩 실패:', error);
        }
    }
    
    // 캐시 관리
    clearCache(pattern = null) {
        if (pattern) {
            const regex = new RegExp(pattern);
            for (const [key] of this.cache) {
                if (regex.test(key)) {
                    this.cache.delete(key);
                }
            }
        } else {
            this.cache.clear();
        }
    }
    
    getCacheStats() {
        return {
            size: this.cache.size,
            keys: Array.from(this.cache.keys()),
            loading: this.loadingPromises.size
        };
    }
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// 전역 모듈 로더 인스턴스
const moduleLoader = new ModuleLoader();
export default moduleLoader;
```

#### 모듈 성능 모니터링

```javascript
// utils/performanceMonitor.js - 모듈 성능 모니터링
class ModulePerformanceMonitor {
    constructor() {
        this.metrics = new Map();
        this.isEnabled = process.env.NODE_ENV === 'development';
    }
    
    // 모듈 로드 시간 측정
    async measureModuleLoad(modulePath, loadFunction) {
        if (!this.isEnabled) {
            return await loadFunction();
        }
        
        const startTime = performance.now();
        const startMemory = process.memoryUsage();
        
        try {
            const result = await loadFunction();
            
            const endTime = performance.now();
            const endMemory = process.memoryUsage();
            
            this.recordMetrics(modulePath, {
                loadTime: endTime - startTime,
                memoryDelta: endMemory.heapUsed - startMemory.heapUsed,
                success: true,
                timestamp: new Date()
            });
            
            return result;
            
        } catch (error) {
            const endTime = performance.now();
            
            this.recordMetrics(modulePath, {
                loadTime: endTime - startTime,
                success: false,
                error: error.message,
                timestamp: new Date()
            });
            
            throw error;
        }
    }
    
    // 메트릭 기록
    recordMetrics(modulePath, metrics) {
        if (!this.metrics.has(modulePath)) {
            this.metrics.set(modulePath, []);
        }
        
        this.metrics.get(modulePath).push(metrics);
        
        // 최근 100개 기록만 유지
        const records = this.metrics.get(modulePath);
        if (records.length > 100) {
            records.splice(0, records.length - 100);
        }
    }
    
    // 성능 리포트 생성
    generateReport() {
        const report = {};
        
        for (const [modulePath, metrics] of this.metrics) {
            const successfulLoads = metrics.filter(m => m.success);
            const failedLoads = metrics.filter(m => !m.success);
            
            if (successfulLoads.length > 0) {
                const avgLoadTime = successfulLoads.reduce((sum, m) => sum + m.loadTime, 0) / successfulLoads.length;
                const maxLoadTime = Math.max(...successfulLoads.map(m => m.loadTime));
                const minLoadTime = Math.min(...successfulLoads.map(m => m.loadTime));
                
                report[modulePath] = {
                    totalLoads: metrics.length,
                    successfulLoads: successfulLoads.length,
                    failedLoads: failedLoads.length,
                    successRate: (successfulLoads.length / metrics.length) * 100,
                    avgLoadTime: Math.round(avgLoadTime * 100) / 100,
                    maxLoadTime: Math.round(maxLoadTime * 100) / 100,
                    minLoadTime: Math.round(minLoadTime * 100) / 100,
                    recentErrors: failedLoads.slice(-5).map(m => m.error)
                };
            }
        }
        
        return report;
    }
    
    // 성능 리포트 출력
    printReport() {
        const report = this.generateReport();
        
        console.log('\n=== 모듈 성능 리포트 ===');
        for (const [modulePath, stats] of Object.entries(report)) {
            console.log(`\n📦 ${modulePath}`);
            console.log(`   로드 횟수: ${stats.totalLoads} (성공: ${stats.successfulLoads}, 실패: ${stats.failedLoads})`);
            console.log(`   성공률: ${stats.successRate.toFixed(1)}%`);
            console.log(`   평균 로드 시간: ${stats.avgLoadTime}ms`);
            console.log(`   최대 로드 시간: ${stats.maxLoadTime}ms`);
            
            if (stats.recentErrors.length > 0) {
                console.log(`   최근 오류: ${stats.recentErrors.join(', ')}`);
            }
        }
    }
}

const performanceMonitor = new ModulePerformanceMonitor();
export default performanceMonitor;
```

### 에러 처리 및 복구 전략

#### 견고한 모듈 에러 처리

```javascript
// utils/errorHandler.js - 모듈 에러 처리
class ModuleErrorHandler {
    constructor() {
        this.errorHandlers = new Map();
        this.circuitBreakers = new Map();
    }
    
    // 에러 핸들러 등록
    registerErrorHandler(modulePath, handler) {
        this.errorHandlers.set(modulePath, handler);
    }
    
    // 서킷 브레이커 패턴 구현
    createCircuitBreaker(modulePath, options = {}) {
        const { 
            failureThreshold = 5, 
            timeout = 60000, 
            resetTimeout = 30000 
        } = options;
        
        this.circuitBreakers.set(modulePath, {
            failures: 0,
            lastFailureTime: null,
            state: 'CLOSED', // CLOSED, OPEN, HALF_OPEN
            failureThreshold,
            timeout,
            resetTimeout
        });
    }
    
    // 서킷 브레이커를 통한 안전한 모듈 실행
    async executeWithCircuitBreaker(modulePath, operation) {
        const breaker = this.circuitBreakers.get(modulePath);
        
        if (!breaker) {
            return await this.executeWithErrorHandling(modulePath, operation);
        }
        
        // 서킷 브레이커 상태 확인
        if (breaker.state === 'OPEN') {
            if (Date.now() - breaker.lastFailureTime > breaker.resetTimeout) {
                breaker.state = 'HALF_OPEN';
            } else {
                throw new Error(`서킷 브레이커 열림: ${modulePath}`);
            }
        }
        
        try {
            const result = await this.executeWithErrorHandling(modulePath, operation);
            
            // 성공 시 서킷 브레이커 리셋
            if (breaker.state === 'HALF_OPEN') {
                breaker.state = 'CLOSED';
                breaker.failures = 0;
            }
            
            return result;
            
        } catch (error) {
            breaker.failures++;
            breaker.lastFailureTime = Date.now();
            
            if (breaker.failures >= breaker.failureThreshold) {
                breaker.state = 'OPEN';
            }
            
            throw error;
        }
    }
    
    // 에러 핸들링과 함께 모듈 실행
    async executeWithErrorHandling(modulePath, operation) {
        try {
            return await operation();
            
    } catch (error) {
            const handler = this.errorHandlers.get(modulePath);
            
            if (handler) {
                return await handler(error, modulePath);
            }
            
            // 기본 에러 처리
            console.error(`모듈 실행 오류 [${modulePath}]:`, error);
            throw error;
        }
    }
    
    // 자동 복구 메커니즘
    async autoRecovery(modulePath, recoveryStrategies) {
        for (const strategy of recoveryStrategies) {
            try {
                console.log(`복구 시도: ${strategy.name} for ${modulePath}`);
                const result = await strategy.execute();
    
    if (result.success) {
                    console.log(`복구 성공: ${strategy.name}`);
                    return result;
                }
                
            } catch (error) {
                console.warn(`복구 실패: ${strategy.name} - ${error.message}`);
            }
        }
        
        throw new Error(`모든 복구 시도 실패: ${modulePath}`);
    }
}

const errorHandler = new ModuleErrorHandler();
export default errorHandler;
```

## 모듈 시스템 비교 및 선택

### CommonJS vs ES6 모듈 상세 비교

| 측면 | CommonJS | ES6 모듈 | 권장 사용 사례 |
|:-----|:---------|:---------|:---------------|
| **로딩 방식** | 동기적 (런타임) | 비동기적 (컴파일 타임) | CommonJS: 서버사이드<br/>ES6: 클라이언트사이드 |
| **정적 분석** | 불가능 | 가능 | ES6: 번들러 최적화, 트리 쉐이킹 |
| **순환 의존성** | 지원 (부분적) | 제한적 지원 | CommonJS: 복잡한 의존성 구조 |
| **브라우저 지원** | 번들러 필요 | 네이티브 지원 | ES6: 모던 브라우저 환경 |
| **Node.js 지원** | 네이티브 | 실험적 (.mjs) | CommonJS: 안정적인 Node.js 환경 |
| **번들 크기** | 최적화 어려움 | 트리 쉐이킹 가능 | ES6: 번들 크기 최적화 중요시 |
| **개발 경험** | 단순함 | 더 풍부한 기능 | ES6: 대규모 프로젝트 |

> CommonJS는 서버사이드에서 안정적이고, ES6 모듈은 클라이언트사이드 최적화에 유리하다.

### 위 표에서 세 줄은 지금 기준으로 맞지 않는다

**"Node.js 지원: ES6 = 실험적(.mjs)"** 는 옛 상태다. 지금 Node 에서 ESM 은 플래그 없이 동작하며 `package.json` 의 `"type": "module"` 이나 `.mjs` 확장자로 켠다([Node.js ESM 문서](https://nodejs.org/api/esm.html)). "서버는 CommonJS, 브라우저는 ESM" 이라는 구분도 그래서 성립하지 않는다. 지금 CommonJS 를 고르는 이유는 안정성이 아니라 **기존 코드와 의존 패키지가 그쪽이기 때문**이다.

**"로딩 방식: ES6 = 비동기적(컴파일 타임)"** 은 두 개념이 섞여 있다. 정확히는 의존성 해석이 실행 전에 끝나고, 그래서 **`import` 한 모듈이 그 파일의 첫 줄보다 먼저 평가된다.** 이 한 문장이 CommonJS 에서 넘어올 때 가장 자주 사고를 낸다.

```javascript
// t2.mjs
process.env.APP_PORT = '8080';      // import 보다 위에 적었다
import { PORT } from './env.mjs';   // env.mjs 는 process.env.APP_PORT 를 읽는다
console.log(PORT);
```

실행하면 이렇게 나온다.

```
[env.mjs 평가] APP_PORT = undefined
[main 실행] PORT = (없음)
```

같은 코드를 `require` 로 쓰면 위에서 아래로 실행되므로 `8080` 이 나온다. `dotenv.config()` 를 import 아래에 두고 "환경변수를 못 읽는다"고 헤매는 사고가 여기서 나온다. ESM 에서는 설정 로드를 **별도 모듈로 분리해 맨 위에서 import** 하거나, 그 시점 이후에 동적 `import()` 로 미룬다.

```javascript
import './load-env.mjs';           // 이 모듈 안에서 dotenv.config() 를 부른다
import { PORT } from './env.mjs';  // 그 다음에 평가된다
```

**"순환 의존성: CommonJS 가 낫다"** 도 조건이 붙는다. CommonJS 는 순환이 생기면 **아직 채워지지 않은 `module.exports`** 를 그대로 넘겨준다. 받는 쪽은 `undefined` 를 쥐고도 그냥 진행하다가 한참 뒤 엉뚱한 자리에서 터진다. ESM 은 라이브 바인딩이라 나중에 채워지지만, 초기화 전에 접근하면 그 자리에서 `ReferenceError` 로 죽는다. **조용히 틀리는 쪽과 시끄럽게 죽는 쪽 중 무엇을 고르느냐**의 문제지 한쪽이 더 잘 지원하는 것이 아니다. 어느 쪽이든 순환 자체를 없애는 것이 답이고, 대개는 두 모듈이 함께 쓰는 것을 세 번째 모듈로 빼면 풀린다.

### 프로젝트별 모듈 시스템 선택

#### Node.js 백엔드 프로젝트
```javascript
// package.json
{
  "type": "commonjs",  // 또는 생략 (기본값)
  "main": "src/app.js"
}

// 권장 구조
src/
├── config/
│   ├── database.js    // CommonJS
│   └── redis.js       // CommonJS
├── models/
│   ├── User.js        // CommonJS
│   └── Product.js     // CommonJS
└── app.js             // CommonJS
```

#### 프론트엔드 프로젝트
```javascript
// package.json
{
  "type": "module",
  "main": "src/app.js"
}

// 권장 구조
src/
├── components/
│   ├── Header.js      // ES6 모듈
│   └── Footer.js      // ES6 모듈
├── utils/
│   ├── api.js         // ES6 모듈
│   └── validation.js  // ES6 모듈
└── app.js             // ES6 모듈
```

#### 하이브리드 프로젝트
```javascript
// Node.js 서버 (CommonJS)
// src/server.js
const express = require('express');
const { UserService } = require('./services/UserService');

// 클라이언트 번들 (ES6 모듈)
// src/client/
import { UserComponent } from './components/UserComponent.js';
import { apiClient } from './utils/apiClient.js';
```


### 실무 적용 팁

- 점진적 마이그레이션 — 기존 CommonJS 프로젝트는 ES6 모듈로 조금씩 옮긴다.
- 모니터링 — 모듈 로드 성능은 계속 지켜보면서 최적화한다.
- 문서화 — 모듈이 무엇을 하고 어떻게 쓰는지 분명히 적어 둔다.
- 테스트 — 모듈 하나하나를 따로 테스트할 수 있게 설계한다.


## 참조 자료

### 공식 문서

- [MDN - JavaScript Modules](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules)
- [Node.js - Modules](https://nodejs.org/api/modules.html)
- [ECMAScript 2020 - Modules](https://tc39.es/ecma262/#sec-modules)

### 관련 표준

- [CommonJS Modules/1.1 Specification](http://wiki.commonjs.org/wiki/Modules/1.1)
- [ES6 Modules Specification](https://tc39.es/ecma262/#sec-modules)
- [Node.js ES Modules](https://nodejs.org/api/esm.html)

### 도구 및 라이브러리

- [Webpack - Module Federation](https://webpack.js.org/concepts/module-federation/)
- [Rollup - Tree Shaking](https://rollupjs.org/guide/en/#tree-shaking)
- [Vite - Fast Build Tool](https://vitejs.dev/guide/features.html#es-modules)

### 추가 학습 자료

- [JavaScript.info - Modules](https://javascript.info/modules)
- [You Don't Know JS - ES6 & Beyond](https://github.com/getify/You-Dont-Know-JS/tree/1st-ed/es6%20%26%20beyond)

### 실무 가이드

- [Google JavaScript Style Guide](https://google.github.io/styleguide/jsguide.html)
- [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- [Node.js Best Practices](https://github.com/goldbergyoni/nodebestpractices)

---


