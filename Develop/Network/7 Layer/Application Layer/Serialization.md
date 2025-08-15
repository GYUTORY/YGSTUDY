---
title: 직렬화(Serialization)와 역직렬화(Deserialization)
tags: [network, 7-layer, application-layer, serialization, data-format, json, xml]
updated: 2025-08-10
---

# 직렬화(Serialization)와 역직렬화(Deserialization)

## 배경

### 직렬화의 필요성
데이터를 네트워크로 전송하거나 파일에 저장할 때, 메모리에 있는 객체나 데이터 구조를 바이트 스트림으로 변환해야 합니다. 이 과정을 직렬화라고 하며, 반대로 바이트 스트림을 다시 원래의 객체로 변환하는 과정을 역직렬화라고 합니다.

### 직렬화의 주요 용도
- **네트워크 통신**: 객체를 바이트 스트림으로 변환하여 전송
- **데이터 저장**: 객체를 파일이나 데이터베이스에 저장
- **캐싱**: 객체를 메모리나 디스크에 캐시
- **분산 시스템**: 서로 다른 시스템 간 데이터 교환

### 직렬화 방식의 종류
- **텍스트 기반**: JSON, XML, YAML 등
- **바이너리 기반**: Protocol Buffers, MessagePack, BSON 등
- **언어별**: Java Serializable, Python pickle 등

## 핵심

### 1. JSON 직렬화

#### 기본 JSON 처리
```javascript
// JSON 직렬화 유틸리티 클래스
class JSONSerializer {
    // 객체를 JSON 문자열로 직렬화
    static serialize(obj) {
        try {
            return JSON.stringify(obj, null, 2);
        } catch (error) {
            throw new Error(`JSON 직렬화 실패: ${error.message}`);
        }
    }
    
    // JSON 문자열을 객체로 역직렬화
    static deserialize(jsonString) {
        try {
            return JSON.parse(jsonString);
        } catch (error) {
            throw new Error(`JSON 역직렬화 실패: ${error.message}`);
        }
    }
    
    // 안전한 직렬화 (순환 참조 처리)
    static safeSerialize(obj) {
        const seen = new WeakSet();
        
        return JSON.stringify(obj, (key, value) => {
            if (typeof value === 'object' && value !== null) {
                if (seen.has(value)) {
                    return '[Circular Reference]';
                }
                seen.add(value);
            }
            return value;
        }, 2);
    }
    
    // 커스텀 직렬화 (특정 필드 제외)
    static serializeWithExclusions(obj, excludeFields = []) {
        const filtered = {};
        
        for (const [key, value] of Object.entries(obj)) {
            if (!excludeFields.includes(key)) {
                filtered[key] = value;
            }
        }
        
        return JSON.stringify(filtered, null, 2);
    }
    
    // 직렬화 성능 측정
    static measureSerializationPerformance(obj, iterations = 1000) {
        const start = performance.now();
        
        for (let i = 0; i < iterations; i++) {
            JSON.stringify(obj);
        }
        
        const end = performance.now();
        return {
            totalTime: end - start,
            averageTime: (end - start) / iterations,
            iterations: iterations
        };
    }
}

// JSON 직렬화 예시
const userData = {
    id: 1,
    name: '홍길동',
    email: 'hong@example.com',
    age: 30,
    isActive: true,
    createdAt: new Date(),
    preferences: {
        theme: 'dark',
        language: 'ko'
    }
};

console.log('기본 직렬화:', JSONSerializer.serialize(userData));

// 순환 참조가 있는 객체
const circularObj = { name: 'test' };
circularObj.self = circularObj;

console.log('안전한 직렬화:', JSONSerializer.safeSerialize(circularObj));

// 특정 필드 제외
console.log('필드 제외 직렬화:', JSONSerializer.serializeWithExclusions(userData, ['email', 'age']));

// 성능 측정
const performance = JSONSerializer.measureSerializationPerformance(userData);
console.log('직렬화 성능:', performance);
```

### 2. 복잡한 객체 직렬화

#### 클래스 인스턴스 직렬화
```javascript
// 직렬화 가능한 기본 클래스
class Serializable {
    // 직렬화 메서드
    toJSON() {
        const obj = {};
        
        for (const [key, value] of Object.entries(this)) {
            if (typeof value !== 'function') {
                obj[key] = value;
            }
        }
        
        obj._type = this.constructor.name;
        return obj;
    }
    
    // 역직렬화 메서드
    static fromJSON(jsonData) {
        const instance = new this();
        
        for (const [key, value] of Object.entries(jsonData)) {
            if (key !== '_type') {
                instance[key] = value;
            }
        }
        
        return instance;
    }
}

// 사용자 클래스
class User extends Serializable {
    constructor(name, email, age) {
        super();
        this.name = name;
        this.email = email;
        this.age = age;
        this.createdAt = new Date();
        this.isActive = true;
    }
    
    // 메서드는 직렬화되지 않음
    getDisplayName() {
        return `${this.name} (${this.email})`;
    }
    
    // 커스텀 직렬화
    toJSON() {
        const base = super.toJSON();
        base.createdAt = this.createdAt.toISOString();
        return base;
    }
    
    // 커스텀 역직렬화
    static fromJSON(jsonData) {
        const user = super.fromJSON(jsonData);
        user.createdAt = new Date(jsonData.createdAt);
        return user;
    }
}

// 사용 예시
const user = new User('김철수', 'kim@example.com', 25);
console.log('원본 객체:', user.getDisplayName());

const serialized = JSONSerializer.serialize(user);
console.log('직렬화된 데이터:', serialized);

const deserialized = User.fromJSON(JSONSerializer.deserialize(serialized));
console.log('역직렬화된 객체:', deserialized.getDisplayName());
```

### 3. 바이너리 직렬화

#### Buffer 기반 직렬화
```javascript
// 바이너리 직렬화 클래스
class BinarySerializer {
    // 객체를 Buffer로 직렬화
    static serializeToBuffer(obj) {
        const jsonString = JSON.stringify(obj);
        return Buffer.from(jsonString, 'utf8');
    }
    
    // Buffer를 객체로 역직렬화
    static deserializeFromBuffer(buffer) {
        const jsonString = buffer.toString('utf8');
        return JSON.parse(jsonString);
    }
    
    // 숫자 배열을 Buffer로 직렬화
    static serializeNumbers(numbers) {
        const buffer = Buffer.alloc(numbers.length * 4); // 32비트 정수
        
        for (let i = 0; i < numbers.length; i++) {
            buffer.writeInt32LE(numbers[i], i * 4);
        }
        
        return buffer;
    }
    
    // Buffer를 숫자 배열로 역직렬화
    static deserializeNumbers(buffer) {
        const numbers = [];
        const count = buffer.length / 4;
        
        for (let i = 0; i < count; i++) {
            numbers.push(buffer.readInt32LE(i * 4));
        }
        
        return numbers;
    }
    
    // 문자열 배열을 Buffer로 직렬화
    static serializeStrings(strings) {
        const stringBuffers = strings.map(str => Buffer.from(str, 'utf8'));
        const totalLength = stringBuffers.reduce((sum, buf) => sum + buf.length + 4, 0);
        const buffer = Buffer.alloc(totalLength);
        
        let offset = 0;
        for (const strBuffer of stringBuffers) {
            buffer.writeUInt32LE(strBuffer.length, offset);
            offset += 4;
            strBuffer.copy(buffer, offset);
            offset += strBuffer.length;
        }
        
        return buffer;
    }
    
    // Buffer를 문자열 배열로 역직렬화
    static deserializeStrings(buffer) {
        const strings = [];
        let offset = 0;
        
        while (offset < buffer.length) {
            const length = buffer.readUInt32LE(offset);
            offset += 4;
            const string = buffer.toString('utf8', offset, offset + length);
            strings.push(string);
            offset += length;
        }
        
        return strings;
    }
}

// 바이너리 직렬화 예시
const data = {
    id: 12345,
    name: '테스트 데이터',
    values: [1, 2, 3, 4, 5]
};

const buffer = BinarySerializer.serializeToBuffer(data);
console.log('직렬화된 Buffer:', buffer);
console.log('Buffer 크기:', buffer.length);

const restored = BinarySerializer.deserializeFromBuffer(buffer);
console.log('역직렬화된 데이터:', restored);

// 숫자 배열 직렬화
const numbers = [100, 200, 300, 400, 500];
const numberBuffer = BinarySerializer.serializeNumbers(numbers);
console.log('숫자 배열 Buffer:', numberBuffer);

const restoredNumbers = BinarySerializer.deserializeNumbers(numberBuffer);
console.log('역직렬화된 숫자 배열:', restoredNumbers);
```

## 예시

### 네트워크 통신에서의 직렬화

#### HTTP API 직렬화
```javascript
// HTTP API 직렬화 유틸리티
class APISerializer {
    // 요청 데이터 직렬화
    static serializeRequest(data, format = 'json') {
        switch (format.toLowerCase()) {
            case 'json':
                return {
                    contentType: 'application/json',
                    body: JSONSerializer.serialize(data)
                };
            case 'form':
                return {
                    contentType: 'application/x-www-form-urlencoded',
                    body: this.objectToFormData(data)
                };
            case 'binary':
                return {
                    contentType: 'application/octet-stream',
                    body: BinarySerializer.serializeToBuffer(data)
                };
            default:
                throw new Error(`지원하지 않는 형식: ${format}`);
        }
    }
    
    // 응답 데이터 역직렬화
    static deserializeResponse(response, format = 'json') {
        switch (format.toLowerCase()) {
            case 'json':
                return JSONSerializer.deserialize(response);
            case 'binary':
                return BinarySerializer.deserializeFromBuffer(response);
            default:
                throw new Error(`지원하지 않는 형식: ${format}`);
        }
    }
    
    // 객체를 폼 데이터로 변환
    static objectToFormData(obj) {
        const params = new URLSearchParams();
        
        for (const [key, value] of Object.entries(obj)) {
            if (value !== null && value !== undefined) {
                params.append(key, String(value));
            }
        }
        
        return params.toString();
    }
    
    // 폼 데이터를 객체로 변환
    static formDataToObject(formData) {
        const obj = {};
        const params = new URLSearchParams(formData);
        
        for (const [key, value] of params.entries()) {
            obj[key] = value;
        }
        
        return obj;
    }
}

// API 통신 예시
const requestData = {
    userId: 123,
    action: 'update',
    data: {
        name: '새로운 이름',
        email: 'new@example.com'
    }
};

// JSON 형식으로 직렬화
const jsonRequest = APISerializer.serializeRequest(requestData, 'json');
console.log('JSON 요청:', jsonRequest);

// 폼 데이터로 직렬화
const formRequest = APISerializer.serializeRequest(requestData, 'form');
console.log('폼 요청:', formRequest);

// 바이너리로 직렬화
const binaryRequest = APISerializer.serializeRequest(requestData, 'binary');
console.log('바이너리 요청 크기:', binaryRequest.body.length);
```

### 파일 저장에서의 직렬화

#### 파일 직렬화 관리자
```javascript
const fs = require('fs').promises;
const path = require('path');

// 파일 직렬화 관리자 클래스
class FileSerializer {
    // 객체를 파일에 저장
    static async saveToFile(obj, filePath, format = 'json') {
        try {
            let data;
            let encoding = 'utf8';
            
            switch (format.toLowerCase()) {
                case 'json':
                    data = JSONSerializer.serialize(obj);
                    break;
                case 'binary':
                    data = BinarySerializer.serializeToBuffer(obj);
                    encoding = null; // Buffer는 인코딩 불필요
                    break;
                default:
                    throw new Error(`지원하지 않는 형식: ${format}`);
            }
            
            await fs.writeFile(filePath, data, encoding);
            console.log(`파일 저장 완료: ${filePath}`);
            
        } catch (error) {
            throw new Error(`파일 저장 실패: ${error.message}`);
        }
    }
    
    // 파일에서 객체 로드
    static async loadFromFile(filePath, format = 'json') {
        try {
            let data;
            let encoding = 'utf8';
            
            if (format.toLowerCase() === 'binary') {
                encoding = null;
            }
            
            data = await fs.readFile(filePath, encoding);
            
            switch (format.toLowerCase()) {
                case 'json':
                    return JSONSerializer.deserialize(data);
                case 'binary':
                    return BinarySerializer.deserializeFromBuffer(data);
                default:
                    throw new Error(`지원하지 않는 형식: ${format}`);
            }
            
        } catch (error) {
            throw new Error(`파일 로드 실패: ${error.message}`);
        }
    }
    
    // 대용량 객체 스트리밍 저장
    static async saveLargeObject(obj, filePath) {
        const writeStream = require('fs').createWriteStream(filePath);
        
        return new Promise((resolve, reject) => {
            writeStream.write('[\n');
            
            let isFirst = true;
            for (const item of obj) {
                if (!isFirst) {
                    writeStream.write(',\n');
                }
                writeStream.write(JSON.stringify(item, null, 2));
                isFirst = false;
            }
            
            writeStream.write('\n]');
            writeStream.end();
            
            writeStream.on('finish', resolve);
            writeStream.on('error', reject);
        });
    }
    
    // 파일 정보 출력
    static async getFileInfo(filePath) {
        try {
            const stats = await fs.stat(filePath);
            const ext = path.extname(filePath);
            
            return {
                path: filePath,
                size: stats.size,
                extension: ext,
                created: stats.birthtime,
                modified: stats.mtime,
                format: this.detectFormat(ext)
            };
        } catch (error) {
            throw new Error(`파일 정보 조회 실패: ${error.message}`);
        }
    }
    
    // 파일 확장자로 형식 감지
    static detectFormat(extension) {
        const formatMap = {
            '.json': 'json',
            '.bin': 'binary',
            '.dat': 'binary',
            '.txt': 'text'
        };
        
        return formatMap[extension.toLowerCase()] || 'unknown';
    }
}

// 파일 직렬화 예시
const testData = {
    users: [
        { id: 1, name: '사용자1', email: 'user1@example.com' },
        { id: 2, name: '사용자2', email: 'user2@example.com' },
        { id: 3, name: '사용자3', email: 'user3@example.com' }
    ],
    metadata: {
        totalCount: 3,
        createdAt: new Date().toISOString(),
        version: '1.0.0'
    }
};

// JSON 파일로 저장
FileSerializer.saveToFile(testData, 'test-data.json', 'json')
    .then(() => FileSerializer.loadFromFile('test-data.json', 'json'))
    .then(loadedData => {
        console.log('로드된 데이터:', loadedData);
        return FileSerializer.getFileInfo('test-data.json');
    })
    .then(fileInfo => {
        console.log('파일 정보:', fileInfo);
    })
    .catch(error => {
        console.error('오류:', error.message);
    });
```

## 운영 팁

### 성능 최적화

#### 직렬화 성능 최적화
```javascript
// 성능 최적화된 직렬화 클래스
class OptimizedSerializer {
    constructor() {
        this.cache = new Map();
        this.maxCacheSize = 1000;
    }
    
    // 캐시를 활용한 직렬화
    serializeWithCache(obj) {
        const key = this.generateKey(obj);
        
        if (this.cache.has(key)) {
            return this.cache.get(key);
        }
        
        const result = JSONSerializer.serialize(obj);
        
        // 캐시 크기 제한
        if (this.cache.size >= this.maxCacheSize) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
        
        this.cache.set(key, result);
        return result;
    }
    
    // 객체 키 생성 (간단한 구현)
    generateKey(obj) {
        return JSON.stringify(Object.keys(obj).sort());
    }
    
    // 배치 직렬화
    batchSerialize(objects) {
        return objects.map(obj => this.serializeWithCache(obj));
    }
    
    // 캐시 통계
    getCacheStats() {
        return {
            size: this.cache.size,
            maxSize: this.maxCacheSize,
            hitRate: this.calculateHitRate()
        };
    }
    
    // 캐시 히트율 계산
    calculateHitRate() {
        // 실제 구현에서는 히트/미스 카운터를 추가해야 함
        return this.cache.size / this.maxCacheSize;
    }
    
    // 캐시 정리
    clearCache() {
        this.cache.clear();
    }
}

// 성능 테스트
const serializer = new OptimizedSerializer();
const testObjects = Array.from({ length: 100 }, (_, i) => ({
    id: i,
    name: `Object ${i}`,
    data: { value: i * 2, timestamp: Date.now() }
}));

console.time('일반 직렬화');
testObjects.forEach(obj => JSONSerializer.serialize(obj));
console.timeEnd('일반 직렬화');

console.time('캐시 직렬화');
testObjects.forEach(obj => serializer.serializeWithCache(obj));
console.timeEnd('캐시 직렬화');

console.log('캐시 통계:', serializer.getCacheStats());
```

### 에러 처리

#### 안전한 직렬화
```javascript
// 안전한 직렬화 클래스
class SafeSerializer {
    // 안전한 JSON 직렬화
    static safeSerialize(obj) {
        try {
            // 순환 참조 검사
            const seen = new WeakSet();
            
            const safeStringify = (value) => {
                if (typeof value === 'object' && value !== null) {
                    if (seen.has(value)) {
                        return '[Circular Reference]';
                    }
                    seen.add(value);
                }
                return value;
            };
            
            return JSON.stringify(obj, safeStringify, 2);
            
        } catch (error) {
            console.error('직렬화 오류:', error.message);
            return null;
        }
    }
    
    // 안전한 역직렬화
    static safeDeserialize(jsonString) {
        try {
            const result = JSON.parse(jsonString);
            
            // 타입 검증
            if (typeof result !== 'object' || result === null) {
                throw new Error('유효하지 않은 객체 형식입니다.');
            }
            
            return result;
            
        } catch (error) {
            console.error('역직렬화 오류:', error.message);
            return null;
        }
    }
    
    // 데이터 검증
    static validateData(data, schema) {
        const errors = [];
        
        for (const [field, rules] of Object.entries(schema)) {
            if (rules.required && !(field in data)) {
                errors.push(`${field} 필드가 필요합니다.`);
                continue;
            }
            
            if (field in data) {
                const value = data[field];
                
                if (rules.type && typeof value !== rules.type) {
                    errors.push(`${field} 필드는 ${rules.type} 타입이어야 합니다.`);
                }
                
                if (rules.minLength && value.length < rules.minLength) {
                    errors.push(`${field} 필드는 최소 ${rules.minLength}자 이상이어야 합니다.`);
                }
                
                if (rules.maxLength && value.length > rules.maxLength) {
                    errors.push(`${field} 필드는 최대 ${rules.maxLength}자까지 가능합니다.`);
                }
            }
        }
        
        return {
            valid: errors.length === 0,
            errors: errors
        };
    }
}

// 안전한 직렬화 예시
const testData = {
    name: '테스트',
    age: 25,
    email: 'test@example.com'
};

const schema = {
    name: { required: true, type: 'string', minLength: 2, maxLength: 50 },
    age: { required: true, type: 'number' },
    email: { required: true, type: 'string', maxLength: 100 }
};

const validation = SafeSerializer.validateData(testData, schema);
console.log('데이터 검증:', validation);

if (validation.valid) {
    const serialized = SafeSerializer.safeSerialize(testData);
    console.log('안전한 직렬화:', serialized);
    
    const deserialized = SafeSerializer.safeDeserialize(serialized);
    console.log('안전한 역직렬화:', deserialized);
}
```

## 참고

### 직렬화 형식 비교

#### 성능 및 용도별 비교
```javascript
// 직렬화 형식 비교 클래스
class SerializationComparison {
    // JSON vs 바이너리 성능 비교
    static comparePerformance(data, iterations = 1000) {
        const results = {};
        
        // JSON 직렬화 성능
        const jsonStart = performance.now();
        for (let i = 0; i < iterations; i++) {
            JSONSerializer.serialize(data);
        }
        const jsonEnd = performance.now();
        results.json = {
            time: jsonEnd - jsonStart,
            size: JSONSerializer.serialize(data).length
        };
        
        // 바이너리 직렬화 성능
        const binaryStart = performance.now();
        for (let i = 0; i < iterations; i++) {
            BinarySerializer.serializeToBuffer(data);
        }
        const binaryEnd = performance.now();
        results.binary = {
            time: binaryEnd - binaryStart,
            size: BinarySerializer.serializeToBuffer(data).length
        };
        
        return results;
    }
    
    // 형식별 특징
    static getFormatCharacteristics() {
        return {
            json: {
                name: 'JSON',
                humanReadable: true,
                size: '중간',
                performance: '보통',
                useCase: '웹 API, 설정 파일, 로그'
            },
            binary: {
                name: 'Binary',
                humanReadable: false,
                size: '작음',
                performance: '빠름',
                useCase: '게임, 실시간 통신, 대용량 데이터'
            },
            xml: {
                name: 'XML',
                humanReadable: true,
                size: '큼',
                performance: '느림',
                useCase: '웹 서비스, 문서 교환'
            }
        };
    }
    
    // 용도별 권장 형식
    static getRecommendedFormat(useCase) {
        const recommendations = {
            'web-api': 'json',
            'real-time': 'binary',
            'configuration': 'json',
            'logging': 'json',
            'gaming': 'binary',
            'document-exchange': 'xml'
        };
        
        return recommendations[useCase] || 'json';
    }
}

// 성능 비교 예시
const testObject = {
    id: 12345,
    name: '성능 테스트 객체',
    values: Array.from({ length: 1000 }, (_, i) => i),
    metadata: {
        createdAt: new Date().toISOString(),
        version: '1.0.0'
    }
};

const performanceResults = SerializationComparison.comparePerformance(testObject);
console.log('성능 비교 결과:', performanceResults);

const characteristics = SerializationComparison.getFormatCharacteristics();
console.log('형식별 특징:', characteristics);

const recommendation = SerializationComparison.getRecommendedFormat('web-api');
console.log('웹 API 권장 형식:', recommendation);
```

### 결론
직렬화와 역직렬화는 데이터 전송과 저장의 핵심 기술입니다.
JSON은 가독성과 호환성이 좋아 웹 개발에서 널리 사용됩니다.
바이너리 직렬화는 성능이 우수하여 실시간 애플리케이션에 적합합니다.
적절한 에러 처리와 성능 최적화가 직렬화 구현의 핵심입니다.
용도에 맞는 직렬화 형식을 선택하는 것이 중요합니다.

