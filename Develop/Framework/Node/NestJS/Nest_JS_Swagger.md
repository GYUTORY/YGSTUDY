---
title: NestJS Swagger로 API 문서 자동화
tags: [nestjs, swagger, openapi, api-docs, dto, node]
updated: 2026-06-07
---

# NestJS Swagger로 API 문서 자동화

API 문서를 사람이 직접 작성하면 코드와 거의 항상 어긋난다. 필드 하나 추가하고 문서를 안 고치는 일이 반복되면, 프론트엔드는 문서를 안 믿고 백엔드 개발자한테 슬랙으로 물어본다. `@nestjs/swagger`는 컨트롤러와 DTO에 붙은 데코레이터, 그리고 타입 정보를 읽어서 OpenAPI 스펙을 런타임에 생성한다. 코드가 곧 문서이기 때문에 어긋날 여지가 줄어든다.

이 문서는 Swagger를 붙이는 기본 설정부터, 실무에서 막히는 지점—DTO 스키마가 비어 나오는 문제, JWT 토큰을 매번 다시 입력해야 하는 문제, 제네릭 응답 래퍼가 스펙에 안 잡히는 문제, 운영 환경에 문서가 노출되는 문제—을 실제로 겪은 순서대로 정리한다. DTO 검증 자체는 [Nest_JS_Validation_Pipe.md](Nest_JS_Validation_Pipe.md)를, 인증 구조는 [Nest_JS_인증_JWT_Passport.md](Nest_JS_인증_JWT_Passport.md)를 참고한다.


## 설치와 기본 셋업

```bash
npm install @nestjs/swagger
```

Express 기반이면 위 패키지 하나로 끝난다. 예전에는 `swagger-ui-express`를 따로 깔아야 했는데, 최근 버전은 `@nestjs/swagger`가 UI를 내장한다. Fastify를 쓰면 `@fastify/swagger`가 필요하지만, 대부분 Express 어댑터를 그대로 쓰니 추가 설치는 신경 안 써도 된다.

문서는 `main.ts`의 bootstrap 단계에서 만든다. `DocumentBuilder`로 메타 정보를 정의하고, `SwaggerModule.createDocument`로 실제 스펙 객체를 만든 뒤, `SwaggerModule.setup`으로 특정 경로에 UI를 붙인다.

```typescript
// main.ts
import { NestFactory } from '@nestjs/core';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  const config = new DocumentBuilder()
    .setTitle('주문 API')
    .setDescription('주문/결제 도메인 REST API')
    .setVersion('1.0')
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('docs', app, document);

  await app.listen(3000);
}
bootstrap();
```

`SwaggerModule.setup('docs', ...)`로 등록하면 `http://localhost:3000/docs`에서 Swagger UI가, `http://localhost:3000/docs-json`에서 OpenAPI JSON 원본이 열린다. `-json` 엔드포인트는 프론트엔드가 코드 생성기(openapi-generator 등)에 물릴 때 쓰니 경로를 기억해 두면 좋다.

`createDocument`는 bootstrap 시점에 컨트롤러를 전부 스캔해서 스펙 객체를 한 번 만든다. 런타임 요청마다 다시 만드는 게 아니다. 그래서 라우트를 동적으로 바꾸는 게 아니면 성능 부담은 없다.


## DocumentBuilder 설정

`DocumentBuilder`는 OpenAPI 문서의 최상단 메타데이터를 구성하는 빌더다. 체이닝으로 필요한 항목만 붙인다. 실무에서 자주 쓰는 것들만 추린다.

```typescript
const config = new DocumentBuilder()
  .setTitle('주문 API')
  .setDescription('주문/결제 도메인 REST API')
  .setVersion('1.0')
  .addServer('https://api.example.com', '운영')
  .addServer('http://localhost:3000', '로컬')
  .addTag('orders', '주문 생성/조회')
  .addTag('payments', '결제 승인/취소')
  .build();
```

`addServer`는 UI 상단에 서버 선택 드롭다운을 만든다. 로컬에서 띄운 Swagger UI로 운영 API를 직접 때려보고 싶을 때 쓴다. 단, 운영 서버 URL을 로컬 문서에 박아두면 실수로 운영에 요청이 나갈 수 있으니, 운영을 첫 번째에 두지 않는 편이 안전하다.

`addTag`로 미리 태그를 선언해 두면 UI에서 그룹 순서와 설명이 정리된다. 컨트롤러에 `@ApiTags()`만 쓰면 태그는 생기지만 설명은 안 붙는다.

버전 문자열(`setVersion`)은 UI 제목 옆에 표시될 뿐 라우팅과는 무관하다. NestJS의 URI 버저닝(`/v1/orders`)과 헷갈리기 쉬운데 서로 별개다.


## 컨트롤러 데코레이터 — @ApiTags, @ApiOperation, @ApiResponse

컨트롤러에 아무 데코레이터도 안 붙여도 라우트는 문서에 나온다. 다만 설명이 비어 있어서 쓸모가 적다. 세 개만 제대로 붙이면 문서 가독성이 크게 올라간다.

```typescript
import { Controller, Get, Post, Body, Param } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiParam } from '@nestjs/swagger';

@ApiTags('orders')
@Controller('orders')
export class OrderController {
  @Post()
  @ApiOperation({ summary: '주문 생성', description: '재고를 확인하고 주문을 생성한다' })
  @ApiResponse({ status: 201, description: '생성 성공', type: OrderResponseDto })
  @ApiResponse({ status: 409, description: '재고 부족' })
  create(@Body() dto: CreateOrderDto) {
    return this.orderService.create(dto);
  }

  @Get(':id')
  @ApiOperation({ summary: '주문 단건 조회' })
  @ApiParam({ name: 'id', description: '주문 ID', example: 1024 })
  @ApiResponse({ status: 200, type: OrderResponseDto })
  @ApiResponse({ status: 404, description: '주문 없음' })
  findOne(@Param('id') id: string) {
    return this.orderService.findOne(+id);
  }
}
```

`@ApiTags`는 클래스에 붙이면 그 컨트롤러의 모든 라우트가 같은 그룹으로 묶인다. 메서드마다 다른 태그를 주고 싶으면 메서드에도 붙일 수 있다.

`@ApiResponse`의 `type`에 DTO 클래스를 넘기면 응답 본문 스키마가 그 DTO 기준으로 그려진다. 상태 코드별로 여러 번 붙일 수 있다. 자주 쓰는 코드는 `@ApiOkResponse`, `@ApiCreatedResponse`, `@ApiNotFoundResponse` 같은 단축 데코레이터로 대체할 수 있는데, 결국 `@ApiResponse({ status })`의 래퍼라 동작은 같다.

여기서 자주 놓치는 점이 있다. `@ApiResponse`에 `type`을 안 주면 응답 본문이 문서에 안 그려진다. 그리고 응답을 인터셉터로 감싸는 경우—예를 들어 모든 응답을 `{ success, data }`로 래핑하는 구조—라면, 컨트롤러가 반환하는 DTO와 클라이언트가 실제로 받는 본문이 다르다. 이때 `type`에 DTO만 적으면 문서가 거짓말을 한다. 이 문제는 아래 제네릭 래퍼 절에서 다룬다.


## 쿼리·헤더·경로 파라미터 — @ApiQuery, @ApiHeader, @ApiParam

`@ApiParam`은 경로 파라미터를, `@ApiQuery`는 쿼리 스트링을, `@ApiHeader`는 요청 헤더를 문서에 명시한다. 셋 다 비슷한 옵션을 받는다.

```typescript
@Get(':id/items')
@ApiOperation({ summary: '주문의 상품 목록 조회' })
@ApiParam({ name: 'id', description: '주문 ID', example: 1024, type: Number })
@ApiQuery({ name: 'category', description: '카테고리 필터', required: false, enum: ['food', 'goods'] })
@ApiHeader({ name: 'X-Request-Id', description: '요청 추적용 UUID', required: false })
findItems(
  @Param('id') id: string,
  @Query('category') category?: string,
  @Headers('X-Request-Id') requestId?: string,
) {
  return this.orderService.findItems(+id, category);
}
```

`required: false`를 안 주면 모든 쿼리·헤더가 필수로 그려진다. UI에서 "Try it out" 했을 때 안 채워도 통과돼야 하는 값은 명시적으로 옵셔널을 표시한다.

페이지네이션은 거의 모든 목록 API에 붙는다. 매 라우트에 `@ApiQuery({ name: 'page' })`, `@ApiQuery({ name: 'size' })`를 반복해 적으면 금방 지친다. 두 가지 방식이 있다. 첫째, DTO로 묶는다.

```typescript
export class PaginationQueryDto {
  @ApiPropertyOptional({ description: '페이지 번호', minimum: 1, default: 1, example: 1 })
  @Type(() => Number)
  @IsInt()
  @Min(1)
  page: number = 1;

  @ApiPropertyOptional({ description: '페이지 크기', minimum: 1, maximum: 100, default: 20, example: 20 })
  @Type(() => Number)
  @IsInt()
  @Min(1)
  @Max(100)
  size: number = 20;
}

@Get()
findAll(@Query() query: PaginationQueryDto) {
  return this.orderService.findAll(query);
}
```

`@Query()`에 DTO를 받으면 각 필드가 자동으로 쿼리 파라미터로 그려진다. 컨트롤러 메서드는 깔끔해지고, 페이지네이션을 쓰는 모든 라우트에서 같은 DTO를 재사용한다. 검증 데코레이터(`@Min`, `@Max`)와 변환(`@Type(() => Number)`)이 같이 붙어 있어 안전하다.

둘째, 커스텀 데코레이터로 묶는다. 페이지네이션 쿼리 두 개와 정렬 한 개처럼 반복되는 묶음을 데코레이터 하나로 만든다.

```typescript
import { applyDecorators } from '@nestjs/common';
import { ApiQuery } from '@nestjs/swagger';

export const ApiPagination = () =>
  applyDecorators(
    ApiQuery({ name: 'page', required: false, type: Number, example: 1 }),
    ApiQuery({ name: 'size', required: false, type: Number, example: 20 }),
    ApiQuery({ name: 'sort', required: false, type: String, example: '-createdAt' }),
  );

@Get()
@ApiPagination()
findAll(@Query() query: any) {}
```

DTO 방식이 검증까지 한꺼번에 처리돼 보통 더 낫다. 커스텀 데코레이터는 검증 로직을 별도로 처리하는 게이트웨이 같은 곳에서 쓴다.

`@ApiQuery`에서 자주 잊는 게 `isArray: true`다. `?ids=1&ids=2`처럼 같은 키를 여러 번 받는 경우, `type: Number` 단독으로 두면 단일 값으로 그려진다. `isArray: true, type: Number`를 같이 명시해야 배열 입력 UI가 나온다.


## DTO 자동 스키마 생성과 @ApiProperty

응답·요청 본문 스키마는 DTO 클래스에서 나온다. 그런데 TypeScript의 타입 정보는 컴파일하면 대부분 사라진다. Swagger는 런타임에 동작하므로, 데코레이터로 명시하지 않으면 프로퍼티의 타입과 존재 자체를 알 수가 없다. 그래서 기본적으로는 `@ApiProperty`를 직접 붙여야 한다.

```typescript
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsString, IsInt, Min } from 'class-validator';

export class CreateOrderDto {
  @ApiProperty({ description: '상품 ID', example: 501 })
  @IsInt()
  productId: number;

  @ApiProperty({ description: '수량', minimum: 1, example: 2 })
  @IsInt()
  @Min(1)
  quantity: number;

  @ApiPropertyOptional({ description: '메모', example: '문 앞에 놓아주세요' })
  @IsString()
  memo?: string;
}
```

`@ApiProperty`를 안 붙인 프로퍼티는 스키마에서 통째로 빠진다. DTO에 필드가 다섯 개인데 데코레이터를 세 개만 붙였으면, 문서에는 세 개만 나오고 나머지 두 개는 없는 셈이 된다. 처음 Swagger를 붙이면 "분명 DTO에 필드가 있는데 문서가 비어 있다"는 상황을 거의 다 겪는데, 원인은 이것이다.

`@ApiProperty`의 옵션으로 자주 쓰는 것들:

- `required: false` — 옵셔널 표시. `@ApiPropertyOptional`이 이걸 미리 적용한 버전이다.
- `enum` — enum 타입일 때 선택지를 드롭다운으로 보여준다. `enum: OrderStatus`처럼 enum 객체를 그대로 넘긴다.
- `nullable: true` — `null`이 올 수 있음을 명시.
- `type` — 배열이나 중첩 객체일 때 명시. 배열은 `type: [ItemDto]`처럼 대괄호로 감싼다.
- `example` — UI의 "Try it out"에 채워질 기본값. 이게 있으면 프론트엔드가 요청 형태를 바로 이해한다.

중첩 객체와 배열은 타입 추론이 특히 약하다. `items: ItemDto[]` 같은 필드는 `@ApiProperty({ type: [ItemDto] })`로 명시하지 않으면 빈 배열로만 나온다. 제네릭(`Page<T>`)은 타입 정보가 더 안 남아서 별도 처리가 필요하다(아래 절).


## CLI 플러그인 — @ApiProperty를 안 붙이고 자동 추론

필드마다 `@ApiProperty`를 붙이는 건 금방 지친다. 게다가 `@ApiProperty`에 적은 내용이 `class-validator` 데코레이터와 중복된다. `@Min(1)`을 붙였는데 `@ApiProperty({ minimum: 1 })`을 또 적는 식이다. 이 중복을 없애는 게 CLI 플러그인이다.

플러그인은 컴파일 단계에서 AST를 분석해, 명시적으로 안 붙인 `@ApiProperty`를 자동으로 끼워 넣는다. 추론 근거는 세 가지다.

- TypeScript 타입 — `productId: number`를 보고 `type: Number`를 채운다.
- `?` 여부 — `memo?: string`을 보고 `required: false`를 채운다.
- `class-validator` 데코레이터 — `@Min(1)`을 보고 `minimum: 1`을, `@IsEnum`을 보고 `enum`을 채운다.

`nest-cli.json`에 플러그인을 등록한다.

```json
{
  "compilerOptions": {
    "plugins": [
      {
        "name": "@nestjs/swagger",
        "options": {
          "introspectComments": true
        }
      }
    ]
  }
}
```

`introspectComments: true`를 켜면 프로퍼티 위의 JSDoc 주석을 읽어서 `description`으로 넣는다. 즉 아래처럼 쓰면 데코레이터 하나 없이도 문서가 채워진다.

```typescript
export class CreateOrderDto {
  /** 상품 ID */
  @IsInt()
  productId: number;

  /** 수량 */
  @IsInt()
  @Min(1)
  quantity: number;

  /** 배송 메모 */
  @IsString()
  memo?: string;
}
```

플러그인을 쓸 때 걸리는 지점이 두 개 있다.

첫째, 플러그인은 `nest build`(내부적으로 `ts-loader`/`tsc` + 플러그인 훅) 경로로 컴파일할 때만 동작한다. `nest start`나 `nest build`는 문제없는데, `jest`로 테스트를 돌릴 때는 ts-jest가 별도 컴파일을 하므로 플러그인이 안 먹는다. 테스트에서 Swagger 문서를 검증한다면 ts-jest 설정에 플러그인을 따로 물려야 한다. 보통은 테스트에서 문서를 검증할 일이 없으니 무시해도 된다.

둘째, 플러그인은 "추론"이라 한계가 있다. 제네릭 타입, 유니온 타입, 인터페이스 기반 필드는 추론을 못 한다. 이런 필드는 여전히 `@ApiProperty`를 직접 붙여야 한다. 그래서 실무에서는 플러그인으로 80%를 자동화하고, 추론이 안 되는 곳만 수동으로 보강하는 식으로 간다.


## Mapped Types — DTO를 깎아 쓰는 방법

같은 자원을 다루는 DTO가 비슷비슷하게 여러 개 생긴다. `CreateOrderDto`로 만들고 `UpdateOrderDto`로 수정한다면, 보통 수정은 모든 필드가 옵셔널이다. 그렇다고 같은 필드를 두 번 적고 데코레이터도 두 벌 붙이면 동기화가 깨진다. `@nestjs/swagger`의 Mapped Types가 이걸 해결한다.

```typescript
import { PartialType, PickType, OmitType, IntersectionType } from '@nestjs/swagger';

export class CreateOrderDto {
  @ApiProperty({ example: 501 }) productId: number;
  @ApiProperty({ example: 2 }) quantity: number;
  @ApiPropertyOptional({ example: '문 앞에 놓아주세요' }) memo?: string;
}

// 전부 옵셔널로 변환
export class UpdateOrderDto extends PartialType(CreateOrderDto) {}

// 특정 필드만 뽑기
export class OrderQuantityDto extends PickType(CreateOrderDto, ['quantity'] as const) {}

// 특정 필드 빼기
export class OrderWithoutMemoDto extends OmitType(CreateOrderDto, ['memo'] as const) {}

// 두 DTO 합치기
export class OrderWithUserDto extends IntersectionType(CreateOrderDto, UserDto) {}
```

`PartialType`은 모든 필드를 옵셔널로 만들고, `PickType`은 지정한 필드만 남기고, `OmitType`은 지정한 필드를 뺀다. 핵심은 이 함수들이 `@ApiProperty` 메타데이터까지 그대로 복사·변형해서 새 클래스에 붙여 준다는 점이다. 그래서 파생 클래스에 `@ApiProperty`를 다시 안 붙여도 문서가 제대로 나온다.

주의할 점이 두 가지 있다. 첫째, `@nestjs/mapped-types`와 `@nestjs/swagger`에서 각각 같은 이름의 함수를 export 한다. 이름이 같아도 동작이 미묘하게 다르다. `@nestjs/swagger` 쪽이 `@ApiProperty`까지 복사하므로, Swagger를 쓰는 프로젝트라면 무조건 `@nestjs/swagger`에서 import 한다. `@nestjs/mapped-types`에서 import 하면 검증은 되지만 문서에 필드가 안 나온다. 이 실수는 IDE 자동 import에 끌려가서 자주 일어난다.

둘째, `as const`를 빠뜨리면 타입스크립트가 필드 이름 리터럴을 잃어버려 컴파일 에러가 난다. `PickType(CreateOrderDto, ['quantity'] as const)`처럼 항상 `as const`를 붙인다.

`IntersectionType`은 두 DTO를 합쳐 새 DTO를 만들 때 쓴다. 사용자 정보와 주문 정보를 한 응답에 묶는 경우 같이. 다만 필드 이름이 겹치면 뒤쪽이 이긴다는 점은 미리 확인해야 한다. 다른 데코레이터(`@IsString` 같은 검증)도 같이 복사되므로, 파생 DTO에 다시 붙이면 중복 적용으로 동작이 꼬일 수 있다.


## 파일 업로드 문서화 — @ApiConsumes와 multipart/form-data

파일 업로드 라우트는 일반 JSON 본문과 다르다. 본문 콘텐츠 타입이 `multipart/form-data`고, 필드 하나가 바이너리(`type: 'string', format: 'binary'`)다. Swagger는 이걸 자동으로 추론하지 못해 `@ApiConsumes`와 `@ApiBody`로 직접 그려 줘야 한다.

```typescript
import { Controller, Post, UploadedFile, UseInterceptors, Body } from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { ApiConsumes, ApiBody } from '@nestjs/swagger';

@Post('upload')
@ApiConsumes('multipart/form-data')
@ApiBody({
  schema: {
    type: 'object',
    properties: {
      file: { type: 'string', format: 'binary' },
      description: { type: 'string', example: '주문 영수증' },
    },
    required: ['file'],
  },
})
@UseInterceptors(FileInterceptor('file'))
uploadReceipt(
  @UploadedFile() file: Express.Multer.File,
  @Body('description') description?: string,
) {
  return this.fileService.save(file, description);
}
```

`@ApiConsumes('multipart/form-data')`가 없으면 UI의 "Try it out"에서 파일 선택 입력이 안 나온다. `@ApiBody`의 `schema`는 OpenAPI 객체를 그대로 받는데, `format: 'binary'`가 파일 입력의 신호다.

여러 파일을 동시에 업로드하는 경우는 `items`로 표현한다.

```typescript
@Post('upload-many')
@ApiConsumes('multipart/form-data')
@ApiBody({
  schema: {
    type: 'object',
    properties: {
      files: {
        type: 'array',
        items: { type: 'string', format: 'binary' },
      },
    },
  },
})
@UseInterceptors(FilesInterceptor('files', 10))
uploadMany(@UploadedFiles() files: Express.Multer.File[]) {
  return this.fileService.saveAll(files);
}
```

DTO 클래스로 표현하고 싶다면 `@ApiProperty({ type: 'string', format: 'binary' })`를 붙인 클래스를 만들고 `@ApiBody({ type: FileUploadDto })`로 넘기는 방법도 있다. 다만 클래스 변환이 multipart에서 잘 안 먹는 케이스가 있어, 실무에서는 위처럼 `schema`를 직접 적는 쪽이 일관성 있다.

파일 업로드 라우트는 글로벌 `ValidationPipe`가 본문 검증을 시도하다 깨질 수 있다. `multipart/form-data`는 파서가 다르고 `class-transformer`가 파일 객체를 변환하다 실패하기도 한다. 라우트 단위로 파이프를 끄거나, 파일은 `@UploadedFile()`로 받고 나머지 필드만 검증하는 식으로 분리한다.


## JWT/Bearer 인증 표현 — addBearerAuth

인증이 걸린 API는 Swagger UI에서 토큰을 넣고 호출할 수 있어야 한다. 두 단계가 필요하다. `DocumentBuilder`에 인증 스킴을 선언하고, 인증이 필요한 라우트에 `@ApiBearerAuth`를 붙인다.

```typescript
const config = new DocumentBuilder()
  .setTitle('주문 API')
  .setVersion('1.0')
  .addBearerAuth(
    { type: 'http', scheme: 'bearer', bearerFormat: 'JWT' },
    'access-token', // 이 이름이 @ApiBearerAuth와 매칭된다
  )
  .build();
```

```typescript
import { ApiBearerAuth } from '@nestjs/swagger';
import { UseGuards } from '@nestjs/common';

@ApiTags('orders')
@ApiBearerAuth('access-token') // addBearerAuth에서 준 이름과 동일해야 한다
@UseGuards(JwtAuthGuard)
@Controller('orders')
export class OrderController {}
```

`addBearerAuth`의 두 번째 인자(여기서는 `'access-token'`)는 스킴의 이름이다. `@ApiBearerAuth`에 같은 이름을 넘겨야 둘이 연결된다. 이름을 안 주면 기본값이 `'bearer'`라 양쪽 다 생략해도 동작하지만, 인증 스킴이 여러 개일 때 헷갈리니 이름을 명시하는 편이 낫다.

`@ApiBearerAuth`는 클래스에 붙이면 그 컨트롤러 전체에, 메서드에 붙이면 해당 라우트에만 자물쇠 표시가 생긴다. 이 데코레이터는 문서에 "이 API는 토큰이 필요하다"고 표시할 뿐, 실제 인증을 거는 건 `@UseGuards(JwtAuthGuard)`다. 둘은 별개라서 한쪽만 붙이는 실수를 자주 한다. 가드만 붙이고 `@ApiBearerAuth`를 안 붙이면, UI에서 토큰을 넣어도 요청 헤더에 안 실려서 401이 난다.

실무에서 거슬리는 점 하나. Swagger UI는 새로고침하면 입력한 토큰을 잊어버린다. 개발 중에 토큰을 매번 다시 붙여넣는 게 번거로운데, `setup`에 `persistAuthorization`을 켜면 브라우저 로컬스토리지에 토큰을 저장해 새로고침해도 유지된다.

```typescript
SwaggerModule.setup('docs', app, document, {
  swaggerOptions: {
    persistAuthorization: true,
  },
});
```

`persistAuthorization`은 토큰을 브라우저에 평문으로 저장하므로 운영 환경에 노출된 문서에서는 켜지 않는 게 맞다. 어차피 운영에서는 문서 자체를 막는 게 정석이다(아래).


## Cookie·API Key 인증 스킴

`addBearerAuth` 말고도 `DocumentBuilder`는 다른 인증 스킴을 지원한다. 세션 쿠키 기반 서비스나 내부용 API Key를 쓰는 라우트가 섞여 있다면 같이 등록한다.

```typescript
const config = new DocumentBuilder()
  .setTitle('주문 API')
  .setVersion('1.0')
  .addBearerAuth({ type: 'http', scheme: 'bearer', bearerFormat: 'JWT' }, 'access-token')
  .addCookieAuth('SESSION_ID', { type: 'apiKey', in: 'cookie', name: 'SESSION_ID' }, 'session')
  .addApiKey({ type: 'apiKey', name: 'X-API-Key', in: 'header' }, 'api-key')
  .build();
```

라우트마다 어떤 스킴이 필요한지 데코레이터로 표시한다.

```typescript
@ApiCookieAuth('session')
@Controller('admin/orders')
export class AdminOrderController {}

@ApiSecurity('api-key')
@Controller('internal/sync')
export class InternalSyncController {}
```

`@ApiSecurity`는 임의 스킴 이름을 받는 범용 데코레이터다. `@ApiCookieAuth`, `@ApiBearerAuth`는 각자 전용 단축형이지만, 결국 같은 메타데이터를 붙인다.

쿠키 인증을 Swagger UI에서 직접 테스트하려면 한 가지 함정이 있다. 브라우저는 cross-origin 요청에서 쿠키를 자동으로 안 보낸다. Swagger UI가 다른 도메인(예: `localhost:3000/docs`에서 `api.example.com`)으로 요청을 날리는 경우 쿠키가 안 실린다. 같은 도메인이거나, `setup` 옵션에 `withCredentials: true`를 켜야 한다.

```typescript
SwaggerModule.setup('docs', app, document, {
  swaggerOptions: {
    withCredentials: true,
  },
});
```

서버 쪽도 CORS 설정에서 `credentials: true`를 켜야 쿠키가 통과한다. 둘 중 하나라도 빠지면 UI에서 인증된 요청이 안 나간다.

API Key 인증은 사내 시스템 간 통신에서 자주 쓴다. 운영 환경에서는 Swagger UI 자체를 안 노출하니 큰 문제는 없지만, 개발 환경에서 키 값을 UI에 입력해 두고 깜빡 잊은 채 화면을 공유하지 않도록 주의한다. `persistAuthorization`을 켜 두면 로컬스토리지에 그대로 남아 있다.

여러 스킴을 동시에 거는 라우트도 가능하다. JWT가 만료된 사용자에게는 임시 토큰 헤더를 대신 받게 하는 식인데, `@ApiSecurity`를 여러 번 붙이면 둘 다 표시된다. 다만 OpenAPI 스펙상 두 스킴은 "OR" 관계인지 "AND" 관계인지 명시가 모호해, 클라이언트 코드 생성기마다 해석이 다르다. 가능하면 한 라우트에는 한 스킴만 거는 편이 낫다.


## 제네릭 응답 래퍼 문서화 — ApiExtraModels, getSchemaPath

응답을 공통 포맷으로 감싸는 구조가 많다. 인터셉터에서 모든 응답을 `{ success, data, timestamp }`로 래핑하는 식이다. 이때 `data` 자리에 들어가는 타입은 API마다 다르다. 이런 제네릭 구조는 데코레이터의 `type` 한 줄로는 표현이 안 된다. TypeScript 제네릭(`ApiResponseDto<T>`)은 런타임에 `T`가 사라지기 때문이다.

먼저 공통 래퍼 DTO를 정의한다. 제네릭 파라미터 `T`가 들어가는 `data` 필드는 `@ApiProperty`를 안 붙인다. 어차피 타입이 안 남아 의미가 없고, 뒤에서 스키마를 직접 합성할 것이다.

```typescript
import { ApiProperty } from '@nestjs/swagger';

export class ApiResponseDto<T> {
  @ApiProperty({ example: true })
  success: boolean;

  @ApiProperty({ example: '2026-05-27T10:00:00.000Z' })
  timestamp: string;

  data: T; // 여기는 데코레이터를 붙이지 않는다
}
```

핵심은 두 함수다. `ApiExtraModels`는 컨트롤러에서 직접 참조되지 않는 DTO를 스펙의 `components.schemas`에 강제로 등록한다. 제네릭의 `data`에 들어가는 타입은 어디서도 `type`으로 명시되지 않아 스캔에 안 잡히므로, 이걸로 등록해 줘야 한다. `getSchemaPath`는 그렇게 등록된 모델의 `$ref` 경로(`#/components/schemas/OrderResponseDto`)를 문자열로 돌려준다.

이 둘을 `applyDecorators`로 묶어 재사용 가능한 커스텀 데코레이터를 만든다. OpenAPI의 `allOf`로 공통 래퍼 스키마와 실제 데이터 스키마를 합성하는 게 요령이다.

```typescript
import { applyDecorators, Type } from '@nestjs/common';
import { ApiExtraModels, ApiOkResponse, getSchemaPath } from '@nestjs/swagger';

export const ApiOkResponseWrapped = <TModel extends Type<unknown>>(model: TModel) =>
  applyDecorators(
    ApiExtraModels(ApiResponseDto, model),
    ApiOkResponse({
      schema: {
        allOf: [
          { $ref: getSchemaPath(ApiResponseDto) },
          {
            properties: {
              data: { $ref: getSchemaPath(model) },
            },
          },
        ],
      },
    }),
  );
```

이제 컨트롤러에서는 한 줄로 끝난다.

```typescript
@Get(':id')
@ApiOkResponseWrapped(OrderResponseDto)
findOne(@Param('id') id: string) {
  return this.orderService.findOne(+id);
}
```

문서에는 `{ success, timestamp, data: OrderResponseDto }` 형태로 정확히 그려진다. 배열을 감싸는 경우도 많으니, `data`가 배열인 버전을 따로 만들어 두면 편하다.

```typescript
export const ApiOkResponseWrappedArray = <TModel extends Type<unknown>>(model: TModel) =>
  applyDecorators(
    ApiExtraModels(ApiResponseDto, model),
    ApiOkResponse({
      schema: {
        allOf: [
          { $ref: getSchemaPath(ApiResponseDto) },
          {
            properties: {
              data: { type: 'array', items: { $ref: getSchemaPath(model) } },
            },
          },
        ],
      },
    }),
  );
```

여기서 자주 만나는 증상이 `getSchemaPath`로 참조했는데 `$ref`가 깨진 것처럼 나오는 경우다. 원인은 대상 모델이 스펙에 등록되지 않은 것이다. `ApiExtraModels`에 그 모델을 빠뜨렸거나, 모델 자체에 `@ApiProperty`가 하나도 없어 빈 스키마로 등록된 경우다. `ApiExtraModels`는 컨트롤러나 클래스 위에 직접 붙여도 되고, 위처럼 데코레이터 안에 포함시켜도 된다.


## 다형성 응답 — oneOf, anyOf, discriminator

결제 수단별로 응답 형태가 다른 API가 있다고 하자. 카드 결제는 `cardNumber`, `installment`가 있고, 계좌 이체는 `bankCode`, `accountNumber`가 있다. 응답 타입은 `CardPayment | BankPayment` 같은 유니온이다. TypeScript에서는 표현돼도 OpenAPI에서는 `type: CardPayment` 한 줄로 안 풀린다. `oneOf` 또는 `anyOf`로 그려야 한다.

```typescript
export class CardPaymentDto {
  @ApiProperty({ enum: ['card'] }) method: 'card';
  @ApiProperty() cardNumber: string;
  @ApiProperty() installment: number;
}

export class BankPaymentDto {
  @ApiProperty({ enum: ['bank'] }) method: 'bank';
  @ApiProperty() bankCode: string;
  @ApiProperty() accountNumber: string;
}

@Get(':id/payment')
@ApiExtraModels(CardPaymentDto, BankPaymentDto)
@ApiOkResponse({
  schema: {
    oneOf: [
      { $ref: getSchemaPath(CardPaymentDto) },
      { $ref: getSchemaPath(BankPaymentDto) },
    ],
    discriminator: {
      propertyName: 'method',
      mapping: {
        card: getSchemaPath(CardPaymentDto),
        bank: getSchemaPath(BankPaymentDto),
      },
    },
  },
})
getPayment(@Param('id') id: string) {
  return this.paymentService.findByOrderId(+id);
}
```

`oneOf`는 "정확히 하나"라는 뜻이고 `anyOf`는 "하나 이상"이다. 결제 응답처럼 어느 한 형태로만 떨어지는 경우는 `oneOf`가 맞다. 두 형태가 동시에 유효할 수도 있는 응답은 `anyOf`다.

`discriminator`는 클라이언트가 응답을 받았을 때 어떤 타입인지 판별하는 키를 알려 준다. `propertyName: 'method'`는 응답 본문의 `method` 필드 값으로 분기한다는 뜻이다. `mapping`이 그 값과 스키마를 연결한다. 이걸 잘 설정해 두면 openapi-generator 같은 도구가 클라이언트 코드에서 자동으로 타입 분기를 만들어 준다.

`discriminator`를 빠뜨리면 동작은 한다. UI에는 두 응답 형태가 다 보인다. 다만 코드 생성기는 분기 로직을 못 만들고 그냥 유니온으로만 내보낸다. 프론트가 매번 `if (res.method === 'card')`를 직접 적어야 한다.

요청 본문에 다형성을 쓰는 경우도 같다. `@ApiBody({ schema: { oneOf: [...] } })`로 같은 패턴을 적는다. 다만 NestJS의 `ValidationPipe`는 클래스 한 개를 기준으로 검증하므로, 다형성 요청은 보통 `class-transformer`의 `@Type` + `discriminator` 옵션을 같이 써야 검증까지 완전히 처리된다. 검증과 문서가 따로 노는 흔한 지점이라 처음 다루면 손이 한참 간다.


## 응답 예제 다중 지정 — examples 옵션

`@ApiResponse({ example: ... })`는 예제를 하나만 받는다. 같은 상태 코드라도 상황별로 본문이 다른 응답이 많다. 200 OK인데 "신규 가입자"일 때와 "기존 사용자"일 때 본문이 다른 식이다. 이때 `examples`로 여러 개를 나열한다.

```typescript
@Get('me')
@ApiOkResponse({
  description: '내 정보 조회',
  content: {
    'application/json': {
      schema: { $ref: getSchemaPath(UserDto) },
      examples: {
        newUser: {
          summary: '신규 가입자',
          value: { id: 1, name: '신규', joinedAt: '2026-06-01', isVerified: false },
        },
        verifiedUser: {
          summary: '인증된 사용자',
          value: { id: 2, name: '인증', joinedAt: '2024-01-15', isVerified: true },
        },
      },
    },
  },
})
getMe() {}
```

`content` 키로 미디어 타입별 응답을 따로 정의한다. JSON 외에 XML이나 CSV로도 응답하는 API라면 `'application/xml'`, `'text/csv'` 키를 같이 둔다.

```typescript
@Get('export')
@ApiOkResponse({
  content: {
    'application/json': { schema: { $ref: getSchemaPath(ReportDto) } },
    'text/csv': { schema: { type: 'string', example: 'id,amount\n1,1000\n' } },
  },
})
exportReport(@Query('format') format: string) {}
```

UI는 미디어 타입을 드롭다운으로 보여 주고, 각각에 맞는 예제를 토글로 볼 수 있게 한다. 예제 값이 실제 응답과 한참 다르면 프론트가 오해해 디버깅 시간을 잡아먹는다. 응답 형식을 바꿨으면 `examples`도 같이 손본다. 이 동기화가 자주 어긋나서, 핵심 라우트는 e2e 테스트에서 예제 값과 실제 응답이 같은 키 집합을 가지는지 확인하는 식으로 방어하는 팀도 있다.


## 운영 환경에서 Swagger 노출 차단

API 문서는 엔드포인트 목록, 요청/응답 구조, 인증 방식을 전부 보여준다. 운영 환경에 그대로 열어두면 공격자에게 명세서를 건네는 꼴이다. `/docs`가 인터넷에 열려 있는 서비스가 생각보다 많은데, 대부분 "개발할 때 켜두고 끄는 걸 잊은" 경우다.

가장 단순한 방법은 환경 변수로 분기해서 운영에서는 `setup` 자체를 호출하지 않는 것이다.

```typescript
// main.ts
async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  if (process.env.NODE_ENV !== 'production') {
    const config = new DocumentBuilder()
      .setTitle('주문 API')
      .setVersion('1.0')
      .addBearerAuth(/* ... */)
      .build();
    const document = SwaggerModule.createDocument(app, config);
    SwaggerModule.setup('docs', app, document);
  }

  await app.listen(3000);
}
```

`setup`을 안 부르면 `/docs`와 `/docs-json` 라우트 자체가 등록되지 않는다. 운영에서 그 경로로 접근하면 404가 난다. `createDocument`까지 조건문 안에 넣은 이유는, 운영에서 굳이 스펙 객체를 메모리에 올릴 필요가 없기 때문이다.

운영에서도 사내망이나 특정 인원에게는 문서를 열어야 할 때가 있다. 이때는 완전히 막는 대신 Basic 인증을 앞에 거는 방법을 쓴다. `/docs` 경로에만 미들웨어를 붙이면 된다.

```typescript
import * as basicAuth from 'express-basic-auth';

app.use(
  ['/docs', '/docs-json'],
  basicAuth({
    challenge: true,
    users: { [process.env.DOCS_USER]: process.env.DOCS_PASSWORD },
  }),
);
```

이 미들웨어는 `SwaggerModule.setup` 호출보다 먼저 등록해야 순서상 인증이 앞선다. `-json` 경로를 빠뜨리면 UI는 막혔는데 원본 JSON은 그대로 열려서 의미가 없어지니, 두 경로를 같이 막는다.

운영 노출을 차단하는 또 다른 흔한 실수는, 리버스 프록시(Nginx 등) 레벨에서 `/docs`를 막아두고 안심하는 것이다. 내부 서비스 간 호출이나 프록시를 우회하는 경로가 있으면 그대로 뚫린다. 애플리케이션 레벨에서 막는 게 확실하다.


## 여러 Swagger 문서 분리 운영

같은 NestJS 애플리케이션 안에 외부용 공개 API, 관리자 API, 내부 서비스 간 API가 섞여 있는 경우가 흔하다. 한 화면에 다 보여 주면 페이지가 너무 길고, 관리자용 라우트가 공개 문서에 같이 노출되는 위험도 있다. `SwaggerModule.createDocument`의 `include` 옵션으로 모듈별 문서를 따로 만든다.

```typescript
// main.ts
async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  const publicConfig = new DocumentBuilder()
    .setTitle('공개 API')
    .setVersion('1.0')
    .addBearerAuth({ type: 'http', scheme: 'bearer' }, 'access-token')
    .build();
  const publicDoc = SwaggerModule.createDocument(app, publicConfig, {
    include: [OrderModule, ProductModule],
  });
  SwaggerModule.setup('docs/public', app, publicDoc);

  const adminConfig = new DocumentBuilder()
    .setTitle('관리자 API')
    .setVersion('1.0')
    .addBearerAuth({ type: 'http', scheme: 'bearer' }, 'admin-token')
    .build();
  const adminDoc = SwaggerModule.createDocument(app, adminConfig, {
    include: [AdminModule],
  });
  SwaggerModule.setup('docs/admin', app, adminDoc);

  await app.listen(3000);
}
```

`include`에 모듈을 넣으면 그 모듈에 등록된 컨트롤러만 스캔한다. 빠진 모듈의 라우트는 해당 문서에 안 그려진다. 그러면 공개 문서 URL을 외부에 알려 주고, 관리자 문서 URL은 사내망에서만 접근 가능하도록 미들웨어로 가린다.

여기서 헷갈리는 점이 있다. `include`가 들어간 라우트만 그려진다고 해서, 다른 모듈의 라우트가 실제로 안 동작하는 건 아니다. 라우트는 정상 등록돼 있고 호출도 된다. 단지 그 문서에 안 나올 뿐이다. 관리자 라우트를 공개 문서에서 가린다고 보안이 되는 게 아니다. 인증·인가는 따로 가드로 막아야 한다.

`include` 대신 또는 같이 쓰는 게 `extraModels` 옵션이다. 컨트롤러에 직접 참조되지 않지만 스키마로는 필요한 DTO를 한꺼번에 등록한다. 제네릭 래퍼처럼 동적으로만 참조되는 모델을 모아 두는 데 쓴다.

```typescript
const document = SwaggerModule.createDocument(app, config, {
  extraModels: [ApiResponseDto, ErrorResponseDto, PageDto],
});
```


## OpenAPI 스펙 외부 추출과 CI 연동

런타임에 문서가 자동 생성된다는 건, 빌드 시점에 정적 파일로 뽑을 수도 있다는 뜻이다. 프론트엔드가 백엔드 OpenAPI 스펙으로 API 클라이언트 코드를 생성하는 파이프라인을 만들 때 이게 쓰인다. 매번 백엔드를 띄워서 `/docs-json`을 긁어 오는 게 아니라, 백엔드 빌드 산출물에 `openapi.json`이 들어 있고 프론트가 그걸 읽는다.

추출용 스크립트는 따로 둔다. 평소 부팅과 분리해서, `tsx scripts/generate-openapi.ts`처럼 호출한다.

```typescript
// scripts/generate-openapi.ts
import { NestFactory } from '@nestjs/core';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { writeFileSync } from 'fs';
import { AppModule } from '../src/app.module';

async function generate() {
  const app = await NestFactory.create(AppModule, { logger: false });
  const config = new DocumentBuilder()
    .setTitle('주문 API')
    .setVersion('1.0')
    .addBearerAuth({ type: 'http', scheme: 'bearer' }, 'access-token')
    .build();
  const document = SwaggerModule.createDocument(app, config);
  writeFileSync('./openapi.json', JSON.stringify(document, null, 2));
  await app.close();
  console.log('openapi.json 생성 완료');
}
generate();
```

`app.listen`을 호출하지 않고 `createDocument`까지만 가서 파일로 떨군다. 포트를 열 필요가 없어 CI에서도 빨리 끝난다. 마지막에 `app.close`를 안 부르면 핸들이 살아 있어서 프로세스가 종료되지 않는다.

GitHub Actions나 GitLab CI에서 이 스크립트를 백엔드 빌드 직후에 돌린다. 결과로 나온 `openapi.json`을 아티팩트로 올리고, 프론트 빌드 스테이지에서 그걸 받아 `openapi-generator-cli`나 `openapi-typescript`로 클라이언트 코드를 만든다.

```bash
# 프론트엔드 쪽
npx openapi-typescript ./openapi.json -o ./src/api/schema.ts
```

이 방식의 진짜 이점은 PR 단위로 스펙 변화가 추적된다는 점이다. `openapi.json`을 레포에 같이 커밋해 두면, 백엔드 PR 디프에 스펙 변경이 같이 잡힌다. 깨지는 변경(필드 제거, 타입 변경)을 리뷰어가 바로 본다. 다만 자동 생성 파일이라 머지 충돌이 자주 나서, 머지 직전에 다시 생성하고 커밋하는 흐름이 필요하다.

CI에서 스펙이 안 깨지는지 검증하는 단계도 같이 두면 좋다. 예전 `openapi.json`과 새로 생성한 걸 `oasdiff` 같은 도구로 비교해, 호환성 깨는 변경이 있으면 알림을 띄운다. 필드 삭제나 타입 변경은 무조건 잡아 주고, 추가는 통과시키는 식이다.


## 실무 트러블슈팅

코드를 고쳤는데 Swagger UI에는 옛 스키마가 그대로 보이는 일이 종종 있다. 거의 다 브라우저 캐시 문제다. `/docs-json`을 브라우저에서 직접 열어 보면 최신 스펙이 내려오는데 UI는 옛 걸 보여 주는 식이다. UI는 정적 자원(swagger-ui-bundle.js 등)을 브라우저 캐시에 강하게 물고 있다. 강력 새로고침(Cmd+Shift+R / Ctrl+F5)이나 시크릿 모드에서 한 번 더 확인한다. 그래도 안 바뀌면 백엔드를 안 재시작했을 가능성이 크다. `createDocument`는 bootstrap 시점에 한 번 만들어 메모리에 들고 있으므로, DTO를 바꾸고 핫리로드만으로는 스펙이 갱신 안 될 때가 있다. 프로세스를 완전히 재시작한다.

순환 참조 DTO도 자주 깨진다. `Order`가 `User`를 참조하고 `User`가 다시 `Order[]`를 가지는 구조 같은 경우다. `@ApiProperty({ type: () => User })`처럼 콜백으로 감싸 lazy 평가하면 클래스 정의 순서 문제는 해결되지만, JSON 스키마 자체에서도 무한 참조가 일어날 수 있다. 보통은 한쪽을 다른 DTO(예: `UserSummaryDto`, 필드 일부만 노출)로 끊는 게 정석이다. 응답에서까지 양방향 그래프를 그대로 노출할 일은 거의 없다.

`Date` 타입은 OpenAPI에서 직접 표현이 안 된다. JavaScript의 `Date`는 직렬화하면 ISO 문자열이 되므로, 문서에서도 `type: 'string', format: 'date-time'`으로 그리는 게 맞다. CLI 플러그인이 `Date` 타입을 보면 이걸 자동으로 처리해 주지만, 플러그인이 안 먹은 환경에서는 직접 적어 줘야 한다.

```typescript
@ApiProperty({ type: String, format: 'date-time', example: '2026-06-07T10:00:00.000Z' })
createdAt: Date;
```

`BigInt`는 더 까다롭다. `JSON.stringify`가 `BigInt`를 직접 직렬화하지 못해 런타임에 에러가 나고, OpenAPI에도 `bigint` 타입이 없다. 보통은 문자열로 직렬화하고 문서에도 `type: 'string'`으로 표시한다. 큰 ID나 금액에서 자주 마주치는 문제다.

```typescript
@ApiProperty({ type: String, example: '9007199254740993' })
@Transform(({ value }) => value.toString())
amount: bigint;
```

`@ApiProperty({ enum })`을 썼는데 UI에 enum 값이 안 나오거나 이상하게 나오는 경우가 있다. 원인은 두 가지다. 첫째, enum 객체 대신 enum 값 배열을 넘긴 경우다. `enum: [OrderStatus.PAID, OrderStatus.CANCELLED]`처럼 배열로 주면 값은 보이지만 enum 이름(스키마 컴포넌트로 추출되는 이름)이 안 잡힌다. `enum: OrderStatus, enumName: 'OrderStatus'`로 적어야 재사용 가능한 컴포넌트로 추출된다. 둘째, `const enum`을 쓴 경우다. TypeScript의 `const enum`은 컴파일 타임에 인라인돼 런타임 객체가 없다. Swagger가 못 읽어서 빈 값이 나온다. 일반 `enum`으로 바꾸거나, 별도 객체로 정의한다.

Decorator의 `description`이 마크다운으로 렌더링된다는 점은 의외로 잘 모른다. 줄바꿈, 코드블록, 링크 모두 동작한다. 복잡한 비즈니스 규칙을 문서에 박을 때 쓰인다. 다만 너무 길면 UI가 답답해진다. 두세 줄 넘어가는 설명은 별도 위키 페이지로 빼고 링크만 거는 게 보통이다.


## 정리하며 자주 쓰는 패턴

처음 Swagger를 붙일 때 시간을 가장 많이 잡아먹는 건 "문서가 비어 나오는" 문제다. 거의 다 `@ApiProperty` 누락이거나 제네릭/배열 타입 미명시다. CLI 플러그인을 먼저 켜두면 단순 필드는 자동으로 채워지니, 수동 작업은 제네릭 래퍼와 인증 표시 정도로 줄어든다.

마지막으로 운영 배포 전에 `/docs` 노출 여부를 반드시 확인한다. 환경 변수 분기를 넣었더라도 그 변수가 실제 운영 환경에서 올바른 값으로 설정돼 있는지까지 봐야 한다. `NODE_ENV`가 비어 있어서 분기가 안 먹는 경우가 종종 있다.
