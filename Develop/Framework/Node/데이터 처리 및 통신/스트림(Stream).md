---
title: Node.js Stream (스트림)
tags: [framework, node, 데이터-처리-및-통신, stream, nodejs, data-processing]
updated: 2025-08-10
---

# Node.js Stream (스트림)

## 배경

Stream(스트림)은 데이터를 작은 조각(Chunk) 단위로 읽고 쓰는 방식입니다. 일반적인 파일이나 데이터를 처리할 때 한꺼번에 메모리에 로드하는 방식이 아니라, 데이터를 스트리밍하여 처리 속도와 메모리 효율을 극대화할 수 있습니다.

### 스트림의 필요성
- **메모리 효율성**: 대용량 파일을 한 번에 메모리에 로드하지 않음
- **처리 속도**: 데이터를 받는 즉시 처리 가능
- **실시간 처리**: 데이터가 생성되는 대로 처리
- **확장성**: 대용량 데이터도 효율적으로 처리

### 스트림의 핵심 개념
- **Chunk 단위 처리**: 데이터를 작은 조각으로 나누어 처리
- **백프레셔(Backpressure)**: 데이터 처리 속도 조절
- **파이프라인**: 여러 스트림을 연결하여 복잡한 처리 가능
- **이벤트 기반**: 데이터 흐름을 이벤트로 관리

## 핵심

### Node.js에서 제공하는 스트림의 유형

Node.js의 스트림은 크게 4가지 유형으로 나뉩니다:

#### 1. Readable Stream (읽기 스트림)
- 데이터를 읽어들이는 역할을 하는 스트림
- 예제: 파일을 읽거나, HTTP 요청에서 데이터를 받을 때 사용

#### 2. Writable Stream (쓰기 스트림)
- 데이터를 쓰기 위한 스트림
- 예제: 파일에 데이터를 쓰거나, HTTP 응답을 보낼 때 사용

#### 3. Duplex Stream (양방향 스트림)
- 읽기와 쓰기가 동시에 가능한 스트림
- 예제: 네트워크 소켓(Socket) 통신

#### 4. Transform Stream (변환 스트림)
- 입력 데이터를 받아 변환하여 출력하는 스트림
- 예제: 파일 압축(Gzip), 데이터 암호화

### 스트림의 상태

#### Readable Stream 상태
```javascript
// 스트림의 상태 확인
const readableStream = fs.createReadStream('file.txt');

console.log('스트림 상태:', readableStream.readable);
console.log('읽기 가능한 바이트:', readableStream.readableLength);
console.log('파이프된 스트림 수:', readableStream.readableObjectMode);
```

#### Writable Stream 상태
```javascript
// 쓰기 스트림 상태 확인
const writableStream = fs.createWriteStream('output.txt');

console.log('스트림 상태:', writableStream.writable);
console.log('버퍼 크기:', writableStream.writableLength);
console.log('최대 버퍼 크기:', writableStream.writableHighWaterMark);
```

## 예시

### 기본 스트림 예제

#### Readable Stream (읽기 스트림)
```javascript
const fs = require('fs');

// fs.createReadStream을 사용하여 파일을 읽기 스트림으로 열기
const readableStream = fs.createReadStream('example.txt', { 
    encoding: 'utf8',
    highWaterMark: 64 * 1024 // 64KB 청크 크기
});

// 데이터가 읽힐 때마다 실행되는 이벤트 리스너
readableStream.on('data', chunk => {
    console.log('읽은 데이터 크기:', chunk.length);
    console.log('읽은 데이터:', chunk.substring(0, 100) + '...');
});

// 스트림이 끝났을 때 실행되는 이벤트 리스너
readableStream.on('end', () => {
    console.log('파일 읽기 완료!');
});

// 오류 발생 시 처리
readableStream.on('error', error => {
    console.error('읽기 오류:', error);
});
```

#### Writable Stream (쓰기 스트림)
```javascript
const fs = require('fs');

// 파일 쓰기 스트림 생성
const writableStream = fs.createWriteStream('output.txt', {
    encoding: 'utf8',
    flags: 'w' // 쓰기 모드
});

// 데이터 쓰기
writableStream.write('첫 번째 줄\n');
writableStream.write('두 번째 줄\n');
writableStream.write('세 번째 줄\n');

// 스트림 종료
writableStream.end();

// 쓰기 완료 이벤트
writableStream.on('finish', () => {
    console.log('파일 쓰기 완료!');
});

// 오류 처리
writableStream.on('error', error => {
    console.error('쓰기 오류:', error);
});
```

#### 파이프를 사용한 파일 복사
```javascript
const fs = require('fs');

// 파일 복사 (스트림 파이프 사용)
const readStream = fs.createReadStream('input.txt');
const writeStream = fs.createWriteStream('output.txt');

// 파이프로 연결
readStream.pipe(writeStream);

// 복사 완료 이벤트
writeStream.on('finish', () => {
    console.log('파일 복사 완료!');
});

// 오류 처리
readStream.on('error', error => {
    console.error('읽기 오류:', error);
});

writeStream.on('error', error => {
    console.error('쓰기 오류:', error);
});
```

### 고급 스트림 예제

#### Transform Stream (변환 스트림)
```javascript
const { Transform } = require('stream');

// 대문자 변환 스트림
class UpperCaseTransform extends Transform {
    constructor(options = {}) {
        super(options);
    }

    _transform(chunk, encoding, callback) {
        // 데이터를 대문자로 변환
        const upperChunk = chunk.toString().toUpperCase();
        this.push(upperChunk);
        callback();
    }
}

// 사용 예시
const fs = require('fs');
const upperCaseTransform = new UpperCaseTransform();

const readStream = fs.createReadStream('input.txt');
const writeStream = fs.createWriteStream('output.txt');

// 파이프라인 연결
readStream
    .pipe(upperCaseTransform)
    .pipe(writeStream);

writeStream.on('finish', () => {
    console.log('대문자 변환 완료!');
});
```

#### 커스텀 Readable Stream
```javascript
const { Readable } = require('stream');

// 숫자 생성 스트림
class NumberGenerator extends Readable {
    constructor(options = {}) {
        super(options);
        this.counter = 0;
        this.maxCount = options.maxCount || 100;
    }

    _read(size) {
        if (this.counter >= this.maxCount) {
            this.push(null); // 스트림 종료
            return;
        }

        // 숫자를 문자열로 변환하여 푸시
        const number = this.counter++;
        this.push(number.toString() + '\n');
    }
}

// 사용 예시
const numberStream = new NumberGenerator({ maxCount: 10 });
const writeStream = fs.createWriteStream('numbers.txt');

numberStream.pipe(writeStream);

writeStream.on('finish', () => {
    console.log('숫자 생성 완료!');
});
```

#### 실전 애플리케이션 예제

#### HTTP 파일 업로드 처리
```javascript
const http = require('http');
const fs = require('fs');
const { Transform } = require('stream');

// 파일 업로드 처리 서버
const server = http.createServer((req, res) => {
    if (req.method === 'POST' && req.url === '/upload') {
        console.log('파일 업로드 시작');
        
        // 파일 쓰기 스트림 생성
        const writeStream = fs.createWriteStream('uploaded-file.txt');
        
        // 업로드 진행률 추적
        let uploadedBytes = 0;
        const contentLength = parseInt(req.headers['content-length'], 10);
        
        // 진행률 변환 스트림
        const progressTransform = new Transform({
            transform(chunk, encoding, callback) {
                uploadedBytes += chunk.length;
                const progress = (uploadedBytes / contentLength * 100).toFixed(2);
                console.log(`업로드 진행률: ${progress}%`);
                
                this.push(chunk);
                callback();
            }
        });
        
        // 파이프라인 연결
        req.pipe(progressTransform).pipe(writeStream);
        
        writeStream.on('finish', () => {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ 
                message: '파일 업로드 완료',
                size: uploadedBytes 
            }));
        });
        
        writeStream.on('error', (error) => {
            console.error('업로드 오류:', error);
            res.writeHead(500);
            res.end('업로드 실패');
        });
    } else {
        res.writeHead(404);
        res.end('Not Found');
    }
});

server.listen(3000, () => {
    console.log('파일 업로드 서버가 포트 3000에서 실행 중입니다.');
});
```

#### 데이터 압축 및 암호화 파이프라인
```javascript
const fs = require('fs');
const zlib = require('zlib');
const crypto = require('crypto');
const { Transform } = require('stream');

// 암호화 변환 스트림
class EncryptionTransform extends Transform {
    constructor(password, options = {}) {
        super(options);
        this.cipher = crypto.createCipher('aes-256-cbc', password);
    }

    _transform(chunk, encoding, callback) {
        const encrypted = this.cipher.update(chunk, encoding, 'hex');
        this.push(encrypted);
        callback();
    }

    _flush(callback) {
        const final = this.cipher.final('hex');
        this.push(final);
        callback();
    }
}

// 복호화 변환 스트림
class DecryptionTransform extends Transform {
    constructor(password, options = {}) {
        super(options);
        this.decipher = crypto.createDecipher('aes-256-cbc', password);
    }

    _transform(chunk, encoding, callback) {
        const decrypted = this.decipher.update(chunk, 'hex', 'utf8');
        this.push(decrypted);
        callback();
    }

    _flush(callback) {
        const final = this.decipher.final('utf8');
        this.push(final);
        callback();
    }
}

// 파일 압축 및 암호화
function compressAndEncrypt(inputFile, outputFile, password) {
    const readStream = fs.createReadStream(inputFile);
    const writeStream = fs.createWriteStream(outputFile);
    const gzip = zlib.createGzip();
    const encrypt = new EncryptionTransform(password);

    readStream
        .pipe(gzip)
        .pipe(encrypt)
        .pipe(writeStream);

    return new Promise((resolve, reject) => {
        writeStream.on('finish', resolve);
        writeStream.on('error', reject);
    });
}

// 파일 복호화 및 압축 해제
function decryptAndDecompress(inputFile, outputFile, password) {
    const readStream = fs.createReadStream(inputFile);
    const writeStream = fs.createWriteStream(outputFile);
    const gunzip = zlib.createGunzip();
    const decrypt = new DecryptionTransform(password);

    readStream
        .pipe(decrypt)
        .pipe(gunzip)
        .pipe(writeStream);

    return new Promise((resolve, reject) => {
        writeStream.on('finish', resolve);
        writeStream.on('error', reject);
    });
}

// 사용 예시
async function processFile() {
    const password = 'my-secret-password';
    
    try {
        // 압축 및 암호화
        await compressAndEncrypt('input.txt', 'compressed-encrypted.bin', password);
        console.log('파일 압축 및 암호화 완료');
        
        // 복호화 및 압축 해제
        await decryptAndDecompress('compressed-encrypted.bin', 'output.txt', password);
        console.log('파일 복호화 및 압축 해제 완료');
    } catch (error) {
        console.error('파일 처리 오류:', error);
    }
}

processFile();
```

## 운영 팁

### 성능 최적화

#### 스트림 성능 최적화 기법
```javascript
// 1. 적절한 청크 크기 설정
const fs = require('fs');

// 대용량 파일 처리 시 큰 청크 크기 사용
const readStream = fs.createReadStream('large-file.txt', {
    highWaterMark: 1024 * 1024, // 1MB 청크
    encoding: 'utf8'
});

// 2. 백프레셔 처리
class BackpressureHandler {
    constructor() {
        this.isPaused = false;
    }

    handleBackpressure(stream) {
        stream.on('data', (chunk) => {
            // 데이터 처리 속도가 느려지면 일시 중지
            if (this.isPaused) {
                stream.pause();
            }
            
            // 데이터 처리
            this.processChunk(chunk);
        });
    }

    processChunk(chunk) {
        // 무거운 처리 작업 시뮬레이션
        setTimeout(() => {
            console.log('청크 처리 완료:', chunk.length);
            
            // 처리 완료 후 재개
            if (this.isPaused) {
                this.isPaused = false;
                // 스트림 재개 로직
            }
        }, 100);
    }
}

// 3. 메모리 사용량 모니터링
class StreamMonitor {
    constructor() {
        this.stats = {
            bytesProcessed: 0,
            chunksProcessed: 0,
            startTime: Date.now()
        };
    }

    monitorStream(stream) {
        stream.on('data', (chunk) => {
            this.stats.bytesProcessed += chunk.length;
            this.stats.chunksProcessed++;
        });

        stream.on('end', () => {
            const duration = Date.now() - this.stats.startTime;
            const throughput = this.stats.bytesProcessed / duration * 1000; // bytes/sec
            
            console.log('스트림 처리 통계:', {
                bytesProcessed: this.stats.bytesProcessed,
                chunksProcessed: this.stats.chunksProcessed,
                duration: `${duration}ms`,
                throughput: `${(throughput / 1024 / 1024).toFixed(2)}MB/s`
            });
        });
    }
}

// 사용 예시
const monitor = new StreamMonitor();
const readStream = fs.createReadStream('large-file.txt');

monitor.monitorStream(readStream);
readStream.pipe(fs.createWriteStream('output.txt'));
```

### 오류 처리

#### 스트림 오류 처리 패턴
```javascript
// 1. 종합적인 오류 처리
function createRobustStreamPipeline() {
    const readStream = fs.createReadStream('input.txt');
    const writeStream = fs.createWriteStream('output.txt');
    
    // 오류 처리 함수
    function handleError(error, streamName) {
        console.error(`${streamName} 오류:`, error.message);
        
        // 스트림 정리
        readStream.destroy();
        writeStream.destroy();
        
        // 오류 복구 로직
        setTimeout(() => {
            console.log('스트림 재시작 시도...');
            createRobustStreamPipeline();
        }, 1000);
    }
    
    // 각 스트림에 오류 리스너 추가
    readStream.on('error', (error) => handleError(error, '읽기 스트림'));
    writeStream.on('error', (error) => handleError(error, '쓰기 스트림'));
    
    // 파이프라인 연결
    readStream.pipe(writeStream);
    
    // 완료 이벤트
    writeStream.on('finish', () => {
        console.log('스트림 처리 완료');
    });
}

// 2. 재시도 로직이 포함된 스트림
class RetryStream extends Transform {
    constructor(options = {}) {
        super(options);
        this.maxRetries = options.maxRetries || 3;
        this.retryDelay = options.retryDelay || 1000;
        this.retryCount = 0;
    }

    _transform(chunk, encoding, callback) {
        this.processChunk(chunk, encoding, callback);
    }

    processChunk(chunk, encoding, callback) {
        try {
            // 데이터 처리 로직
            const processed = this.processData(chunk);
            this.push(processed);
            callback();
        } catch (error) {
            if (this.retryCount < this.maxRetries) {
                this.retryCount++;
                console.log(`재시도 ${this.retryCount}/${this.maxRetries}`);
                
                setTimeout(() => {
                    this.processChunk(chunk, encoding, callback);
                }, this.retryDelay);
            } else {
                callback(error);
            }
        }
    }

    processData(chunk) {
        // 실제 데이터 처리 로직
        return chunk.toString().toUpperCase();
    }
}

// 3. 스트림 상태 모니터링
class StreamHealthMonitor {
    constructor() {
        this.health = {
            isHealthy: true,
            lastActivity: Date.now(),
            errorCount: 0,
            successCount: 0
        };
    }

    monitorStream(stream) {
        stream.on('data', () => {
            this.health.lastActivity = Date.now();
            this.health.successCount++;
        });

        stream.on('error', (error) => {
            this.health.errorCount++;
            this.health.isHealthy = false;
            console.error('스트림 오류:', error.message);
        });

        stream.on('end', () => {
            this.health.isHealthy = true;
        });

        // 주기적 상태 확인
        setInterval(() => {
            const timeSinceLastActivity = Date.now() - this.health.lastActivity;
            
            if (timeSinceLastActivity > 30000) { // 30초
                console.warn('스트림이 30초간 비활성 상태입니다.');
            }
            
            console.log('스트림 상태:', this.health);
        }, 10000);
    }
}
```

## 참고

### 스트림 이벤트 종류

#### Readable Stream 이벤트
```javascript
const readStream = fs.createReadStream('file.txt');

// 데이터 이벤트: 새로운 데이터가 사용 가능할 때
readStream.on('data', (chunk) => {
    console.log('데이터 수신:', chunk.length, '바이트');
});

// end 이벤트: 더 이상 읽을 데이터가 없을 때
readStream.on('end', () => {
    console.log('읽기 완료');
});

// error 이벤트: 오류 발생 시
readStream.on('error', (error) => {
    console.error('읽기 오류:', error);
});

// close 이벤트: 스트림이 닫힐 때
readStream.on('close', () => {
    console.log('스트림 닫힘');
});

// readable 이벤트: 읽을 데이터가 있을 때
readStream.on('readable', () => {
    let chunk;
    while ((chunk = readStream.read()) !== null) {
        console.log('읽기 가능한 데이터:', chunk);
    }
});
```

#### Writable Stream 이벤트
```javascript
const writeStream = fs.createWriteStream('output.txt');

// drain 이벤트: 버퍼가 비워졌을 때
writeStream.on('drain', () => {
    console.log('버퍼가 비워짐, 더 많은 데이터를 쓸 수 있음');
});

// finish 이벤트: 모든 데이터가 쓰여졌을 때
writeStream.on('finish', () => {
    console.log('쓰기 완료');
});

// error 이벤트: 오류 발생 시
writeStream.on('error', (error) => {
    console.error('쓰기 오류:', error);
});

// close 이벤트: 스트림이 닫힐 때
writeStream.on('close', () => {
    console.log('스트림 닫힘');
});
```

### 스트림 모드

#### Object Mode vs Buffer Mode
```javascript
const { Readable, Writable } = require('stream');

// Buffer Mode (기본값)
class BufferStream extends Readable {
    constructor() {
        super();
        this.counter = 0;
    }

    _read() {
        if (this.counter >= 5) {
            this.push(null);
            return;
        }
        
        // Buffer로 데이터 전송
        this.push(Buffer.from(`데이터 ${this.counter++}\n`));
    }
}

// Object Mode
class ObjectStream extends Readable {
    constructor() {
        super({ objectMode: true });
        this.counter = 0;
    }

    _read() {
        if (this.counter >= 5) {
            this.push(null);
            return;
        }
        
        // 객체로 데이터 전송
        this.push({ id: this.counter, data: `데이터 ${this.counter++}` });
    }
}

// 사용 예시
const bufferStream = new BufferStream();
const objectStream = new ObjectStream();

bufferStream.on('data', (chunk) => {
    console.log('Buffer 모드:', chunk.toString());
});

objectStream.on('data', (obj) => {
    console.log('Object 모드:', obj);
});
```

### 결론
스트림은 Node.js에서 대용량 데이터를 효율적으로 처리하는 핵심 기술입니다.
적절한 스트림 사용으로 메모리 사용량을 최소화하고 성능을 향상시킬 수 있습니다.
백프레셔를 이해하고 처리하여 안정적인 스트림 파이프라인을 구축해야 합니다.
스트림의 다양한 유형과 이벤트를 활용하여 복잡한 데이터 처리 로직을 구현할 수 있습니다.
오류 처리와 모니터링을 통해 안정적인 스트림 애플리케이션을 개발해야 합니다.
