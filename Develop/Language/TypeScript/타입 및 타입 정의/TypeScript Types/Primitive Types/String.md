---
title: TypeScript String 타입
tags: [language, typescript, 타입-및-타입-정의, typescript-types, primitive-types, string]
updated: 2025-08-10
---

# TypeScript String 타입

## 배경

TypeScript에서 `string` 타입은 텍스트 데이터를 나타내는 기본 데이터 타입입니다.

### string 타입의 필요성
- **텍스트 처리**: 문자, 단어, 문장 등의 텍스트 데이터 처리
- **사용자 입력**: 사용자로부터 받은 텍스트 데이터 처리
- **데이터 표현**: 정보를 사람이 읽을 수 있는 형태로 표현
- **API 통신**: 서버와의 텍스트 기반 통신

### 기본 개념
- **16비트 유니코드**: 유니코드 문자 집합 지원
- **불변 객체**: 문자열은 한 번 생성되면 변경 불가
- **인덱싱**: 각 문자에 인덱스로 접근 가능
- **다양한 표현**: 작은따옴표, 큰따옴표, 백틱 지원

## 핵심

### 1. string 타입 기본 사용법

#### string 변수 선언
```typescript
// 기본 string 변수 선언
let name: string = '홍길동';
let message: string = "안녕하세요";
let description: string = `TypeScript 문자열`;

// 타입 추론을 통한 선언
let title = '제목';  // string으로 추론
let content = "내용"; // string으로 추론

// 빈 문자열
let emptyString: string = '';
let emptyString2: string = "";

// 문자열 길이 확인
console.log(name.length);        // 3
console.log(emptyString.length); // 0
```

#### 문자열 리터럴
```typescript
// 작은따옴표 (Single quotes)
let singleQuote: string = '작은따옴표 문자열';

// 큰따옴표 (Double quotes)
let doubleQuote: string = "큰따옴표 문자열";

// 백틱 (Template literals)
let templateLiteral: string = `템플릿 리터럴 문자열`;

// 이스케이프 문자
let escapedString: string = '줄바꿈\n탭\t따옴표\"';
let rawString: string = `원시 문자열: \n\t\"`;

console.log(escapedString);
console.log(rawString);
```

### 2. 템플릿 리터럴과 문자열 보간

#### 템플릿 리터럴 사용
```typescript
// 기본 템플릿 리터럴
let firstName: string = '홍';
let lastName: string = '길동';
let fullName: string = `${firstName} ${lastName}`;

console.log(fullName); // "홍 길동"

// 표현식 사용
let age: number = 30;
let greeting: string = `안녕하세요, 저는 ${firstName}이고 ${age}살입니다.`;

console.log(greeting); // "안녕하세요, 저는 홍이고 30살입니다."

// 함수 호출
function getCurrentYear(): number {
    return new Date().getFullYear();
}

let yearMessage: string = `현재 년도는 ${getCurrentYear()}년입니다.`;
console.log(yearMessage); // "현재 년도는 2024년입니다."
```

#### 멀티라인 문자열
```typescript
// 템플릿 리터럴로 멀티라인 문자열 생성
let multiLineString: string = `
    첫 번째 줄
    두 번째 줄
    세 번째 줄
`;

// 일반 문자열로 멀티라인 (이스케이프 문자 사용)
let multiLineString2: string = '첫 번째 줄\n두 번째 줄\n세 번째 줄';

console.log(multiLineString);
console.log(multiLineString2);
```

### 3. 문자열 메서드와 조작

#### 기본 문자열 메서드
```typescript
let text: string = 'Hello, TypeScript!';

// 문자열 길이
console.log(text.length); // 18

// 대소문자 변환
console.log(text.toUpperCase()); // "HELLO, TYPESCRIPT!"
console.log(text.toLowerCase()); // "hello, typescript!"

// 문자열 검색
console.log(text.indexOf('TypeScript')); // 7
console.log(text.includes('Hello'));     // true
console.log(text.startsWith('Hello'));   // true
console.log(text.endsWith('!'));         // true

// 문자열 추출
console.log(text.substring(0, 5));       // "Hello"
console.log(text.slice(7, 17));          // "TypeScript"
console.log(text.charAt(0));             // "H"
```

#### 문자열 분할과 결합
```typescript
// 문자열 분할
let sentence: string = '사과,바나나,오렌지,포도';
let fruits: string[] = sentence.split(',');
console.log(fruits); // ["사과", "바나나", "오렌지", "포도"]

// 문자열 결합
let words: string[] = ['Hello', 'World', 'TypeScript'];
let combined: string = words.join(' ');
console.log(combined); // "Hello World TypeScript"

// 문자열 반복
let repeated: string = 'ha'.repeat(3);
console.log(repeated); // "hahaha"

// 문자열 치환
let original: string = 'Hello World';
let replaced: string = original.replace('World', 'TypeScript');
console.log(replaced); // "Hello TypeScript"

// 모든 치환
let text2: string = 'cat cat cat';
let replaced2: string = text2.replaceAll('cat', 'dog');
console.log(replaced2); // "dog dog dog"
```

## 예시

### 1. 실제 사용 사례

#### 사용자 입력 검증
```typescript
class InputValidator {
    // 이메일 검증
    static isValidEmail(email: string): boolean {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // 비밀번호 강도 검증
    static isStrongPassword(password: string): boolean {
        const minLength = 8;
        const hasUpperCase = /[A-Z]/.test(password);
        const hasLowerCase = /[a-z]/.test(password);
        const hasNumbers = /\d/.test(password);
        const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);

        return password.length >= minLength && 
               hasUpperCase && 
               hasLowerCase && 
               hasNumbers && 
               hasSpecialChar;
    }

    // 전화번호 형식 검증
    static isValidPhoneNumber(phone: string): boolean {
        const phoneRegex = /^[0-9]{2,3}-[0-9]{3,4}-[0-9]{4}$/;
        return phoneRegex.test(phone);
    }

    // 문자열 정리 (공백 제거, 소문자 변환)
    static sanitizeString(input: string): string {
        return input.trim().toLowerCase();
    }
}

// 사용 예시
console.log(InputValidator.isValidEmail('user@example.com')); // true
console.log(InputValidator.isValidEmail('invalid-email'));    // false

console.log(InputValidator.isStrongPassword('StrongPass123!')); // true
console.log(InputValidator.isStrongPassword('weak'));          // false

console.log(InputValidator.isValidPhoneNumber('010-1234-5678')); // true
console.log(InputValidator.isValidPhoneNumber('01012345678'));   // false

console.log(InputValidator.sanitizeString('  Hello World  ')); // "hello world"
```

#### 문자열 포맷팅
```typescript
class StringFormatter {
    // 카멜 케이스로 변환
    static toCamelCase(str: string): string {
        return str.replace(/-([a-z])/g, (match, letter) => letter.toUpperCase());
    }

    // 스네이크 케이스로 변환
    static toSnakeCase(str: string): string {
        return str.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
    }

    // 파스칼 케이스로 변환
    static toPascalCase(str: string): string {
        return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
    }

    // 숫자 포맷팅 (천 단위 구분자)
    static formatNumber(num: number): string {
        return num.toLocaleString();
    }

    // 날짜 포맷팅
    static formatDate(date: Date): string {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    // 문자열 자르기 (말줄임표)
    static truncate(str: string, maxLength: number): string {
        if (str.length <= maxLength) {
            return str;
        }
        return str.substring(0, maxLength) + '...';
    }
}

// 사용 예시
console.log(StringFormatter.toCamelCase('hello-world')); // "helloWorld"
console.log(StringFormatter.toSnakeCase('helloWorld')); // "hello_world"
console.log(StringFormatter.toPascalCase('hello world')); // "Hello world"

console.log(StringFormatter.formatNumber(1234567)); // "1,234,567"
console.log(StringFormatter.formatDate(new Date())); // "2024-01-15"

console.log(StringFormatter.truncate('매우 긴 문자열입니다.', 10)); // "매우 긴 문자열..."
```

### 2. 고급 패턴

#### 문자열과 제네릭
```typescript
// 문자열 처리를 위한 제네릭 클래스
class StringProcessor<T extends string> {
    private value: T;

    constructor(value: T) {
        this.value = value;
    }

    // 문자열 변환 메서드들
    toUpperCase(): string {
        return this.value.toUpperCase();
    }

    toLowerCase(): string {
        return this.value.toLowerCase();
    }

    reverse(): string {
        return this.value.split('').reverse().join('');
    }

    // 조건부 처리
    ifContains(substring: string, callback: (str: string) => string): string {
        if (this.value.includes(substring)) {
            return callback(this.value);
        }
        return this.value;
    }

    // 체이닝을 위한 메서드
    pipe<U>(fn: (str: string) => U): U {
        return fn(this.value);
    }
}

// 사용 예시
const processor = new StringProcessor('Hello, TypeScript!');

console.log(processor.toUpperCase()); // "HELLO, TYPESCRIPT!"
console.log(processor.reverse()); // "!tpircSepyT ,olleH"

const result = processor
    .pipe(str => str.toUpperCase())
    .pipe(str => str.replace('TYPESCRIPT', 'JAVASCRIPT'));

console.log(result); // "HELLO, JAVASCRIPT!"
```

#### 문자열과 정규표현식
```typescript
class StringAnalyzer {
    // 단어 개수 세기
    static countWords(text: string): number {
        return text.trim().split(/\s+/).length;
    }

    // 문장 개수 세기
    static countSentences(text: string): number {
        return text.split(/[.!?]+/).filter(sentence => sentence.trim().length > 0).length;
    }

    // 특정 패턴 찾기
    static findPatterns(text: string, pattern: RegExp): string[] {
        const matches = text.match(pattern);
        return matches || [];
    }

    // 이메일 주소 추출
    static extractEmails(text: string): string[] {
        const emailPattern = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g;
        return this.findPatterns(text, emailPattern);
    }

    // URL 추출
    static extractUrls(text: string): string[] {
        const urlPattern = /https?:\/\/[^\s]+/g;
        return this.findPatterns(text, urlPattern);
    }

    // 해시태그 추출
    static extractHashtags(text: string): string[] {
        const hashtagPattern = /#[\w가-힣]+/g;
        return this.findPatterns(text, hashtagPattern);
    }
}

// 사용 예시
const sampleText = `
안녕하세요! 이것은 샘플 텍스트입니다.
이메일 주소는 user@example.com입니다.
웹사이트: https://example.com
해시태그: #TypeScript #JavaScript
`;

console.log(StringAnalyzer.countWords(sampleText)); // 15
console.log(StringAnalyzer.countSentences(sampleText)); // 4
console.log(StringAnalyzer.extractEmails(sampleText)); // ["user@example.com"]
console.log(StringAnalyzer.extractUrls(sampleText)); // ["https://example.com"]
console.log(StringAnalyzer.extractHashtags(sampleText)); // ["#TypeScript", "#JavaScript"]
```

## 운영 팁

### 성능 최적화

#### 문자열 연산 최적화
```typescript
// 문자열 연결 최적화
class StringOptimizer {
    // 배열을 사용한 문자열 연결 (성능 향상)
    static joinStrings(strings: string[]): string {
        return strings.join('');
    }

    // StringBuilder 패턴
    static buildString(parts: string[]): string {
        let result = '';
        for (const part of parts) {
            result += part;
        }
        return result;
    }

    // 템플릿 리터럴 사용 (가독성과 성능)
    static createTemplate(values: Record<string, string>): string {
        return `이름: ${values.name}, 나이: ${values.age}, 도시: ${values.city}`;
    }
}

// 사용 예시
const parts = ['Hello', ' ', 'World', '!'];
console.log(StringOptimizer.joinStrings(parts)); // "Hello World!"

const values = { name: '홍길동', age: '30', city: '서울' };
console.log(StringOptimizer.createTemplate(values)); // "이름: 홍길동, 나이: 30, 도시: 서울"
```

### 에러 처리

#### 안전한 문자열 처리
```typescript
class SafeStringHandler {
    // null/undefined 안전 처리
    static safeToString(value: unknown): string {
        if (value === null || value === undefined) {
            return '';
        }
        return String(value);
    }

    // 문자열 검증
    static validateString(value: unknown): { isValid: boolean; value?: string } {
        if (typeof value === 'string') {
            return { isValid: true, value };
        }
        return { isValid: false };
    }

    // 안전한 문자열 접근
    static safeSubstring(str: string, start: number, end?: number): string {
        if (typeof str !== 'string') {
            return '';
        }
        
        const length = str.length;
        const safeStart = Math.max(0, Math.min(start, length));
        const safeEnd = end !== undefined ? Math.max(0, Math.min(end, length)) : length;
        
        return str.substring(safeStart, safeEnd);
    }

    // 문자열 정규화
    static normalizeString(str: string): string {
        return str
            .trim()
            .replace(/\s+/g, ' ') // 여러 공백을 하나로
            .toLowerCase();
    }
}

// 사용 예시
console.log(SafeStringHandler.safeToString(null)); // ""
console.log(SafeStringHandler.safeToString(123)); // "123"

const validation = SafeStringHandler.validateString('hello');
console.log(validation); // { isValid: true, value: 'hello' }

console.log(SafeStringHandler.safeSubstring('Hello World', 0, 5)); // "Hello"
console.log(SafeStringHandler.safeSubstring('Hello World', 100, 200)); // ""

console.log(SafeStringHandler.normalizeString('  Hello   World  ')); // "hello world"
```

## 참고

### string 타입 특성

| 특성 | 설명 |
|------|------|
| **불변성** | 한 번 생성되면 변경 불가 |
| **인덱싱** | 각 문자에 인덱스로 접근 가능 |
| **유니코드** | 16비트 유니코드 문자 지원 |
| **리터럴** | 작은따옴표, 큰따옴표, 백틱 지원 |

### string vs String 비교표

| 구분 | string | String |
|------|--------|--------|
| **타입** | 원시 타입 | 객체 타입 |
| **메서드** | 직접 호출 불가 | 메서드 호출 가능 |
| **성능** | 빠름 | 상대적으로 느림 |
| **사용 권장** | 일반적인 사용 | 특별한 경우만 |

### 결론
TypeScript의 string 타입은 텍스트 데이터를 처리하는 기본 타입입니다.
템플릿 리터럴을 활용하여 동적 문자열을 효율적으로 생성하세요.
문자열 메서드를 활용하여 다양한 문자열 조작을 수행하세요.
정규표현식과 함께 사용하여 복잡한 문자열 패턴을 처리하세요.
문자열의 불변성을 이해하고 적절한 메서드를 선택하세요.
성능을 고려하여 문자열 연산을 최적화하세요.
안전한 문자열 처리를 통해 런타임 오류를 방지하세요.

