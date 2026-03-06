---
title: Node.js 에러 처리 전략 가이드
tags: [nodejs, error-handling, express, nestjs, middleware, global-handler, custom-error]
updated: 2026-03-01
---

# Node.js 에러 처리 전략

## 개요

Node.js에서 에러 처리는 **애플리케이션의 안정성**을 결정하는 핵심이다. 잡히지 않은 에러는 프로세스를 죽이고, 잘못된 에러 처리는 보안 취약점을 만든다.

```
에러 처리의 목표:
  1. 프로세스가 죽지 않는다 (안정성)
  2. 클라이언트에게 적절한 응답을 준다 (UX)
  3. 디버깅 가능한 로그를 남긴다 (운영)
  4. 민감한 정보를 노출하지 않는다 (보안)
```

## 핵심

### 1. 에러 분류

| 유형 | 예시 | 복구 가능 | 처리 방법 |
|------|------|---------|---------|
| **Operational** (운영 에러) | DB 연결 실패, 타임아웃, 400 에러 | ✅ | try/catch, 재시도 |
| **Programmer** (프로그래밍 에러) | TypeError, null 참조, 잘못된 인자 | ❌ | 코드 수정 |

```javascript
// Operational Error: 예상 가능, 복구 가능
try {
    await db.query('SELECT * FROM users');
} catch (error) {
    if (error.code === 'ECONNREFUSED') {
        // DB 연결 실패 → 재시도 또는 폴백
        return getCachedData();
    }
    throw error;
}

// Programmer Error: 예상 불가, 코드 수정 필요
const user = null;
user.name;  // TypeError: Cannot read property 'name' of null
// → 이건 catch로 처리할 게 아니라 코드를 고쳐야 함
```

### 2. 커스텀 에러 클래스

```javascript
// 기본 에러 클래스
class AppError extends Error {
    constructor(message, statusCode, errorCode) {
        super(message);
        this.name = this.constructor.name;
        this.statusCode = statusCode;
        this.errorCode = errorCode;
        this.isOperational = true;
        Error.captureStackTrace(this, this.constructor);
    }
}

// 구체적 에러 클래스
class NotFoundError extends AppError {
    constructor(resource, id) {
        super(`${resource} with id ${id} not found`, 404, 'NOT_FOUND');
    }
}

class ValidationError extends AppError {
    constructor(errors) {
        super('Validation failed', 400, 'VALIDATION_ERROR');
        this.errors = errors;
    }
}

class UnauthorizedError extends AppError {
    constructor(message = 'Authentication required') {
        super(message, 401, 'UNAUTHORIZED');
    }
}

class ForbiddenError extends AppError {
    constructor(message = 'Access denied') {
        super(message, 403, 'FORBIDDEN');
    }
}

class ConflictError extends AppError {
    constructor(message) {
        super(message, 409, 'CONFLICT');
    }
}
```

### 3. Express 에러 처리

#### 라우트 에러 처리

```javascript
// ❌ 에러가 삼켜짐
app.get('/users/:id', async (req, res) => {
    const user = await userService.findById(req.params.id);
    res.json(user);  // 에러 발생 시 응답 없이 행(hang)
});

// ✅ try/catch로 감싸기
app.get('/users/:id', async (req, res, next) => {
    try {
        const user = await userService.findById(req.params.id);
        if (!user) throw new NotFoundError('User', req.params.id);
        res.json(user);
    } catch (error) {
        next(error);  // 에러 미들웨어로 전달
    }
});

// ✅✅ 래퍼 함수로 자동화
const asyncHandler = (fn) => (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
};

app.get('/users/:id', asyncHandler(async (req, res) => {
    const user = await userService.findById(req.params.id);
    if (!user) throw new NotFoundError('User', req.params.id);
    res.json(user);
}));
```

#### 글로벌 에러 미들웨어

```javascript
// 4개 파라미터 → Express가 에러 미들웨어로 인식
app.use((err, req, res, next) => {
    // 운영 에러 (예상된 에러)
    if (err.isOperational) {
        return res.status(err.statusCode).json({
            status: 'error',
            code: err.errorCode,
            message: err.message,
            ...(err.errors && { errors: err.errors }),
        });
    }

    // 프로그래밍 에러 (예상치 못한 에러)
    console.error('UNEXPECTED ERROR:', err);
    res.status(500).json({
        status: 'error',
        code: 'INTERNAL_ERROR',
        message: 'Something went wrong',
        // ❌ 프로덕션에서 스택 트레이스 노출 금지
        ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
    });
});
```

#### 404 핸들러

```javascript
// 모든 라우트 이후, 에러 미들웨어 이전
app.use((req, res) => {
    res.status(404).json({
        status: 'error',
        code: 'NOT_FOUND',
        message: `Route ${req.method} ${req.path} not found`,
    });
});
```

### 4. NestJS 에러 처리

```typescript
// 글로벌 예외 필터
@Catch()
export class GlobalExceptionFilter implements ExceptionFilter {
    private readonly logger = new Logger(GlobalExceptionFilter.name);

    catch(exception: unknown, host: ArgumentsHost) {
        const ctx = host.switchToHttp();
        const response = ctx.getResponse();
        const request = ctx.getRequest();

        let status = 500;
        let message = 'Internal server error';
        let code = 'INTERNAL_ERROR';

        if (exception instanceof HttpException) {
            status = exception.getStatus();
            const res = exception.getResponse();
            message = typeof res === 'string' ? res : (res as any).message;
            code = (res as any).code || 'HTTP_ERROR';
        }

        // 500 에러만 상세 로그
        if (status >= 500) {
            this.logger.error(`${request.method} ${request.url}`, exception);
        }

        response.status(status).json({
            status: 'error',
            code,
            message,
            timestamp: new Date().toISOString(),
            path: request.url,
        });
    }
}

// main.ts에서 등록
app.useGlobalFilters(new GlobalExceptionFilter());
```

```typescript
// NestJS 내장 예외
throw new NotFoundException('User not found');
throw new BadRequestException('Invalid input');
throw new UnauthorizedException('Token expired');
throw new ForbiddenException('Access denied');
throw new ConflictException('Email already exists');
```

### 5. 프로세스 레벨 에러

```javascript
// 잡히지 않은 Promise 거부
process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection:', reason);
    // 로그 기록 후 프로세스 종료 (PM2가 재시작)
    process.exit(1);
});

// 잡히지 않은 예외
process.on('uncaughtException', (error) => {
    console.error('Uncaught Exception:', error);
    // 진행 중인 요청 완료 후 종료 (graceful shutdown)
    server.close(() => {
        process.exit(1);
    });
    // 10초 내 종료 안 되면 강제 종료
    setTimeout(() => process.exit(1), 10000);
});

// SIGTERM (컨테이너 종료 시그널)
process.on('SIGTERM', () => {
    console.log('SIGTERM received. Graceful shutdown...');
    server.close(() => {
        db.disconnect();
        process.exit(0);
    });
});
```

### 6. 에러 응답 표준 형식

```json
{
    "status": "error",
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "errors": [
        {
            "field": "email",
            "message": "Invalid email format"
        },
        {
            "field": "age",
            "message": "Must be at least 18"
        }
    ],
    "timestamp": "2026-03-01T10:15:30.000Z",
    "path": "/api/users",
    "requestId": "req-abc123"
}
```

```javascript
// 성공 응답도 일관된 형식
{
    "status": "success",
    "data": { ... },
    "meta": {
        "page": 1,
        "total": 100
    }
}
```

### 7. 에러 로깅

```javascript
// 구조화된 에러 로그
const logger = require('pino')();

app.use((err, req, res, next) => {
    logger.error({
        err: {
            message: err.message,
            code: err.errorCode,
            stack: err.stack,
        },
        request: {
            method: req.method,
            url: req.url,
            headers: {
                'user-agent': req.headers['user-agent'],
            },
            body: req.body,
            userId: req.user?.id,
        },
        responseTime: Date.now() - req.startTime,
    }, 'Request error');

    // ... 응답 처리
});
```

### 8. 외부 서비스 에러 처리

```javascript
// 재시도 + 서킷 브레이커 패턴
class ExternalServiceClient {
    constructor(baseUrl, options = {}) {
        this.baseUrl = baseUrl;
        this.maxRetries = options.maxRetries || 3;
        this.timeout = options.timeout || 5000;
    }

    async request(path, options = {}) {
        let lastError;

        for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(
                    () => controller.abort(),
                    this.timeout
                );

                const response = await fetch(`${this.baseUrl}${path}`, {
                    ...options,
                    signal: controller.signal,
                });
                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new AppError(
                        `External service error: ${response.status}`,
                        502,
                        'EXTERNAL_SERVICE_ERROR'
                    );
                }
                return response.json();
            } catch (error) {
                lastError = error;
                if (attempt < this.maxRetries) {
                    await new Promise(r =>
                        setTimeout(r, 1000 * Math.pow(2, attempt - 1))
                    );
                }
            }
        }
        throw lastError;
    }
}
```

## 체크리스트

| 항목 | 설명 | 필수 |
|------|------|------|
| 커스텀 에러 클래스 | Operational vs Programmer 구분 | ✅ |
| 글로벌 에러 핸들러 | 모든 에러를 한 곳에서 처리 | ✅ |
| asyncHandler 래퍼 | async 라우트 에러 자동 전파 | ✅ |
| 프로세스 에러 핸들링 | unhandledRejection, uncaughtException | ✅ |
| 에러 응답 표준화 | 일관된 JSON 형식 | ✅ |
| Graceful Shutdown | SIGTERM 처리, 진행 중 요청 완료 | ✅ |
| 프로덕션 에러 숨기기 | 스택 트레이스, 내부 정보 노출 금지 | ✅ |
| 구조화된 로깅 | requestId, userId 포함 | ⭐ |

## 참고

- [Express Error Handling](https://expressjs.com/en/guide/error-handling.html)
- [NestJS Exception Filters](https://docs.nestjs.com/exception-filters)
- [Node.js Best Practices](https://github.com/goldbergyoni/nodebestpractices)
- [로깅 전략](로깅/로깅_전략.md) — 구조화된 로깅
- [보안 모범사례](보안/Node.js_보안_모범사례.md) — 에러를 통한 정보 노출 방지
