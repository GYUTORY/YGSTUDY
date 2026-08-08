---
title: API Input Validation
tags: [security, api, backend]
updated: 2026-04-07
---

# API 입력값 검증

API 서버에서 가장 많이 터지는 문제 중 하나가 입력값 검증이다. 프론트엔드에서 검증했으니 괜찮겠지 하고 넘어가면 Postman이나 curl로 직접 호출하는 순간 바로 뚫린다.

입력값 검증은 반드시 서버 사이드에서 해야 한다. 프론트엔드 검증은 UX를 위한 것이지, 보안을 위한 것이 아니다.

---

## class-validator로 요청 검증

NestJS 기준으로 `class-validator` 데코레이터를 사용해서 DTO에 검증 규칙을 건다.

```typescript
import { IsNotEmpty, Min, Max, MaxLength, Matches } from 'class-validator';

export class CreateOrderRequest {
  @IsNotEmpty({ message: '상품 ID는 필수다' })
  productId: string;

  @Min(1, { message: '수량은 1 이상이어야 한다' })
  @Max(9999, { message: '수량은 9999를 넘을 수 없다' })
  quantity: number;

  @MaxLength(200, { message: '배송 메모는 200자 이내' })
  deliveryNote?: string;

  @Matches(/^\d{5}$/, { message: '우편번호 형식이 아니다' })
  zipCode?: string;
}
```

NestJS에서는 `ValidationPipe`를 전역으로 등록해야 검증이 동작한다. 빠뜨리면 DTO 어노테이션이 아무런 효과가 없다.

```typescript
// main.ts
import { ValidationPipe } from '@nestjs/common';

app.useGlobalPipes(new ValidationPipe({
  whitelist: true,       // DTO에 없는 필드를 자동으로 제거
  forbidNonWhitelisted: true, // DTO에 없는 필드가 오면 400 반환
}));
```

### 검증 실패 시 응답 처리

기본 에러 응답은 클라이언트가 파싱하기 어렵다. `@RestControllerAdvice`로 통일된 형식을 만든다.

```typescript
// NestJS — ValidationPipe의 exceptionFactory로 응답 형식을 통일한다
import { ValidationPipe, BadRequestException } from '@nestjs/common';

app.useGlobalPipes(new ValidationPipe({
  whitelist: true,
  forbidNonWhitelisted: true,
  exceptionFactory: (errors) => {
    const messages = errors.map(e => ({
      field: e.property,
      message: Object.values(e.constraints ?? {}).join(', '),
    }));
    return new BadRequestException({ code: 'VALIDATION_ERROR', errors: messages });
  },
}));
```

주의할 점: 검증 에러 메시지에 내부 구현 정보를 노출하면 안 된다. `"DB column 'product_id' cannot be null"` 같은 메시지가 나가는 경우를 봤다. 메시지는 항상 사용자 관점에서 작성한다.

---

## 중첩 객체 검증 누락

가장 흔하게 놓치는 부분이다. DTO 안에 다른 객체가 있을 때 `@Valid`를 안 걸면 내부 객체의 검증이 무시된다.

```typescript
import { IsNotEmpty, IsPositive, ValidateNested, ArrayMinSize } from 'class-validator';
import { Type } from 'class-transformer';

export class AddressDto {
  @IsNotEmpty()
  street: string;

  @IsNotEmpty()
  city: string;
}

export class OrderItemDto {
  @IsNotEmpty()
  productId: string;

  @IsPositive()
  quantity: number;
}

export class CreateOrderRequest {
  @ValidateNested()  // 이게 없으면 address 내부 필드 검증이 동작하지 않는다
  @Type(() => AddressDto)
  address: AddressDto;

  @ValidateNested({ each: true })  // each: true로 리스트 내 각 원소를 검증한다
  @ArrayMinSize(1, { message: '주문 항목은 최소 1개' })
  @Type(() => OrderItemDto)
  items: OrderItemDto[];
}
```

List 안의 객체에도 `@Valid`가 필요하다. `List<OrderItemDto>` 자체에 `@Valid`를 걸어야 리스트 내 각 원소에 대해 검증이 동작한다.

실무에서 이걸 놓치면 빈 `address`나 `quantity: -1`인 주문이 DB에 들어간다. 데이터 정합성이 깨지고 나중에 원인을 추적하기 어렵다.

---

## JSON Schema 기반 검증

Bean Validation이 커버하지 못하는 복잡한 구조 검증이 필요할 때 JSON Schema를 쓴다. 특히 외부 시스템에서 들어오는 webhook이나, 스키마가 동적으로 바뀌는 경우에 유용하다.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["eventType", "payload"],
  "properties": {
    "eventType": {
      "type": "string",
      "enum": ["ORDER_CREATED", "ORDER_CANCELLED", "PAYMENT_COMPLETED"]
    },
    "payload": {
      "type": "object",
      "required": ["orderId"],
      "properties": {
        "orderId": {
          "type": "string",
          "minLength": 1,
          "maxLength": 50
        },
        "amount": {
          "type": "number",
          "minimum": 0,
          "exclusiveMaximum": 100000000
        }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

`additionalProperties: false`를 빼먹으면 스키마에 정의되지 않은 필드가 그대로 통과한다. 의도하지 않은 필드가 들어와서 로직에 영향을 주는 경우가 있다.

TypeScript에서 JSON Schema 검증은 `ajv` 라이브러리를 많이 쓴다.

```typescript
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

const ajv = new Ajv({ allErrors: true });
addFormats(ajv);

const validate = ajv.compile(schema); // schema는 JSON Schema 객체

const valid = validate(payload);
if (!valid) {
  throw new InvalidPayloadException(ajv.errorsText(validate.errors));
}
```

---

## 페이로드 크기 제한

요청 본문 크기를 제한하지 않으면 수 GB짜리 JSON을 보내는 것만으로 서버 메모리를 잡아먹을 수 있다.

### Express / NestJS 설정

```typescript
// main.ts — NestJS + Express
import { json, urlencoded } from 'express';

// JSON 요청 본문 크기 제한 (1MB)
app.use(json({ limit: '1mb' }));
// URL-encoded 폼 크기 제한
app.use(urlencoded({ limit: '1mb', extended: true }));
```

파일 업로드(multipart)는 `multer`의 `limits` 옵션으로 제한한다.

```typescript
import multer from 'multer';

const upload = multer({
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB per file
    files: 5,                    // 동시 업로드 파일 수
    fieldSize: 1 * 1024 * 1024, // 비파일 필드 크기 1MB
  },
});
```

`Content-Length` 헤더를 보내지 않는 chunked 요청은 `express.json()`이 읽으면서 실제 바이트를 누적한다. `limit` 옵션이 누적 바이트 기준으로 동작하므로 별도 래퍼 없이 처리된다.

---

## 타입 강제 변환 문제

JSON을 TypeScript 객체로 역직렬화할 때 암묵적으로 타입이 변환되는 경우가 있다. 이게 보안 문제로 이어진다.

### 숫자 → 문자열 변환

```json
{
  "userId": 12345
}
```

NestJS `ValidationPipe`에서 `transform: true`가 켜져 있으면 `userId`가 `string` 타입 필드로 선언돼 있어도 `12345`를 `"12345"`로 변환한다. 의도한 동작이 아닐 수 있다.

```typescript
// 암묵적 변환을 끄고 타입 불일치를 에러로 처리
app.useGlobalPipes(new ValidationPipe({
  transform: false,              // 암묵적 타입 변환 비활성화
  forbidNonWhitelisted: true,   // 알 수 없는 필드 차단
  whitelist: true,
}));
```

### 배열에 단일 값이 오는 경우

```json
{
  "tags": "single-tag"
}
```

`transform: true`가 켜져 있고 필드가 `string[]`로 선언돼 있으면 문자열 하나가 배열로 변환되기도 한다. `IsArray()` 데코레이터와 함께 타입을 명시적으로 검증하면 배열이 아닌 값을 차단할 수 있다.

```typescript
import { IsArray, IsString } from 'class-validator';

export class CreateTagRequest {
  @IsArray()
  @IsString({ each: true })
  tags: string[]; // "single-tag"가 오면 IsArray() 검증에서 실패
}
```

### 알 수 없는 필드 처리

요청에 DTO에 정의되지 않은 필드가 오면 기본적으로 무시된다. Mass Assignment 공격의 원인이 된다.

```typescript
// ValidationPipe의 whitelist + forbidNonWhitelisted로 알 수 없는 필드를 차단
app.useGlobalPipes(new ValidationPipe({
  whitelist: true,              // DTO에 없는 필드를 자동 제거
  forbidNonWhitelisted: true,  // 없는 필드가 오면 400 반환 (단순 제거 대신 거부)
}));
```

실제로 겪은 케이스: `role` 필드가 DTO에 없는데 `{"name": "test", "role": "ADMIN"}`을 보내면 무시된다. 하지만 나중에 누군가 DTO에 `role` 필드를 추가하는 순간 외부에서 권한을 조작할 수 있게 된다. `forbidNonWhitelisted: true`를 켜두면 알 수 없는 필드가 오는 즉시 400으로 거부된다.

---

## Content-Type 검증

`Content-Type` 헤더를 확인하지 않으면 예상치 못한 형식의 데이터가 들어온다.

### Express / NestJS에서의 Content-Type 처리

`express.json()` 미들웨어는 기본적으로 `Content-Type: application/json`만 처리한다. NestJS에서는 라우트에 `@Header()` 데코레이터를 붙이거나, 미들웨어로 제한한다.

```typescript
// NestJS — 라우트 수준에서 Content-Type 제한
import { Controller, Post, Body, Headers, UnsupportedMediaTypeException } from '@nestjs/common';

@Post('orders')
async createOrder(
  @Body() dto: CreateOrderRequest,
  @Headers('content-type') contentType: string,
) {
  if (!contentType?.includes('application/json')) {
    throw new UnsupportedMediaTypeException();
  }
  return this.orderService.create(dto);
}
```

### Content-Type 불일치 공격

`Content-Type: text/plain`으로 보내면서 본문은 JSON인 경우가 있다. 일부 프레임워크는 Content-Type을 무시하고 본문을 파싱하려 한다.

```typescript
// Express 미들웨어로 Content-Type 검증
import { Request, Response, NextFunction } from 'express';

const ALLOWED_CONTENT_TYPES = new Set(['application/json', 'multipart/form-data']);

function contentTypeGuard(req: Request, res: Response, next: NextFunction) {
  if (['POST', 'PUT', 'PATCH'].includes(req.method)) {
    const contentType = req.headers['content-type'];
    if (!contentType) {
      return res.status(415).json({ error: 'Content-Type is required' });
    }
    // Content-Type에서 charset 등의 파라미터를 제거하고 비교
    const mediaType = contentType.split(';')[0].trim().toLowerCase();
    if (!ALLOWED_CONTENT_TYPES.has(mediaType)) {
      return res.status(415).json({ error: 'Unsupported Media Type' });
    }
  }
  next();
}

app.use(contentTypeGuard);
```

---

## 파일 업로드 검증

파일 업로드는 검증할 게 많고, 하나라도 빠지면 심각한 보안 문제가 된다.

### 확장자만 검증하면 안 된다

확장자를 `.webp`로 바꿔서 `.jsp` 파일을 올리는 건 기본적인 공격이다. 파일의 실제 내용(매직 바이트)을 확인해야 한다.

```typescript
import { BadRequestException } from '@nestjs/common';
import { Express } from 'express';
import * as path from 'path';

// 허용할 파일 타입의 매직 바이트
const MAGIC_BYTES: Record<string, number[]> = {
  'image/jpeg': [0xff, 0xd8, 0xff],
  'image/png':  [0x89, 0x50, 0x4e, 0x47],
  'application/pdf': [0x25, 0x50, 0x44, 0x46],
};

const ALLOWED_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'pdf']);

export function validateUploadedFile(file: Express.Multer.File): void {
  // 1. 파일 크기 검증 (multer limits로도 가능하지만 명시적으로 한 번 더)
  if (file.size > 10 * 1024 * 1024) {
    throw new BadRequestException('파일 크기가 10MB를 초과한다');
  }

  // 2. 파일명 검증 — 경로 탐색 문자 차단
  const originalName = file.originalname;
  if (!originalName || originalName.includes('..') || originalName.includes('/') || originalName.includes('\\')) {
    throw new BadRequestException('잘못된 파일명이다');
  }

  // 3. 확장자 검증
  const ext = path.extname(originalName).replace('.', '').toLowerCase();
  if (!ALLOWED_EXTENSIONS.has(ext)) {
    throw new BadRequestException('허용되지 않는 파일 형식이다');
  }

  // 4. 매직 바이트 검증 — 실제 파일 내용 확인
  const expected = MAGIC_BYTES[file.mimetype];
  if (!expected) {
    throw new BadRequestException('지원하지 않는 Content-Type이다');
  }
  const buf = file.buffer; // memoryStorage 사용 시 buffer에서 읽는다
  if (!expected.every((byte, i) => buf[i] === byte)) {
    throw new BadRequestException('파일 내용이 확장자와 일치하지 않는다');
  }
}
```

### 파일명 처리

업로드된 파일의 원본 파일명을 그대로 저장하면 안 된다. 파일명에 특수문자나 경로 탐색 문자가 포함될 수 있다.

```typescript
import * as path from 'path';
import { randomUUID } from 'crypto';

function generateSafeFilename(originalFilename: string): string {
  const ext = path.extname(originalFilename).toLowerCase(); // ".webp"
  // UUID로 새 파일명을 생성하고, 확장자만 유지한다
  return `${randomUUID()}${ext}`;
}
```

저장 경로도 주의해야 한다. 웹 서버의 document root 아래에 저장하면 업로드한 파일이 직접 실행될 수 있다. 별도의 스토리지 경로를 사용하거나 S3 같은 외부 스토리지를 쓴다.

---

## 경로 파라미터와 쿼리 파라미터 검증

JSON 요청 본문만 검증하고, URL의 경로 파라미터나 쿼리 파라미터 검증은 빠뜨리는 경우가 많다.

### 경로 파라미터

```typescript
import { Param, ParseUUIDPipe, ParseIntPipe } from '@nestjs/common';

@Get('users/:userId/orders/:orderId')
@UseGuards(JwtAuthGuard)
async getOrder(
  @Param('userId', new ParseUUIDPipe()) userId: string,  // UUID 형식 자동 검증
  @Param('orderId', new ParseIntPipe()) orderId: number, // 정수 형식 자동 검증
) {
  return this.orderService.getOrder(userId, orderId);
}
```

`ParseUUIDPipe`는 UUID 형식이 아니면 400을 반환한다. 커스텀 패턴이 필요하면 `PipeTransform`을 구현한다.

### 쿼리 파라미터

페이징 파라미터를 검증하지 않으면 `page=0&size=1000000`으로 전체 데이터를 한 번에 가져갈 수 있다.

```typescript
import { Query, BadRequestException } from '@nestjs/common';
import { IsInt, Min, Max } from 'class-validator';
import { Type } from 'class-transformer';

export class PaginationQuery {
  @Type(() => Number)
  @IsInt() @Min(0)
  page: number = 0;

  @Type(() => Number)
  @IsInt() @Min(1) @Max(100)
  size: number = 20;

  sort: string = 'createdAt';
}

@Get('orders')
async listOrders(@Query() query: PaginationQuery) {
  // sort 파라미터는 허용된 값만 받는다
  const allowedSortFields = new Set(['createdAt', 'amount', 'status']);
  if (!allowedSortFields.has(query.sort)) {
    throw new BadRequestException('허용되지 않는 정렬 기준이다');
  }
  return this.orderService.list(query);
}
```

`sort` 파라미터를 그대로 SQL에 넣으면 SQL Injection이 된다. 화이트리스트로 검증해야 한다.

---

## 문자열 입력값의 함정

문자열 검증에서 자주 놓치는 부분들이 있다.

### 공백 문자 처리

`@NotBlank`는 null과 빈 문자열, 공백만 있는 문자열을 잡아준다. 하지만 탭이나 줄바꿈 같은 제어 문자는 통과한다.

```typescript
import { IsNotEmpty, Matches } from 'class-validator';

// 이름 필드에 제어 문자가 들어오는 걸 막으려면 패턴을 건다
@IsNotEmpty()
@Matches(/^[\p{L}\p{N}\s]{1,50}$/u, { message: '허용되지 않는 문자가 포함되어 있다' })
name: string;
```

### Unicode 정규화

같은 글자처럼 보이지만 다른 유니코드 코드포인트인 경우가 있다. `"café"`가 NFC와 NFD로 다르게 인코딩될 수 있다. 검색이나 중복 체크에서 문제를 일으킨다.

```typescript
// 입력값을 NFC로 정규화한다
const normalized = input.normalize('NFC');
```

### HTML/Script 태그

입력값에 `<script>alert(1)</script>` 같은 걸 넣는 건 기본적인 XSS 시도다. 저장 시점에 이스케이프하거나, 출력 시점에 이스케이프한다. 두 곳 다 하면 이중 이스케이프 문제가 생기므로 한 곳에서만 처리한다.

보통은 출력 시점에 이스케이프하는 것을 권장한다. 저장 시점에 이스케이프하면 원본 데이터가 변형되어 검색이나 다른 용도로 사용할 때 문제가 생긴다.

---

## 검증 순서

입력값 검증은 순서가 있다. 잘못된 순서로 검증하면 의미 없는 에러 메시지가 나가거나, 비즈니스 로직에서 예외가 터진다.

1. **Content-Type 확인** — 잘못된 형식의 요청은 파싱하기 전에 거부한다
2. **페이로드 크기 확인** — 파싱 전에 크기를 체크해서 메모리 낭비를 방지한다
3. **구문 검증(파싱)** — JSON이 올바른 형식인지 확인한다
4. **구조 검증** — 필수 필드 존재 여부, 타입, 길이 등을 확인한다
5. **비즈니스 규칙 검증** — 존재하는 상품인지, 재고가 있는지 등 도메인 로직 검증

Spring에서는 1~4단계가 프레임워크와 Bean Validation으로 처리되고, 5단계는 서비스 레이어에서 처리한다. 서비스 레이어 검증을 컨트롤러에 넣으면 코드가 복잡해지고, 다른 진입점(메시지 큐, 배치 등)에서 검증이 누락된다.

---

## 실무에서 자주 터지는 상황 정리

**빈 배열 vs null**: `"items": []`와 `"items": null`과 `items` 필드가 아예 없는 경우를 구분해야 한다. `@NotNull`은 null만 잡고, `@Size(min=1)`은 빈 배열을 잡는다. 필드가 아예 없으면 null로 들어온다.

**숫자 범위**: `int` 타입의 `quantity` 필드에 `2147483648`(Integer.MAX_VALUE + 1)을 보내면 Jackson에서 파싱 에러가 난다. Long으로 받아야 하는데 int로 받고 있다면, 큰 숫자가 왔을 때 오버플로우가 아니라 파싱 에러가 나는지 확인해야 한다.

**날짜 형식**: `"2026-13-01"`이나 `"2026-02-30"` 같은 잘못된 날짜를 Jackson이 어떻게 처리하는지 확인해야 한다. `lenient` 모드가 켜져 있으면 `2026-13-01`이 `2027-01-01`로 변환된다.

```typescript
import { IsISO8601 } from 'class-validator';

// ISO 8601 날짜 형식만 허용 (lenient 파싱 없음)
@IsISO8601({ strict: true }, { message: '날짜 형식이 아니다 (예: 2026-04-07)' })
orderDate: string;
```

**enum 값**: DTO에서 String으로 받아서 수동으로 변환하는 것보다 enum 타입으로 받는 게 낫다. 잘못된 값이 오면 Jackson이 자동으로 에러를 발생시킨다. 단, 에러 메시지가 내부 구현(enum 클래스명)을 노출할 수 있으므로 `@JsonCreator`로 커스텀 처리하는 게 좋다.

```typescript
import { IsEnum } from 'class-validator';

enum OrderStatus {
  PENDING = 'PENDING',
  CONFIRMED = 'CONFIRMED',
  SHIPPED = 'SHIPPED',
  DELIVERED = 'DELIVERED',
}

export class UpdateOrderStatusRequest {
  @IsEnum(OrderStatus, { message: (args) => `잘못된 주문 상태: ${args.value}` })
  status: OrderStatus;
}
// 잘못된 값이 오면 class-validator가 자동으로 400을 반환한다
```
