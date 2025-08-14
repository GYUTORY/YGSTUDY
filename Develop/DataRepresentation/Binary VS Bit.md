---
title: Bit, Binary, Byte, and Hexadecimal
tags: [datarepresentation, binary-vs-bit, bit, binary, byte, hexadecimal, data-representation]
updated: 2025-08-14
---

# Bit, Binary, Byte, and Hexadecimal

## 배경

컴퓨터 시스템에서 데이터를 표현하고 처리하는 기본 단위들에 대한 이해는 프로그래밍의 기초가 됩니다. Bit, Binary, Byte, Hexadecimal은 이러한 데이터 표현의 핵심 개념들입니다.

### 데이터 표현의 계층 구조
- **Bit**: 가장 작은 데이터 단위
- **Binary**: 2진수 체계
- **Byte**: 8비트로 구성된 기본 처리 단위
- **Hexadecimal**: 16진수 표현 방식

### 각 개념의 중요성
- **Bit**: 모든 디지털 데이터의 기초
- **Binary**: 컴퓨터의 기본 연산 체계
- **Byte**: 메모리 주소 지정의 기본 단위
- **Hexadecimal**: 프로그래밍에서의 효율적인 데이터 표현

## 핵심

### 1. Bit (비트)

#### 정의와 특징
Bit는 Binary Digit의 약자로, 컴퓨터에서 다루는 가장 작은 데이터 단위입니다. 디지털 시스템에서 정보를 표현하는 기본 단위로, 1948년 클로드 섀넌(Claude Shannon)이 정보 이론을 발표하면서 처음 사용된 용어입니다.

#### 비트의 표현 방식
1비트는 두 가지 상태만을 표현할 수 있습니다:
  - 0 또는 1
  - true 또는 false
  - on 또는 off
  - 전압이 높음 또는 낮음

#### 하드웨어에서의 구현
```javascript
// 비트 상태 시뮬레이션
class BitSimulator {
    constructor() {
        this.value = 0; // 0 또는 1
    }
    
    set(value) {
        this.value = value ? 1 : 0;
    }
    
    get() {
        return this.value;
    }
    
    toggle() {
        this.value = this.value ? 0 : 1;
    }
    
    toString() {
        return this.value.toString();
    }
}

// 사용 예제
const bit = new BitSimulator();
bit.set(1);
console.log(bit.get()); // 1
bit.toggle();
console.log(bit.get()); // 0
```

#### 물리적 구현 방식
- **전자 회로**: 고전압(5V 또는 3.3V) = 1, 저전압(0V) = 0
- **자기 매체**: 자화 방향 = 1 또는 0
- **광학 매체**: 반사/비반사 = 1 또는 0

#### 메모리 셀에서의 비트 저장
```javascript
// 메모리 셀 시뮬레이션
class MemoryCell {
    constructor() {
        this.charge = 0; // DRAM 시뮬레이션
        this.state = false; // SRAM 시뮬레이션
    }
    
    // DRAM 방식 (커패시터 충전/방전)
    writeDRAM(value) {
        this.charge = value ? 1 : 0;
    }
    
    readDRAM() {
        return this.charge > 0.5 ? 1 : 0;
    }
    
    // SRAM 방식 (플립플롭)
    writeSRAM(value) {
        this.state = value;
    }
    
    readSRAM() {
        return this.state ? 1 : 0;
    }
    
    // Flash Memory 방식 (플로팅 게이트)
    writeFlash(value) {
        this.charge = value ? 1 : 0;
        // Flash는 한 번 쓰면 지우기 전까지 유지
    }
    
    readFlash() {
        return this.charge > 0.5 ? 1 : 0;
    }
}
```

#### 논리 게이트 구현
```javascript
// 기본 논리 게이트 시뮬레이션
class LogicGates {
    // AND 게이트: 두 입력이 모두 1일 때만 1 출력
    static AND(a, b) {
        return a && b ? 1 : 0;
    }
    
    // OR 게이트: 입력 중 하나라도 1이면 1 출력
    static OR(a, b) {
        return a || b ? 1 : 0;
    }
    
    // NOT 게이트: 입력의 반대값 출력
    static NOT(a) {
        return a ? 0 : 1;
    }
    
    // XOR 게이트: 입력이 서로 다를 때만 1 출력
    static XOR(a, b) {
        return a !== b ? 1 : 0;
    }
    
    // NAND 게이트: AND의 결과를 NOT
    static NAND(a, b) {
        return this.NOT(this.AND(a, b));
    }
    
    // NOR 게이트: OR의 결과를 NOT
    static NOR(a, b) {
        return this.NOT(this.OR(a, b));
    }
}

// 사용 예제
console.log('AND:', LogicGates.AND(1, 1)); // 1
console.log('AND:', LogicGates.AND(1, 0)); // 0
console.log('OR:', LogicGates.OR(1, 0));   // 1
console.log('XOR:', LogicGates.XOR(1, 0)); // 1
console.log('NOT:', LogicGates.NOT(1));    // 0
```

### 2. Binary (이진수)

#### 정의와 특징
2진수 체계는 0과 1만을 사용하여 숫자를 표현하는 방식입니다. 컴퓨터의 기본 연산 체계로, 모든 디지털 데이터의 근간이 됩니다. 고트프리트 라이프니츠(Gottfried Leibniz)가 현대 이진수 체계를 체계화했습니다.

#### 위치 기수법
위치 기수법(positional notation)을 사용하며, 각 자릿수는 2의 거듭제곱을 나타냅니다.

```javascript
// 2진수 계산 함수
class BinaryCalculator {
    // 2진수를 10진수로 변환
    static binaryToDecimal(binary) {
        let decimal = 0;
        const binaryStr = binary.toString();
        
        for (let i = 0; i < binaryStr.length; i++) {
            const digit = parseInt(binaryStr[i]);
            const power = binaryStr.length - 1 - i;
            decimal += digit * Math.pow(2, power);
        }
        
        return decimal;
    }
    
    // 10진수를 2진수로 변환
    static decimalToBinary(decimal) {
        if (decimal === 0) return '0';
        
        let binary = '';
        let num = decimal;
        
        while (num > 0) {
            binary = (num % 2) + binary;
            num = Math.floor(num / 2);
        }
        
        return binary;
    }
    
    // 2진수 덧셈
    static add(a, b) {
        const decimalA = this.binaryToDecimal(a);
        const decimalB = this.binaryToDecimal(b);
        const sum = decimalA + decimalB;
        return this.decimalToBinary(sum);
    }
    
    // 2진수 뺄셈
    static subtract(a, b) {
        const decimalA = this.binaryToDecimal(a);
        const decimalB = this.binaryToDecimal(b);
        const difference = decimalA - decimalB;
        return this.decimalToBinary(Math.max(0, difference));
    }
    
    // 2진수 곱셈
    static multiply(a, b) {
        const decimalA = this.binaryToDecimal(a);
        const decimalB = this.binaryToDecimal(b);
        const product = decimalA * decimalB;
        return this.decimalToBinary(product);
    }
}

// 사용 예제
console.log('1011₂ =', BinaryCalculator.binaryToDecimal(1011), '₁₀');
console.log('11₁₀ =', BinaryCalculator.decimalToBinary(11), '₂');
console.log('101 + 110 =', BinaryCalculator.add(101, 110));
console.log('1010 - 11 =', BinaryCalculator.subtract(1010, 11));
console.log('101 × 11 =', BinaryCalculator.multiply(101, 11));
```

#### 2진수 연산 규칙
```javascript
// 2진수 연산 규칙 시각화
class BinaryOperations {
    static additionTable() {
        console.log('2진수 덧셈 규칙:');
        console.log('0 + 0 = 0');
        console.log('0 + 1 = 1');
        console.log('1 + 0 = 1');
        console.log('1 + 1 = 10 (캐리 발생)');
    }
    
    static subtractionTable() {
        console.log('2진수 뺄셈 규칙:');
        console.log('0 - 0 = 0');
        console.log('1 - 0 = 1');
        console.log('1 - 1 = 0');
        console.log('0 - 1 = 1 (빌림 발생)');
    }
    
    static multiplicationTable() {
        console.log('2진수 곱셈 규칙:');
        console.log('0 × 0 = 0');
        console.log('0 × 1 = 0');
        console.log('1 × 0 = 0');
        console.log('1 × 1 = 1');
    }
    
    // 캐리와 빌림을 고려한 덧셈
    static addWithCarry(a, b) {
        const aStr = a.toString().padStart(8, '0');
        const bStr = b.toString().padStart(8, '0');
        let result = '';
        let carry = 0;
        
        for (let i = 7; i >= 0; i--) {
            const sum = parseInt(aStr[i]) + parseInt(bStr[i]) + carry;
            result = (sum % 2) + result;
            carry = Math.floor(sum / 2);
        }
        
        if (carry > 0) {
            result = carry + result;
        }
        
        return result;
    }
}

BinaryOperations.additionTable();
BinaryOperations.subtractionTable();
BinaryOperations.multiplicationTable();

console.log('캐리 고려 덧셈:', BinaryOperations.addWithCarry(1011, 1101));
```

### 3. Byte (바이트)

#### 정의와 특징
8개의 비트로 구성된 데이터 단위입니다. 컴퓨터에서 가장 기본적인 데이터 처리 단위로, 1956년 IBM의 System/360에서 처음 사용된 용어입니다.

#### 바이트의 용량
- 1 byte = 8 bits
- 2⁸ = 256가지의 서로 다른 값을 표현할 수 있습니다
- ASCII 문자 하나를 저장할 수 있는 최소 단위입니다

#### 바이트 단위 변환
```javascript
// 바이트 단위 변환 클래스
class ByteConverter {
    // 기본 단위 변환
    static bytesToKB(bytes) {
        return bytes / 1024;
    }
    
    static bytesToMB(bytes) {
        return bytes / (1024 * 1024);
    }
    
    static bytesToGB(bytes) {
        return bytes / (1024 * 1024 * 1024);
    }
    
    static bytesToTB(bytes) {
        return bytes / (1024 * 1024 * 1024 * 1024);
    }
    
    // 이진 접두사 변환 (정확한 1024 배수)
    static bytesToKiB(bytes) {
        return bytes / 1024;
    }
    
    static bytesToMiB(bytes) {
        return bytes / (1024 * 1024);
    }
    
    static bytesToGiB(bytes) {
        return bytes / (1024 * 1024 * 1024);
    }
    
    static bytesToTiB(bytes) {
        return bytes / (1024 * 1024 * 1024 * 1024);
    }
    
    // 사람이 읽기 쉬운 형태로 변환
    static toHumanReadable(bytes) {
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let size = bytes;
        let unitIndex = 0;
        
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        
        return `${size.toFixed(2)} ${units[unitIndex]}`;
    }
    
    // 바이트 배열 생성
    static createByteArray(size) {
        return new Uint8Array(size);
    }
    
    // 바이트 패턴 생성
    static createPattern(pattern) {
        const bytes = new Uint8Array(pattern.length);
        for (let i = 0; i < pattern.length; i++) {
            bytes[i] = parseInt(pattern[i], 16);
        }
        return bytes;
    }
}

// 사용 예제
const fileSize = 1048576; // 1MB
console.log('파일 크기:', ByteConverter.toHumanReadable(fileSize));
console.log('KB로 변환:', ByteConverter.bytesToKB(fileSize));
console.log('KiB로 변환:', ByteConverter.bytesToKiB(fileSize));

// 바이트 배열 생성
const byteArray = ByteConverter.createByteArray(4);
byteArray[0] = 0xFF;
byteArray[1] = 0x00;
byteArray[2] = 0xFF;
byteArray[3] = 0x00;

console.log('바이트 배열:', Array.from(byteArray).map(b => b.toString(16).padStart(2, '0')));
```

#### 문자 표현과 바이트
```javascript
// 문자와 바이트 관계
class CharacterEncoding {
    // ASCII 문자를 바이트로 변환
    static charToByte(char) {
        return char.charCodeAt(0);
    }
    
    // 바이트를 ASCII 문자로 변환
    static byteToChar(byte) {
        return String.fromCharCode(byte);
    }
    
    // 문자열을 바이트 배열로 변환
    static stringToBytes(str) {
        const bytes = new Uint8Array(str.length);
        for (let i = 0; i < str.length; i++) {
            bytes[i] = str.charCodeAt(i);
        }
        return bytes;
    }
    
    // 바이트 배열을 문자열로 변환
    static bytesToString(bytes) {
        return String.fromCharCode(...bytes);
    }
    
    // UTF-8 인코딩 시뮬레이션
    static stringToUTF8Bytes(str) {
        const encoder = new TextEncoder();
        return encoder.encode(str);
    }
    
    // UTF-8 디코딩 시뮬레이션
    static utf8BytesToString(bytes) {
        const decoder = new TextDecoder();
        return decoder.decode(bytes);
    }
}

// 사용 예제
const text = "Hello";
console.log('문자열:', text);

const asciiBytes = CharacterEncoding.stringToBytes(text);
console.log('ASCII 바이트:', Array.from(asciiBytes));

const utf8Bytes = CharacterEncoding.stringToUTF8Bytes(text);
console.log('UTF-8 바이트:', Array.from(utf8Bytes));

console.log('ASCII 복원:', CharacterEncoding.bytesToString(asciiBytes));
console.log('UTF-8 복원:', CharacterEncoding.utf8BytesToString(utf8Bytes));
```

### 4. Hexadecimal (16진수)

#### 정의와 특징
16진수는 0-9와 A-F를 사용하여 숫자를 표현하는 방식입니다. 컴퓨터 과학에서 널리 사용되는 수 표현 방식으로, 2진수를 더 간단하게 표현할 수 있는 방법입니다.

#### 16진수의 장점
- 한 자리의 16진수는 4비트를 표현할 수 있습니다
- 두 자리의 16진수는 1바이트(8비트)를 표현할 수 있습니다
- 2진수보다 읽고 쓰기가 더 편리합니다

#### 16진수 변환 및 활용
```javascript
// 16진수 변환 및 활용 클래스
class HexadecimalConverter {
    // 10진수를 16진수로 변환
    static decimalToHex(decimal) {
        return decimal.toString(16).toUpperCase();
    }
    
    // 16진수를 10진수로 변환
    static hexToDecimal(hex) {
        return parseInt(hex, 16);
    }
    
    // 2진수를 16진수로 변환
    static binaryToHex(binary) {
        const decimal = parseInt(binary, 2);
        return decimal.toString(16).toUpperCase();
    }
    
    // 16진수를 2진수로 변환
    static hexToBinary(hex) {
        const decimal = parseInt(hex, 16);
        return decimal.toString(2);
    }
    
    // 메모리 주소 포맷팅
    static formatMemoryAddress(address) {
        return `0x${address.toString(16).toUpperCase().padStart(8, '0')}`;
    }
    
    // 색상 코드 생성
    static rgbToHex(r, g, b) {
        return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`.toUpperCase();
    }
    
    // 색상 코드를 RGB로 변환
    static hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    }
    
    // 16진수 덧셈
    static addHex(a, b) {
        const decimalA = this.hexToDecimal(a);
        const decimalB = this.hexToDecimal(b);
        return this.decimalToHex(decimalA + decimalB);
    }
    
    // 16진수 뺄셈
    static subtractHex(a, b) {
        const decimalA = this.hexToDecimal(a);
        const decimalB = this.hexToDecimal(b);
        return this.decimalToHex(Math.max(0, decimalA - decimalB));
    }
}

// 사용 예제
console.log('255를 16진수로:', HexadecimalConverter.decimalToHex(255));
console.log('FF를 10진수로:', HexadecimalConverter.hexToDecimal('FF'));
console.log('1010을 16진수로:', HexadecimalConverter.binaryToHex('1010'));
console.log('A를 2진수로:', HexadecimalConverter.hexToBinary('A'));

// 메모리 주소 예제
const memoryAddress = 0x7FFF1234;
console.log('메모리 주소:', HexadecimalConverter.formatMemoryAddress(memoryAddress));

// 색상 코드 예제
const color = HexadecimalConverter.rgbToHex(255, 0, 0);
console.log('빨간색 코드:', color);
console.log('RGB 값:', HexadecimalConverter.hexToRgb(color));

// 16진수 연산
console.log('A + B =', HexadecimalConverter.addHex('A', 'B'));
console.log('F - 5 =', HexadecimalConverter.subtractHex('F', '5'));
```

## 예시

### 실전 활용 예제

#### 메모리 덤프 시뮬레이션
```javascript
// 메모리 덤프 시뮬레이터
class MemoryDumpSimulator {
    constructor(size = 256) {
        this.memory = new Uint8Array(size);
        this.initializeMemory();
    }
    
    // 메모리 초기화
    initializeMemory() {
        for (let i = 0; i < this.memory.length; i++) {
            this.memory[i] = Math.floor(Math.random() * 256);
        }
    }
    
    // 메모리 덤프 출력
    dumpMemory(startAddress = 0, length = 16) {
        console.log('Memory Dump:');
        console.log('Address   00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F  ASCII');
        console.log('--------  -----------------------------------------------  ----------------');
        
        for (let i = startAddress; i < startAddress + length; i += 16) {
            const address = i.toString(16).padStart(8, '0').toUpperCase();
            let hexLine = '';
            let asciiLine = '';
            
            for (let j = 0; j < 16; j++) {
                if (i + j < this.memory.length) {
                    const byte = this.memory[i + j];
                    hexLine += byte.toString(16).padStart(2, '0').toUpperCase() + ' ';
                    asciiLine += (byte >= 32 && byte <= 126) ? String.fromCharCode(byte) : '.';
                } else {
                    hexLine += '   ';
                    asciiLine += ' ';
                }
            }
            
            console.log(`${address}  ${hexLine} ${asciiLine}`);
        }
    }
    
    // 특정 주소의 값 읽기
    readByte(address) {
        if (address >= 0 && address < this.memory.length) {
            return this.memory[address];
        }
        throw new Error('Invalid memory address');
    }
    
    // 특정 주소에 값 쓰기
    writeByte(address, value) {
        if (address >= 0 && address < this.memory.length) {
            this.memory[address] = value & 0xFF;
        } else {
            throw new Error('Invalid memory address');
        }
    }
    
    // 문자열을 메모리에 저장
    writeString(address, string) {
        for (let i = 0; i < string.length; i++) {
            this.writeByte(address + i, string.charCodeAt(i));
        }
        // null 종료 문자 추가
        this.writeByte(address + string.length, 0);
    }
    
    // 메모리에서 문자열 읽기
    readString(address) {
        let string = '';
        let i = 0;
        
        while (true) {
            const byte = this.readByte(address + i);
            if (byte === 0) break; // null 종료 문자
            string += String.fromCharCode(byte);
            i++;
        }
        
        return string;
    }
}

// 사용 예제
const memory = new MemoryDumpSimulator(64);
memory.dumpMemory(0, 32);

// 문자열 저장 및 읽기
memory.writeString(0x10, "Hello, World!");
console.log('저장된 문자열:', memory.readString(0x10));

// 특정 주소 값 수정
memory.writeByte(0x20, 0xFF);
console.log('0x20 주소의 값:', memory.readByte(0x20).toString(16).toUpperCase());
```

#### 파일 시스템 시뮬레이션
```javascript
// 간단한 파일 시스템 시뮬레이터
class FileSystemSimulator {
    constructor() {
        this.storage = new Map();
        this.fileTable = new Map();
        this.nextFileId = 1;
    }
    
    // 파일 생성
    createFile(filename, content) {
        const fileId = this.nextFileId++;
        const fileInfo = {
            id: fileId,
            name: filename,
            size: content.length,
            created: new Date(),
            modified: new Date(),
            content: content
        };
        
        this.fileTable.set(fileId, fileInfo);
        this.storage.set(filename, fileInfo);
        
        return fileId;
    }
    
    // 파일 읽기
    readFile(filename) {
        const file = this.storage.get(filename);
        if (!file) {
            throw new Error(`File not found: ${filename}`);
        }
        return file.content;
    }
    
    // 파일 정보 조회
    getFileInfo(filename) {
        const file = this.storage.get(filename);
        if (!file) {
            throw new Error(`File not found: ${filename}`);
        }
        return {
            name: file.name,
            size: file.size,
            created: file.created,
            modified: file.modified
        };
    }
    
    // 파일 목록 조회
    listFiles() {
        return Array.from(this.storage.keys());
    }
    
    // 파일 삭제
    deleteFile(filename) {
        const file = this.storage.get(filename);
        if (!file) {
            throw new Error(`File not found: ${filename}`);
        }
        
        this.storage.delete(filename);
        this.fileTable.delete(file.id);
        
        return true;
    }
    
    // 파일 시스템 상태 출력
    printStatus() {
        console.log('File System Status:');
        console.log('==================');
        console.log(`Total files: ${this.storage.size}`);
        console.log(`Total storage used: ${this.getTotalSize()} bytes`);
        console.log('\nFiles:');
        
        for (const [filename, file] of this.storage) {
            console.log(`  ${filename} (${file.size} bytes) - Modified: ${file.modified.toLocaleString()}`);
        }
    }
    
    // 총 저장 공간 계산
    getTotalSize() {
        let total = 0;
        for (const file of this.storage.values()) {
            total += file.size;
        }
        return total;
    }
}

// 사용 예제
const fs = new FileSystemSimulator();

// 파일 생성
fs.createFile('hello.txt', 'Hello, World!');
fs.createFile('data.bin', new Uint8Array([0x48, 0x65, 0x6C, 0x6C, 0x6F]));
fs.createFile('config.json', '{"name": "test", "version": "1.0"}');

// 파일 시스템 상태 출력
fs.printStatus();

// 파일 읽기
console.log('\n파일 내용:');
console.log('hello.txt:', fs.readFile('hello.txt'));
console.log('config.json:', fs.readFile('config.json'));

// 파일 정보 조회
console.log('\n파일 정보:');
console.log('hello.txt:', fs.getFileInfo('hello.txt'));
```

## 운영 팁

### 성능 최적화

#### 메모리 정렬 최적화
```javascript
// 메모리 정렬 최적화 클래스
class MemoryAlignment {
    // 워드 경계 정렬 확인
    static isWordAligned(address, wordSize = 4) {
        return address % wordSize === 0;
    }
    
    // 워드 경계로 정렬
    static alignToWord(address, wordSize = 4) {
        return Math.ceil(address / wordSize) * wordSize;
    }
    
    // 캐시 라인 크기로 정렬
    static alignToCacheLine(address, cacheLineSize = 64) {
        return Math.ceil(address / cacheLineSize) * cacheLineSize;
    }
    
    // 구조체 패딩 계산
    static calculateStructPadding(fields) {
        let offset = 0;
        let maxAlignment = 1;
        
        for (const field of fields) {
            const alignment = this.getAlignmentForType(field.type);
            maxAlignment = Math.max(maxAlignment, alignment);
            
            // 패딩 추가
            const padding = (alignment - (offset % alignment)) % alignment;
            offset += padding;
            
            offset += field.size;
        }
        
        // 구조체 끝 패딩
        const finalPadding = (maxAlignment - (offset % maxAlignment)) % maxAlignment;
        offset += finalPadding;
        
        return {
            totalSize: offset,
            maxAlignment: maxAlignment
        };
    }
    
    // 타입별 정렬 요구사항
    static getAlignmentForType(type) {
        const alignments = {
            'char': 1,
            'short': 2,
            'int': 4,
            'long': 8,
            'float': 4,
            'double': 8,
            'pointer': 8
        };
        
        return alignments[type] || 1;
    }
}

// 사용 예제
const address = 0x1003;
console.log('원본 주소:', address.toString(16));
console.log('워드 정렬됨:', MemoryAlignment.isWordAligned(address));
console.log('정렬된 주소:', MemoryAlignment.alignToWord(address).toString(16));

// 구조체 패딩 계산
const structFields = [
    { name: 'char1', type: 'char', size: 1 },
    { name: 'int1', type: 'int', size: 4 },
    { name: 'char2', type: 'char', size: 1 },
    { name: 'double1', type: 'double', size: 8 }
];

const padding = MemoryAlignment.calculateStructPadding(structFields);
console.log('구조체 크기:', padding.totalSize);
console.log('최대 정렬:', padding.maxAlignment);
```

### 메모리 효율성

#### 비트 필드 최적화
```javascript
// 비트 필드 최적화 클래스
class BitFieldOptimizer {
    constructor() {
        this.fields = new Map();
        this.currentBit = 0;
    }
    
    // 비트 필드 추가
    addField(name, bits) {
        this.fields.set(name, {
            startBit: this.currentBit,
            bits: bits,
            mask: (1 << bits) - 1
        });
        this.currentBit += bits;
    }
    
    // 값 설정
    setValue(data, fieldName, value) {
        const field = this.fields.get(fieldName);
        if (!field) {
            throw new Error(`Field not found: ${fieldName}`);
        }
        
        const maskedValue = value & field.mask;
        const clearedData = data & ~(field.mask << field.startBit);
        return clearedData | (maskedValue << field.startBit);
    }
    
    // 값 읽기
    getValue(data, fieldName) {
        const field = this.fields.get(fieldName);
        if (!field) {
            throw new Error(`Field not found: ${fieldName}`);
        }
        
        return (data >> field.startBit) & field.mask;
    }
    
    // 비트 필드 정보 출력
    printFields() {
        console.log('Bit Field Layout:');
        console.log('================');
        
        for (const [name, field] of this.fields) {
            console.log(`${name}: bits ${field.startBit}-${field.startBit + field.bits - 1} (${field.bits} bits)`);
        }
        
        console.log(`Total bits used: ${this.currentBit}`);
    }
}

// 사용 예제
const optimizer = new BitFieldOptimizer();

// 네트워크 패킷 헤더 비트 필드 정의
optimizer.addField('version', 4);      // 4비트
optimizer.addField('headerLength', 4); // 4비트
optimizer.addField('typeOfService', 8); // 8비트
optimizer.addField('totalLength', 16);  // 16비트

optimizer.printFields();

// 값 설정 및 읽기
let packetHeader = 0;
packetHeader = optimizer.setValue(packetHeader, 'version', 4);
packetHeader = optimizer.setValue(packetHeader, 'headerLength', 5);
packetHeader = optimizer.setValue(packetHeader, 'typeOfService', 0);
packetHeader = optimizer.setValue(packetHeader, 'totalLength', 1500);

console.log('패킷 헤더:', packetHeader.toString(16).toUpperCase());
console.log('버전:', optimizer.getValue(packetHeader, 'version'));
console.log('헤더 길이:', optimizer.getValue(packetHeader, 'headerLength'));
console.log('서비스 타입:', optimizer.getValue(packetHeader, 'typeOfService'));
console.log('총 길이:', optimizer.getValue(packetHeader, 'totalLength'));
```

## 참고

### 데이터 표현의 수학적 기초

#### 정보 이론과 엔트로피
```javascript
// 정보 이론 계산 클래스
class InformationTheory {
    // 엔트로피 계산 (Shannon entropy)
    static calculateEntropy(probabilities) {
        let entropy = 0;
        
        for (const p of probabilities) {
            if (p > 0) {
                entropy -= p * Math.log2(p);
            }
        }
        
        return entropy;
    }
    
    // 정보량 계산
    static calculateInformation(probability) {
        return -Math.log2(probability);
    }
    
    // 평균 정보량 계산
    static calculateAverageInformation(probabilities) {
        let avgInfo = 0;
        
        for (const p of probabilities) {
            if (p > 0) {
                avgInfo += p * this.calculateInformation(p);
            }
        }
        
        return avgInfo;
    }
    
    // 데이터 압축률 계산
    static calculateCompressionRatio(originalSize, compressedSize) {
        return (1 - compressedSize / originalSize) * 100;
    }
    
    // 비트 효율성 계산
    static calculateBitEfficiency(dataSize, informationBits) {
        return informationBits / dataSize;
    }
}

// 사용 예제
const probabilities = [0.25, 0.25, 0.25, 0.25]; // 균등 분포
console.log('엔트로피:', InformationTheory.calculateEntropy(probabilities));

const biasedProbabilities = [0.5, 0.25, 0.125, 0.125]; // 편향된 분포
console.log('편향된 엔트로피:', InformationTheory.calculateEntropy(biasedProbabilities));

const originalSize = 1000;
const compressedSize = 600;
console.log('압축률:', InformationTheory.calculateCompressionRatio(originalSize, compressedSize) + '%');
```

### 결론
Bit, Binary, Byte, Hexadecimal은 컴퓨터 시스템의 데이터 표현을 이해하는 핵심 개념입니다.
Bit는 모든 디지털 데이터의 기초가 되는 최소 단위입니다.
Binary는 컴퓨터의 기본 연산 체계로, 모든 디지털 데이터의 근간이 됩니다.
Byte는 메모리 주소 지정의 기본 단위로, 문자 표현과 데이터 처리의 기준이 됩니다.
Hexadecimal은 프로그래밍에서 2진수를 더 간결하게 표현하는 효율적인 방법입니다.
이러한 개념들을 이해하고 적절히 활용하면 메모리 효율성과 성능을 최적화할 수 있습니다.
실제 개발에서는 이러한 기본 개념들을 바탕으로 더 복잡한 데이터 구조와 알고리즘을 구현할 수 있습니다.
