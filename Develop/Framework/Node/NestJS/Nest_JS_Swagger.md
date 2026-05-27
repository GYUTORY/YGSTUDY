---
title: NestJS Swagger로 API 문서 자동화
tags: [nestjs, swagger, openapi, api-docs, dto, node]
updated: 2026-05-27
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


## 정리하며 자주 쓰는 패턴

처음 Swagger를 붙일 때 시간을 가장 많이 잡아먹는 건 "문서가 비어 나오는" 문제다. 거의 다 `@ApiProperty` 누락이거나 제네릭/배열 타입 미명시다. CLI 플러그인을 먼저 켜두면 단순 필드는 자동으로 채워지니, 수동 작업은 제네릭 래퍼와 인증 표시 정도로 줄어든다.

마지막으로 운영 배포 전에 `/docs` 노출 여부를 반드시 확인한다. 환경 변수 분기를 넣었더라도 그 변수가 실제 운영 환경에서 올바른 값으로 설정돼 있는지까지 봐야 한다. `NODE_ENV`가 비어 있어서 분기가 안 먹는 경우가 종종 있다.
