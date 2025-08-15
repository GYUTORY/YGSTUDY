---
title: JavaScript에서 2진수, 10진수, 16진수 다루기
tags: [language, javascript, 04심화javascript, javascript에서-2진수-10진수-16진수-다루기, number-system, binary, hexadecimal]
updated: 2025-08-10
---

# JavaScript에서 2진수, 10진수, 16진수 다루기

## 배경

JavaScript에서 숫자를 다룰 때는 주로 10진수를 사용하지만, 프로그래밍에서는 2진수와 16진수도 자주 사용됩니다. 각 진수는 특정한 용도에 적합하며, JavaScript는 이러한 다양한 진수를 처리할 수 있는 내장 기능을 제공합니다.

### 각 진수의 특징과 용도
- **10진수**: 0~9까지의 숫자 사용 (일상생활에서 사용하는 표준 진수)
- **2진수**: 0과 1만 사용 (컴퓨터의 기본 연산 체계)
- **16진수**: 0~9와 A~F 사용 (프로그래밍에서 메모리 주소, 색상 코드 등에 사용)

### JavaScript에서 진수 다루기의 중요성
- **비트 연산**: 플래그 설정, 마스킹 등에서 2진수 활용
- **색상 처리**: 웹 개발에서 RGB 색상을 16진수로 표현
- **메모리 주소**: 디버깅 시 메모리 주소를 16진수로 확인
- **데이터 변환**: 네트워크 통신에서 바이너리 데이터 처리

## 핵심

### 1. 진수 변환 기본 메서드

#### toString() 메서드를 사용한 진수 변환
```javascript
// 10진수를 다른 진수로 변환하는 클래스
class NumberConverter {
    // 10진수를 2진수로 변환
    static toBinary(decimal) {
        return decimal.toString(2);
    }
    
    // 10진수를 8진수로 변환
    static toOctal(decimal) {
        return decimal.toString(8);
    }
    
    // 10진수를 16진수로 변환
    static toHexadecimal(decimal) {
        return decimal.toString(16);
    }
    
    // 10진수를 지정된 진수로 변환
    static toBase(decimal, base) {
        if (base < 2 || base > 36) {
            throw new Error('진수는 2에서 36 사이여야 합니다.');
        }
        return decimal.toString(base);
    }
    
    // 변환 결과를 대문자로 반환
    static toHexadecimalUpper(decimal) {
        return decimal.toString(16).toUpperCase();
    }
}

// 사용 예시
const number = 255;

console.log('10진수:', number);                    // 255
console.log('2진수:', NumberConverter.toBinary(number));           // "11111111"
console.log('8진수:', NumberConverter.toOctal(number));            // "377"
console.log('16진수:', NumberConverter.toHexadecimal(number));     // "ff"
console.log('16진수(대문자):', NumberConverter.toHexadecimalUpper(number)); // "FF"
console.log('5진수:', NumberConverter.toBase(number, 5));          // "2010"
```

#### parseInt() 메서드를 사용한 진수 변환
```javascript
// 문자열을 특정 진수에서 10진수로 변환하는 클래스
class StringToNumberConverter {
    // 2진수 문자열을 10진수로 변환
    static binaryToDecimal(binaryString) {
        return parseInt(binaryString, 2);
    }
    
    // 8진수 문자열을 10진수로 변환
    static octalToDecimal(octalString) {
        return parseInt(octalString, 8);
    }
    
    // 16진수 문자열을 10진수로 변환
    static hexToDecimal(hexString) {
        return parseInt(hexString, 16);
    }
    
    // 지정된 진수의 문자열을 10진수로 변환
    static stringToDecimal(string, base) {
        if (base < 2 || base > 36) {
            throw new Error('진수는 2에서 36 사이여야 합니다.');
        }
        return parseInt(string, base);
    }
    
    // 0x 접두사가 있는 16진수 문자열 처리
    static hexStringToDecimal(hexString) {
        // 0x 접두사 제거 후 변환
        const cleanHex = hexString.replace(/^0x/i, '');
        return parseInt(cleanHex, 16);
    }
}

// 사용 예시
console.log('2진수 "1010" → 10진수:', StringToNumberConverter.binaryToDecimal('1010'));     // 10
console.log('8진수 "17" → 10진수:', StringToNumberConverter.octalToDecimal('17'));          // 15
console.log('16진수 "1f" → 10진수:', StringToNumberConverter.hexToDecimal('1f'));           // 31
console.log('16진수 "0xFF" → 10진수:', StringToNumberConverter.hexStringToDecimal('0xFF')); // 255
console.log('5진수 "2010" → 10진수:', StringToNumberConverter.stringToDecimal('2010', 5));  // 255
```

### 2. 비트 연산자를 활용한 2진수 처리

#### 기본 비트 연산
```javascript
// 비트 연산 유틸리티 클래스
class BitwiseOperations {
    // AND 연산 (&) - 둘 다 1일 때만 1
    static AND(a, b) {
        return a & b;
    }
    
    // OR 연산 (|) - 둘 중 하나라도 1이면 1
    static OR(a, b) {
        return a | b;
    }
    
    // XOR 연산 (^) - 둘이 다를 때만 1
    static XOR(a, b) {
        return a ^ b;
    }
    
    // NOT 연산 (~) - 모든 비트를 뒤집음
    static NOT(a) {
        return ~a;
    }
    
    // 왼쪽 시프트 (<<) - 비트를 왼쪽으로 이동
    static leftShift(a, positions) {
        return a << positions;
    }
    
    // 오른쪽 시프트 (>>) - 부호 있는 오른쪽 시프트
    static rightShift(a, positions) {
        return a >> positions;
    }
    
    // 부호 없는 오른쪽 시프트 (>>>) - 0으로 채움
    static unsignedRightShift(a, positions) {
        return a >>> positions;
    }
    
    // 비트 연산 과정 시각화
    static visualizeOperation(operation, a, b) {
        console.log(`연산: ${operation}`);
        console.log(`A (10진수): ${a}, 2진수: ${a.toString(2).padStart(8, '0')}`);
        console.log(`B (10진수): ${b}, 2진수: ${b.toString(2).padStart(8, '0')}`);
        
        let result;
        switch (operation) {
            case 'AND':
                result = this.AND(a, b);
                break;
            case 'OR':
                result = this.OR(a, b);
                break;
            case 'XOR':
                result = this.XOR(a, b);
                break;
            default:
                throw new Error('지원하지 않는 연산입니다.');
        }
        
        console.log(`결과 (10진수): ${result}, 2진수: ${result.toString(2).padStart(8, '0')}`);
        return result;
    }
}

// 비트 연산 예시
const a = 5;  // 2진수: 00000101
const b = 3;  // 2진수: 00000011

console.log('=== 비트 연산 예시 ===');
BitwiseOperations.visualizeOperation('AND', a, b);  // 1 (00000001)
BitwiseOperations.visualizeOperation('OR', a, b);   // 7 (00000111)
BitwiseOperations.visualizeOperation('XOR', a, b);  // 6 (00000110)

console.log('NOT 연산:', BitwiseOperations.NOT(a));           // -6
console.log('왼쪽 시프트:', BitwiseOperations.leftShift(a, 1)); // 10 (00001010)
console.log('오른쪽 시프트:', BitwiseOperations.rightShift(a, 1)); // 2 (00000010)
```

#### 플래그 시스템 구현
```javascript
// 플래그 시스템 클래스
class FlagSystem {
    constructor() {
        this.flags = 0;
    }
    
    // 플래그 상수 정의
    static FLAGS = {
        READ: 1 << 0,      // 0001
        WRITE: 1 << 1,     // 0010
        EXECUTE: 1 << 2,   // 0100
        DELETE: 1 << 3,    // 1000
        ADMIN: 1 << 4,     // 10000
        GUEST: 1 << 5      // 100000
    };
    
    // 플래그 설정
    setFlag(flag) {
        this.flags |= flag;
    }
    
    // 플래그 제거
    clearFlag(flag) {
        this.flags &= ~flag;
    }
    
    // 플래그 토글
    toggleFlag(flag) {
        this.flags ^= flag;
    }
    
    // 플래그 확인
    hasFlag(flag) {
        return (this.flags & flag) !== 0;
    }
    
    // 모든 플래그 확인
    hasAllFlags(flags) {
        return (this.flags & flags) === flags;
    }
    
    // 플래그 개수 세기
    countFlags() {
        let count = 0;
        let temp = this.flags;
        while (temp) {
            count += temp & 1;
            temp >>= 1;
        }
        return count;
    }
    
    // 플래그 목록 반환
    getActiveFlags() {
        const activeFlags = [];
        for (const [name, flag] of Object.entries(FlagSystem.FLAGS)) {
            if (this.hasFlag(flag)) {
                activeFlags.push(name);
            }
        }
        return activeFlags;
    }
    
    // 플래그 초기화
    reset() {
        this.flags = 0;
    }
    
    // 플래그 상태 출력
    printStatus() {
        console.log('현재 플래그 상태:');
        console.log(`10진수: ${this.flags}`);
        console.log(`2진수: ${this.flags.toString(2).padStart(8, '0')}`);
        console.log(`16진수: 0x${this.flags.toString(16).toUpperCase()}`);
        console.log(`활성 플래그: ${this.getActiveFlags().join(', ')}`);
        console.log(`플래그 개수: ${this.countFlags()}`);
    }
}

// 플래그 시스템 사용 예시
const userPermissions = new FlagSystem();

// 권한 설정
userPermissions.setFlag(FlagSystem.FLAGS.READ);
userPermissions.setFlag(FlagSystem.FLAGS.WRITE);
userPermissions.printStatus();

// 권한 확인
console.log('읽기 권한:', userPermissions.hasFlag(FlagSystem.FLAGS.READ));     // true
console.log('실행 권한:', userPermissions.hasFlag(FlagSystem.FLAGS.EXECUTE)); // false

// 권한 추가
userPermissions.setFlag(FlagSystem.FLAGS.EXECUTE);
userPermissions.printStatus();
```

### 3. Buffer를 활용한 바이너리 데이터 처리

#### 16진수 문자열 처리
```javascript
// Buffer 유틸리티 클래스
class BufferUtils {
    // 16진수 문자열을 Buffer로 변환
    static hexToBuffer(hexString) {
        return Buffer.from(hexString, 'hex');
    }
    
    // Buffer를 16진수 문자열로 변환
    static bufferToHex(buffer) {
        return buffer.toString('hex');
    }
    
    // 16진수 문자열을 일반 문자열로 변환
    static hexToString(hexString) {
        const buffer = Buffer.from(hexString, 'hex');
        return buffer.toString();
    }
    
    // 문자열을 16진수로 변환
    static stringToHex(string) {
        const buffer = Buffer.from(string);
        return buffer.toString('hex');
    }
    
    // 2진수 배열을 Buffer로 변환
    static binaryArrayToBuffer(binaryArray) {
        return Buffer.from(binaryArray);
    }
    
    // Buffer를 2진수 배열로 변환
    static bufferToBinaryArray(buffer) {
        return Array.from(buffer);
    }
    
    // 16진수 데이터 검증
    static isValidHex(hexString) {
        return /^[0-9A-Fa-f]+$/.test(hexString) && hexString.length % 2 === 0;
    }
    
    // Buffer 정보 출력
    static printBufferInfo(buffer, label = 'Buffer') {
        console.log(`=== ${label} 정보 ===`);
        console.log(`크기: ${buffer.length} 바이트`);
        console.log(`16진수: ${buffer.toString('hex')}`);
        console.log(`문자열: ${buffer.toString()}`);
        console.log(`2진수: ${Array.from(buffer).map(b => b.toString(2).padStart(8, '0')).join(' ')}`);
    }
}

// Buffer 사용 예시
const hexString = "48656c6c6f"; // "Hello"의 16진수 표현
const buffer = BufferUtils.hexToBuffer(hexString);

BufferUtils.printBufferInfo(buffer, 'Hello 문자열');

// 문자열 변환
const originalString = BufferUtils.hexToString(hexString);
console.log('원본 문자열:', originalString); // "Hello"

// 문자열을 16진수로 변환
const convertedHex = BufferUtils.stringToHex("Hello");
console.log('변환된 16진수:', convertedHex); // "48656c6c6f"

// 2진수 배열 처리
const binaryArray = [0b01001000, 0b01001001]; // "HI"의 ASCII 코드
const binaryBuffer = BufferUtils.binaryArrayToBuffer(binaryArray);
console.log('2진수 배열 → 문자열:', binaryBuffer.toString()); // "HI"
```

## 예시

### 색상 코드 변환

#### RGB 색상 처리
```javascript
// 색상 변환 유틸리티 클래스
class ColorConverter {
    // RGB를 16진수로 변환
    static rgbToHex(r, g, b) {
        const toHex = (value) => {
            const hex = Math.max(0, Math.min(255, value)).toString(16);
            return hex.length === 1 ? '0' + hex : hex;
        };
        
        return `#${toHex(r)}${toHex(g)}${toHex(b)}`.toUpperCase();
    }
    
    // 16진수를 RGB로 변환
    static hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    }
    
    // RGB를 HSL로 변환
    static rgbToHsl(r, g, b) {
        r /= 255;
        g /= 255;
        b /= 255;
        
        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);
        let h, s, l = (max + min) / 2;
        
        if (max === min) {
            h = s = 0;
        } else {
            const d = max - min;
            s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
            
            switch (max) {
                case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                case g: h = (b - r) / d + 2; break;
                case b: h = (r - g) / d + 4; break;
            }
            h /= 6;
        }
        
        return {
            h: Math.round(h * 360),
            s: Math.round(s * 100),
            l: Math.round(l * 100)
        };
    }
    
    // 색상 밝기 계산
    static getBrightness(r, g, b) {
        return (r * 299 + g * 587 + b * 114) / 1000;
    }
    
    // 색상 대비 계산
    static getContrast(r1, g1, b1, r2, g2, b2) {
        const brightness1 = this.getBrightness(r1, g1, b1);
        const brightness2 = this.getBrightness(r2, g2, b2);
        return Math.abs(brightness1 - brightness2);
    }
    
    // 색상 정보 출력
    static printColorInfo(color) {
        if (color.startsWith('#')) {
            const rgb = this.hexToRgb(color);
            if (rgb) {
                console.log(`색상: ${color}`);
                console.log(`RGB: (${rgb.r}, ${rgb.g}, ${rgb.b})`);
                console.log(`2진수: ${rgb.r.toString(2).padStart(8, '0')} ${rgb.g.toString(2).padStart(8, '0')} ${rgb.b.toString(2).padStart(8, '0')}`);
                
                const hsl = this.rgbToHsl(rgb.r, rgb.g, rgb.b);
                console.log(`HSL: (${hsl.h}°, ${hsl.s}%, ${hsl.l}%)`);
                
                const brightness = this.getBrightness(rgb.r, rgb.g, rgb.b);
                console.log(`밝기: ${brightness.toFixed(2)}`);
            }
        }
    }
}

// 색상 변환 예시
const redHex = ColorConverter.rgbToHex(255, 0, 0);
console.log('빨간색 16진수:', redHex); // "#FF0000"

const rgb = ColorConverter.hexToRgb('#00FF00');
console.log('초록색 RGB:', rgb); // { r: 0, g: 255, b: 0 }

ColorConverter.printColorInfo('#FF6B35');
```

### 메모리 주소 처리

#### 메모리 주소 변환
```javascript
// 메모리 주소 유틸리티 클래스
class MemoryAddressUtils {
    // 10진수 주소를 16진수로 변환
    static decimalToHexAddress(decimal) {
        return `0x${decimal.toString(16).toUpperCase().padStart(8, '0')}`;
    }
    
    // 16진수 주소를 10진수로 변환
    static hexToDecimalAddress(hexAddress) {
        const cleanHex = hexAddress.replace(/^0x/i, '');
        return parseInt(cleanHex, 16);
    }
    
    // 주소 범위 계산
    static calculateAddressRange(baseAddress, size) {
        const start = this.hexToDecimalAddress(baseAddress);
        const end = start + size - 1;
        
        return {
            start: this.decimalToHexAddress(start),
            end: this.decimalToHexAddress(end),
            size: size
        };
    }
    
    // 주소 오프셋 계산
    static calculateOffset(baseAddress, offset) {
        const base = this.hexToDecimalAddress(baseAddress);
        const result = base + offset;
        return this.decimalToHexAddress(result);
    }
    
    // 주소 정렬 확인
    static isAligned(address, alignment) {
        const decimalAddress = this.hexToDecimalAddress(address);
        return decimalAddress % alignment === 0;
    }
    
    // 주소 정보 출력
    static printAddressInfo(address) {
        const decimal = this.hexToDecimalAddress(address);
        const binary = decimal.toString(2).padStart(32, '0');
        
        console.log(`주소: ${address}`);
        console.log(`10진수: ${decimal}`);
        console.log(`2진수: ${binary}`);
        console.log(`8바이트 정렬: ${this.isAligned(address, 8) ? '예' : '아니오'}`);
        console.log(`4바이트 정렬: ${this.isAligned(address, 4) ? '예' : '아니오'}`);
    }
}

// 메모리 주소 처리 예시
const baseAddress = '0x1000';
const offset = 0x123;

console.log('기본 주소:', baseAddress);
console.log('오프셋:', `0x${offset.toString(16).toUpperCase()}`);
console.log('계산된 주소:', MemoryAddressUtils.calculateOffset(baseAddress, offset));

const range = MemoryAddressUtils.calculateAddressRange('0x2000', 1024);
console.log('메모리 범위:', range);

MemoryAddressUtils.printAddressInfo('0x12345678');
```

## 운영 팁

### 성능 최적화

#### 효율적인 진수 변환
```javascript
// 성능 최적화된 진수 변환 클래스
class OptimizedNumberConverter {
    constructor() {
        // 캐시 초기화
        this.cache = new Map();
        this.maxCacheSize = 1000;
    }
    
    // 캐시를 활용한 16진수 변환
    toHexWithCache(decimal) {
        const cacheKey = `hex_${decimal}`;
        
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }
        
        const result = decimal.toString(16).toUpperCase();
        
        // 캐시 크기 제한
        if (this.cache.size >= this.maxCacheSize) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
        
        this.cache.set(cacheKey, result);
        return result;
    }
    
    // 배치 변환 (여러 숫자를 한 번에 처리)
    batchToHex(numbers) {
        return numbers.map(num => this.toHexWithCache(num));
    }
    
    // 캐시 통계
    getCacheStats() {
        return {
            size: this.cache.size,
            maxSize: this.maxCacheSize,
            hitRate: this.calculateHitRate()
        };
    }
    
    // 캐시 히트율 계산 (간단한 구현)
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
const converter = new OptimizedNumberConverter();
const testNumbers = Array.from({ length: 1000 }, (_, i) => i);

console.time('일반 변환');
testNumbers.forEach(num => num.toString(16));
console.timeEnd('일반 변환');

console.time('캐시 변환');
testNumbers.forEach(num => converter.toHexWithCache(num));
console.timeEnd('캐시 변환');

console.log('캐시 통계:', converter.getCacheStats());
```

### 에러 처리

#### 안전한 진수 변환
```javascript
// 안전한 진수 변환 클래스
class SafeNumberConverter {
    // 안전한 16진수 변환
    static safeToHex(value) {
        try {
            // 입력 검증
            if (typeof value !== 'number') {
                throw new Error('숫자 타입이 아닙니다.');
            }
            
            if (!Number.isFinite(value)) {
                throw new Error('유한한 숫자가 아닙니다.');
            }
            
            if (value < 0) {
                throw new Error('음수는 지원하지 않습니다.');
            }
            
            // 변환 수행
            return value.toString(16).toUpperCase();
            
        } catch (error) {
            console.error('16진수 변환 오류:', error.message);
            return null;
        }
    }
    
    // 안전한 문자열 파싱
    static safeParseInt(string, radix = 10) {
        try {
            // 입력 검증
            if (typeof string !== 'string') {
                throw new Error('문자열 타입이 아닙니다.');
            }
            
            if (string.length === 0) {
                throw new Error('빈 문자열입니다.');
            }
            
            // 진수 검증
            if (radix < 2 || radix > 36) {
                throw new Error('진수는 2에서 36 사이여야 합니다.');
            }
            
            // 파싱 수행
            const result = parseInt(string, radix);
            
            if (isNaN(result)) {
                throw new Error('유효하지 않은 숫자입니다.');
            }
            
            return result;
            
        } catch (error) {
            console.error('정수 파싱 오류:', error.message);
            return null;
        }
    }
    
    // 범위 검증
    static validateRange(value, min, max) {
        return value >= min && value <= max;
    }
    
    // 16진수 문자열 검증
    static isValidHex(hexString) {
        return /^[0-9A-Fa-f]+$/.test(hexString);
    }
    
    // 2진수 문자열 검증
    static isValidBinary(binaryString) {
        return /^[01]+$/.test(binaryString);
    }
}

// 안전한 변환 예시
console.log('정상 변환:', SafeNumberConverter.safeToHex(255));           // "FF"
console.log('오류 처리:', SafeNumberConverter.safeToHex('invalid'));     // null
console.log('오류 처리:', SafeNumberConverter.safeToHex(-1));            // null

console.log('정상 파싱:', SafeNumberConverter.safeParseInt('FF', 16));   // 255
console.log('오류 처리:', SafeNumberConverter.safeParseInt('GG', 16));   // null
console.log('오류 처리:', SafeNumberConverter.safeParseInt('', 16));     // null
```

## 참고

### 진수 변환 표준

#### 진수별 변환 표
```javascript
// 진수 변환 표준 클래스
class NumberSystemStandards {
    // 진수별 접두사
    static PREFIXES = {
        binary: '0b',
        octal: '0o',
        hexadecimal: '0x'
    };
    
    // 진수별 최대값 (32비트)
    static MAX_VALUES = {
        binary: 0b11111111111111111111111111111111,
        octal: 0o37777777777,
        decimal: 4294967295,
        hexadecimal: 0xFFFFFFFF
    };
    
    // 진수별 최소값 (32비트)
    static MIN_VALUES = {
        binary: 0b0,
        octal: 0o0,
        decimal: 0,
        hexadecimal: 0x0
    };
    
    // 표준 형식으로 변환
    static toStandardFormat(value, base) {
        switch (base) {
            case 2:
                return `${this.PREFIXES.binary}${value.toString(2)}`;
            case 8:
                return `${this.PREFIXES.octal}${value.toString(8)}`;
            case 16:
                return `${this.PREFIXES.hexadecimal}${value.toString(16).toUpperCase()}`;
            default:
                return value.toString();
        }
    }
    
    // 표준 형식에서 파싱
    static fromStandardFormat(string) {
        if (string.startsWith(this.PREFIXES.binary)) {
            return parseInt(string.slice(2), 2);
        } else if (string.startsWith(this.PREFIXES.octal)) {
            return parseInt(string.slice(2), 8);
        } else if (string.startsWith(this.PREFIXES.hexadecimal)) {
            return parseInt(string.slice(2), 16);
        } else {
            return parseInt(string, 10);
        }
    }
    
    // 진수별 특징 설명
    static getSystemInfo(base) {
        const info = {
            2: {
                name: 'Binary (2진수)',
                digits: '0, 1',
                useCase: '컴퓨터 내부 연산, 비트 연산',
                example: '0b1010'
            },
            8: {
                name: 'Octal (8진수)',
                digits: '0-7',
                useCase: 'Unix 권한, 레거시 시스템',
                example: '0o755'
            },
            10: {
                name: 'Decimal (10진수)',
                digits: '0-9',
                useCase: '일상생활, 일반적인 계산',
                example: '255'
            },
            16: {
                name: 'Hexadecimal (16진수)',
                digits: '0-9, A-F',
                useCase: '메모리 주소, 색상 코드, 디버깅',
                example: '0xFF'
            }
        };
        
        return info[base] || null;
    }
}

// 진수 표준 사용 예시
const value = 255;

console.log('표준 형식:');
console.log('2진수:', NumberSystemStandards.toStandardFormat(value, 2));   // "0b11111111"
console.log('8진수:', NumberSystemStandards.toStandardFormat(value, 8));   // "0o377"
console.log('16진수:', NumberSystemStandards.toStandardFormat(value, 16)); // "0xFF"

console.log('표준 형식 파싱:');
console.log('0b11111111 →', NumberSystemStandards.fromStandardFormat('0b11111111')); // 255
console.log('0xFF →', NumberSystemStandards.fromStandardFormat('0xFF'));             // 255

console.log('16진수 정보:', NumberSystemStandards.getSystemInfo(16));
```

### 결론
JavaScript에서 2진수, 10진수, 16진수를 다루는 방법을 이해하면 비트 연산, 색상 처리, 메모리 주소 처리 등 다양한 프로그래밍 작업에 활용할 수 있습니다.
toString()과 parseInt() 메서드를 활용하여 효율적인 진수 변환이 가능합니다.
비트 연산자를 사용하여 플래그 시스템이나 마스킹 작업을 구현할 수 있습니다.
Buffer 클래스를 활용하여 바이너리 데이터를 효과적으로 처리할 수 있습니다.
성능 최적화와 에러 처리를 고려한 안전한 변환 함수를 구현하는 것이 중요합니다.

