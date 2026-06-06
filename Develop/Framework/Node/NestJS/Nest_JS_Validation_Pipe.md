---
title: NestJS ValidationPipe와 DTO 검증
tags: [nestjs, validation, class-validator, class-transformer, dto, pipe, node]
updated: 2026-06-06
---

# NestJS ValidationPipe와 DTO 검증

NestJS에서 검증을 처음 붙일 때는 `app.useGlobalPipes(new ValidationPipe())` 한 줄로 끝나는 것처럼 보인다. 그런데 실제로 쓰다 보면 "분명 `@IsNumber()`를 붙였는데 쿼리 파라미터가 문자열로 들어온다", "중첩 객체에 데코레이터를 다 달았는데 검증을 안 한다", "whitelist를 켰더니 멀쩡한 필드가 사라진다" 같은 문제를 줄줄이 만난다. 대부분 ValidationPipe의 옵션과 class-transformer의 변환 동작을 정확히 모르고 쓰기 때문이다.

이 문서는 검증 전용으로, ValidationPipe 옵션이 실제로 어떻게 동작하는지, 중첩 구조와 변환에서 어디서 막히는지를 실제로 겪은 순서대로 정리한다. 요청 처리 흐름 전반은 [Nest_JS_요청_라이프사이클.md](Nest_JS_요청_라이프사이클.md)를 참고한다.


## 검증의 두 라이브러리

NestJS의 ValidationPipe는 직접 검증 로직을 가지고 있지 않다. 실제 일은 두 라이브러리가 한다.

```bash
npm install class-validator class-transformer
```

`class-validator`는 DTO 클래스의 프로퍼티에 붙은 `@IsString()`, `@IsEmail()` 같은 데코레이터를 읽어서 값을 검사한다. `class-transformer`는 평범한 JSON 객체(plain object)를 DTO 클래스의 인스턴스로 바꿔주고, 그 과정에서 타입 변환을 한다. ValidationPipe는 이 둘을 순서대로 호출하는 얇은 래퍼다.

순서가 중요하다. 요청 본문은 처음에 그냥 `{ "age": "30" }` 같은 plain object다. ValidationPipe는 먼저 `plainToInstance`로 DTO 인스턴스를 만들고(transform), 그다음 `validate`로 검증한다. 변환이 검증보다 먼저 일어나기 때문에, 변환 옵션을 어떻게 주느냐에 따라 검증 결과가 완전히 달라진다. 이 순서를 머리에 넣고 있어야 뒤에 나오는 함정들이 이해된다.

```typescript
// DTO 정의
import { IsString, IsInt, Min, IsEmail } from 'class-validator';

export class CreateUserDto {
  @IsString()
  name: string;

  @IsEmail()
  email: string;

  @IsInt()
  @Min(0)
  age: number;
}
```

```typescript
// 컨트롤러
@Post()
create(@Body() dto: CreateUserDto) {
  // dto는 검증을 통과한 CreateUserDto 인스턴스
  return this.userService.create(dto);
}
```

ValidationPipe가 글로벌로 등록돼 있어야 `@Body()`에 붙은 DTO 타입을 보고 검증이 돈다. 등록은 보통 `main.ts`에서 한다.

```typescript
import { ValidationPipe } from '@nestjs/common';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalPipes(new ValidationPipe());
  await app.listen(3000);
}
```


## ValidationPipe 옵션 — 실제 동작 차이

옵션 이름만 보면 다 비슷해 보이는데, 켰을 때와 껐을 때 응답이 어떻게 달라지는지 직접 확인하지 않으면 감이 안 온다. 주요 옵션 네 개를 실제 입력/출력으로 비교한다.

### whitelist

`whitelist: true`는 DTO에 데코레이터가 붙은 프로퍼티만 남기고 나머지는 조용히 제거한다. 검증 데코레이터가 하나도 안 붙은 프로퍼티는 통째로 버려진다.

```typescript
app.useGlobalPipes(new ValidationPipe({ whitelist: true }));
```

```typescript
export class CreateUserDto {
  @IsString()
  name: string;

  @IsEmail()
  email: string;
  // role은 DTO에 없음
}
```

요청이 `{ "name": "kim", "email": "a@b.com", "role": "admin" }`로 들어오면, `role`은 조용히 사라지고 컨트롤러에는 `{ name, email }`만 도착한다. 권한 상승 같은 공격을 막는 데 쓴다. 클라이언트가 `isAdmin: true` 같은 필드를 끼워 넣어도 DTO에 없으면 그냥 버려진다.

여기서 자주 하는 실수가 있다. **데코레이터를 안 붙인 프로퍼티는 whitelist가 제거한다.** DTO에 분명히 선언했는데도 검증 데코레이터가 없으면 사라진다.

```typescript
export class CreateUserDto {
  @IsString()
  name: string;

  // 데코레이터를 깜빡함 → whitelist가 제거함
  description: string;
}
```

`description`을 보내도 컨트롤러에서는 `undefined`다. "분명 DTO에 있는데 값이 안 들어온다"는 신고가 들어오면 십중팔구 이 경우다. 검증이 필요 없어도 통과시키려면 `@Allow()`를 붙여야 한다.

```typescript
import { Allow } from 'class-validator';

export class CreateUserDto {
  @IsString()
  name: string;

  @Allow()
  description: string;
}
```

### forbidNonWhitelisted

`whitelist`가 모르는 필드를 조용히 버린다면, `forbidNonWhitelisted: true`는 모르는 필드가 있으면 400 에러를 던진다. `whitelist`와 같이 써야 의미가 있다.

```typescript
app.useGlobalPipes(new ValidationPipe({
  whitelist: true,
  forbidNonWhitelisted: true,
}));
```

위 DTO에 `role` 필드를 보내면 이제는 조용히 사라지지 않고 이렇게 막힌다.

```json
{
  "statusCode": 400,
  "message": ["property role should not exist"],
  "error": "Bad Request"
}
```

API 스펙을 엄격하게 강제하고 싶을 때 켠다. 오타로 `emial`을 보내면 바로 에러가 나서 클라이언트가 빨리 잡을 수 있다는 장점이 있다. 다만 클라이언트가 DTO에 없는 메타 필드(예: 추적용 `_trace`)를 습관적으로 붙이는 환경이면 멀쩡한 요청이 다 막히니, 켜기 전에 실제 트래픽을 한 번 확인해야 한다.

### transform

`transform: true`를 켜면 ValidationPipe가 검증을 통과한 plain object를 실제 DTO 클래스 인스턴스로 바꿔준다. 안 켜면 컨트롤러에 도착하는 값은 DTO 타입으로 선언돼 있어도 사실 그냥 object다.

```typescript
app.useGlobalPipes(new ValidationPipe({ transform: true }));
```

차이가 드러나는 지점은 두 가지다. 첫째, DTO에 메서드를 정의해 두고 컨트롤러에서 호출하는 경우 `transform`이 꺼져 있으면 그 메서드가 없어서 터진다.

```typescript
export class CreateUserDto {
  @IsString()
  name: string;

  getDisplayName(): string {
    return this.name.toUpperCase();
  }
}

@Post()
create(@Body() dto: CreateUserDto) {
  // transform: false면 dto는 plain object → getDisplayName is not a function
  return dto.getDisplayName();
}
```

둘째, 기본 타입 변환이다. `transform: true`면 `@IsInt()`가 붙은 프로퍼티에 `"30"`이 들어와도 숫자 `30`으로 바꿔준다. 이 부분은 뒤의 "string→number 변환 함정"에서 자세히 다룬다.

실무에서는 `transform: true`를 거의 항상 켠다. 켜지 않으면 타입 선언과 실제 런타임 값이 어긋나서 디버깅이 어려워진다.

### transformOptions

`transformOptions`는 `transform: true`일 때 class-transformer에 그대로 넘어가는 옵션이다. 여기서 가장 말썽인 게 `enableImplicitConversion`인데, 별도 절에서 다룬다. 자주 쓰는 다른 옵션은 `excludeExtraneousValues`다.

```typescript
app.useGlobalPipes(new ValidationPipe({
  transform: true,
  transformOptions: {
    enableImplicitConversion: true,
  },
}));
```

### stopAtFirstError

`stopAtFirstError: true`를 켜면 한 프로퍼티에 데코레이터가 여러 개 붙어 있을 때 첫 번째 실패에서 멈춘다. 기본값은 false라서 한 필드에 `@IsString()`, `@MinLength(8)`, `@Matches(/[A-Z]/)`이 다 붙어 있고 빈 값을 보내면 메시지 세 줄이 다 나간다.

```typescript
app.useGlobalPipes(new ValidationPipe({ stopAtFirstError: true }));
```

프론트에서 필드당 메시지를 하나만 띄우면 끄는 게 낫다. 메시지가 두세 줄 쌓이면 뭐가 먼저 잘못된 건지 알기 어렵다. 반대로 폼 전체에 결함을 한 번에 다 보여줘야 하면 끈 상태가 맞다. 사용자가 한 번 고치고 다시 보내는 식이라면 켜는 게 응답 크기와 가독성 모두 낫다.

### disableErrorMessages

운영 환경에서 에러 본문에 어떤 필드가 어떤 규칙으로 막혔는지 자세히 노출하면 공격자에게 DTO 구조를 알려주는 셈이 된다. `disableErrorMessages: true`로 메시지를 떼고 상태 코드만 내보낼 수 있다.

```typescript
app.useGlobalPipes(new ValidationPipe({
  disableErrorMessages: process.env.NODE_ENV === 'production',
}));
```

다만 메시지를 다 떼면 디버깅이 어렵다. 보통은 메시지를 다 끄지 않고 `exceptionFactory`로 필드명 정도만 일반화한 응답을 만든다. 내부 추적용 상세 메시지는 로깅에 남기고 응답에서는 뺀다.

### validationError 옵션

`validationError.target`과 `validationError.value`는 에러 객체에 원본 DTO 인스턴스와 입력 값을 포함할지 정한다. 기본값은 둘 다 true다.

```typescript
app.useGlobalPipes(new ValidationPipe({
  validationError: {
    target: false, // 원본 DTO 인스턴스 제거
    value: false,  // 입력 값 제거
  },
}));
```

기본값 그대로 두면 `ValidationError` 객체에 사용자가 보낸 비밀번호 같은 민감 값이 그대로 박혀서 로그나 에러 응답에 흘러간다. `exceptionFactory`에서 받은 `errors` 배열을 그대로 JSON으로 내보내면 사고가 난다. 둘 다 false로 끄거나, 응답을 만들 때 의식적으로 빼야 한다.

### forbidUnknownValues 주의

class-validator 0.14 이후 `forbidUnknownValues` 기본값이 true로 바뀌었다. 메타데이터가 없는 객체를 검증하려 하면 자동으로 거부한다. 의도된 보안 강화지만, 동적으로 만든 객체나 메타데이터 등록이 안 된 DTO를 검증하면 "an unknown value was passed to the validate function"으로 막힌다. NestJS 컨트롤러에서 `@Body() dto: CreateUserDto` 식으로 쓰면 메타데이터가 정상으로 붙어서 보통은 문제가 없는데, 동적 클래스나 외부에서 import한 DTO에서 가끔 터진다. 메시지가 모호하니 한 번이라도 본 적이 있어야 빨리 알아챈다.

### 운영에서 자주 쓰는 조합

실제로는 옵션을 개별로 켜기보다 아래 조합을 출발점으로 쓴다.

```typescript
app.useGlobalPipes(new ValidationPipe({
  whitelist: true,             // 모르는 필드 제거
  forbidNonWhitelisted: true,  // 모르는 필드 있으면 400
  transform: true,             // DTO 인스턴스로 변환
  transformOptions: {
    enableImplicitConversion: false, // 명시적 @Type을 강제 (이유는 아래)
  },
  stopAtFirstError: true,      // 필드당 첫 실패만 반환
  validationError: {
    target: false,             // 원본 DTO 인스턴스 응답 제외
    value: false,              // 입력 값 응답 제외 (민감정보 유출 방지)
  },
}));
```

`enableImplicitConversion`을 켜고 시작했다가 나중에 끄는 건 호환성 문제로 매우 어렵다. 처음부터 끄고 `@Type()`을 명시적으로 붙이는 쪽이 장기적으로 사고가 적다.


## string→number 변환 함정

가장 많이 묻는 문제가 이거다. POST 본문은 JSON이라 숫자가 숫자로 들어오지만, 쿼리 스트링과 URL 파라미터는 무조건 문자열이다. `?age=30`은 HTTP 레벨에서 `"30"`이지 `30`이 아니다.

```typescript
export class FindUsersDto {
  @IsInt()
  @Min(0)
  page: number;
}

@Get()
findAll(@Query() query: FindUsersDto) {
  return this.userService.find(query);
}
```

`/users?page=2`로 요청하면 `transform`을 안 켰을 때 이렇게 막힌다.

```json
{
  "statusCode": 400,
  "message": ["page must be an integer number"]
}
```

`page`가 `"2"`라는 문자열이라 `@IsInt()`를 통과 못 한다. 해결 방법은 두 가지다.

### 방법 1 — @Type으로 명시적 변환 (권장)

각 프로퍼티에 `@Type(() => Number)`를 붙여서 class-transformer에게 "이건 숫자로 바꿔라"라고 직접 알려준다.

```typescript
import { Type } from 'class-transformer';
import { IsInt, Min } from 'class-validator';

export class FindUsersDto {
  @Type(() => Number)
  @IsInt()
  @Min(0)
  page: number;

  @Type(() => Number)
  @IsInt()
  limit: number;
}
```

데코레이터 실행 순서상 `@Type`이 먼저 변환하고 `@IsInt`가 검증한다. 이제 `"2"`는 `2`로 바뀐 다음 검증을 통과한다. 이 방법은 변환 대상이 명시적이라 코드만 봐도 "이 필드는 숫자로 변환된다"는 게 보인다.

### 방법 2 — enableImplicitConversion

`@Type`을 일일이 붙이기 귀찮다면 `enableImplicitConversion: true`를 켜서 class-transformer가 DTO 프로퍼티의 TypeScript 타입을 보고 알아서 변환하게 할 수 있다.

```typescript
app.useGlobalPipes(new ValidationPipe({
  transform: true,
  transformOptions: { enableImplicitConversion: true },
}));
```

이렇게 하면 `@Type` 없이도 `page: number` 선언만 보고 `"2"`를 `2`로 변환한다. 편해 보이지만 부작용이 만만치 않다. 다음 절에서 다룬다.

### boolean 변환은 또 다른 함정

숫자보다 더 골치 아픈 게 boolean이다. 쿼리에서 `?active=false`로 보내면 값은 `"false"`라는 문자열인데, JavaScript에서 비어 있지 않은 문자열은 전부 truthy다. 그래서 `Boolean("false")`는 `true`다.

```typescript
// 잘못된 방법 — "false" 문자열이 true로 변환됨
@Type(() => Boolean)
@IsBoolean()
active: boolean;
```

`@Type(() => Boolean)`은 `Boolean()` 생성자를 쓰기 때문에 `"false"`도 `true`로 만든다. boolean은 `@Transform`으로 직접 변환 규칙을 써야 한다.

```typescript
import { Transform } from 'class-transformer';
import { IsBoolean } from 'class-validator';

export class FilterDto {
  @Transform(({ value }) => value === 'true' || value === true)
  @IsBoolean()
  active: boolean;
}
```

`?active=false`는 `false`로, `?active=true`는 `true`로 들어온다. 이 함정은 테스트를 문자열 `"true"`로만 하면 안 걸리고, `"false"`로 보내봐야 드러난다. 그래서 운영에 나가서야 "필터를 꺼도 안 꺼진다"는 신고로 발견되는 경우가 많다.

### 단일 파라미터는 전용 파이프를 쓴다

`@Query()`로 DTO 전체를 받지 않고 `@Param('id')` 하나만 받을 때는 NestJS가 제공하는 `ParseIntPipe`가 더 간단하다.

```typescript
@Get(':id')
findOne(@Param('id', ParseIntPipe) id: number) {
  // id는 number, 변환 실패하면 자동 400
  return this.userService.findOne(id);
}
```

`/users/abc`처럼 숫자가 아닌 값이 오면 ValidationPipe를 거치지 않고도 바로 400을 던진다. DTO를 만들 정도가 아닌 단일 값은 이쪽이 깔끔하다.


## enableImplicitConversion의 부작용

`enableImplicitConversion`은 처음엔 편하지만, 변환 규칙이 암묵적이라 예상 못 한 곳에서 값이 바뀐다. 운영에서 실제로 겪은 부작용들이다.

첫째, 숫자처럼 생긴 문자열을 강제로 숫자로 바꾼다. 우편번호나 전화번호처럼 앞자리 0이 의미 있는 값이 망가진다.

```typescript
export class AddressDto {
  @IsString()
  zipCode: string; // "01234"를 기대
}
```

`zipCode`를 `string`으로 선언했으니 안 바뀔 것 같지만, `enableImplicitConversion`은 TypeScript 타입을 보고 변환을 시도하다가 의도와 다른 결과를 낳는 경우가 있다. 특히 `@IsNumberString()` 같은 데코레이터를 섞어 쓰면 변환 시점과 검증 시점이 엇갈려서 디버깅이 어렵다.

둘째, `number`로 선언했는데 빈 문자열이나 잘못된 값이 오면 `NaN`으로 변환되고, `@IsInt()`가 그제서야 막는다. 변환은 조용히 일어나고 검증 메시지만 떠서 원인을 추적하기 번거롭다.

```typescript
// ?page= (빈 값) → NaN으로 변환 → "page must be an integer" 에러
@IsInt()
page: number;
```

셋째, 가장 까다로운 건 배열이다. 쿼리에서 `?ids=1`처럼 값이 하나만 오면 배열이 아니라 단일 값으로 들어오는데, `enableImplicitConversion`이 이걸 일관성 없게 처리한다. `?ids=1&ids=2`는 배열인데 `?ids=1`은 문자열이라, 같은 코드가 입력 개수에 따라 다르게 동작한다.

결론은 명확하다. 새 프로젝트면 `enableImplicitConversion`을 끄고 `@Type()`을 명시적으로 붙인다. 변환 규칙이 코드에 드러나서 리뷰와 디버깅이 훨씬 쉽다. 이미 켜서 운영 중이면 함부로 끄지 말고, DTO마다 `@Type`을 다 붙인 뒤 충분히 테스트하고 끈다.


## 중첩 객체·배열 검증

DTO 안에 또 다른 객체가 있을 때가 진짜 함정이다. 가장 흔한 실수는 중첩 객체에 검증이 안 도는데도 그걸 모르고 넘어가는 것이다.

```typescript
class AddressDto {
  @IsString()
  city: string;

  @IsString()
  zipCode: string;
}

export class CreateUserDto {
  @IsString()
  name: string;

  // 이렇게만 쓰면 address 내부는 검증되지 않는다
  address: AddressDto;
}
```

`address`에 `{ city: 123, zipCode: null }` 같은 엉터리 값을 넣어도 검증을 통과한다. class-validator는 중첩 객체를 자동으로 파고들지 않는다. 명시적으로 두 개를 붙여야 한다.

```typescript
import { ValidateNested } from 'class-validator';
import { Type } from 'class-transformer';

export class CreateUserDto {
  @IsString()
  name: string;

  @ValidateNested()
  @Type(() => AddressDto)
  address: AddressDto;
}
```

`@ValidateNested()`는 "이 프로퍼티 안으로 들어가서 검증하라"는 표시고, `@Type(() => AddressDto)`는 plain object를 `AddressDto` 인스턴스로 바꾸라는 지시다. **둘 다 필요하다.** `@Type`이 없으면 plain object 상태라 데코레이터 메타데이터를 못 읽어서 중첩 검증이 안 돈다. 한쪽만 붙이면 조용히 검증을 건너뛰는데, 에러도 안 나서 한참 뒤에 발견된다.

### 객체 배열

배열 안에 객체가 있으면 `@ValidateNested`에 `{ each: true }`를 줘야 각 요소를 검증한다.

```typescript
export class CreateOrderDto {
  @ValidateNested({ each: true })
  @Type(() => OrderItemDto)
  items: OrderItemDto[];
}

class OrderItemDto {
  @IsString()
  productId: string;

  @IsInt()
  @Min(1)
  quantity: number;
}
```

`each: true`를 빼먹으면 배열 자체는 통과하지만 각 요소 내부는 검증을 안 한다. `items: [{ quantity: -5 }]` 같은 값이 그대로 들어온다. 배열 검증이 안 도는 것 같으면 가장 먼저 `each: true`를 확인한다.

배열 자체에 대한 제약(빈 배열 금지, 최대 개수 등)은 별도 데코레이터로 건다.

```typescript
import { ArrayNotEmpty, ArrayMaxSize } from 'class-validator';

export class CreateOrderDto {
  @ArrayNotEmpty()
  @ArrayMaxSize(100)
  @ValidateNested({ each: true })
  @Type(() => OrderItemDto)
  items: OrderItemDto[];
}
```

### 중첩 검증 에러 메시지

중첩 검증이 실패하면 에러 구조가 평면적이지 않고 `children`으로 중첩된다. 프론트에 그대로 내려주면 어느 필드가 틀렸는지 알기 어렵다.

```json
{
  "message": [
    "items.0.quantity must not be less than 1"
  ]
}
```

ValidationPipe가 기본으로 `items.0.quantity` 형태로 경로를 펼쳐주긴 하는데, 더 다듬고 싶으면 `exceptionFactory` 옵션으로 에러를 직접 가공한다. 이건 뒤의 커스텀 처리에서 다룬다.


## 커스텀 밸리데이터 — @ValidatorConstraint

class-validator의 기본 데코레이터로 안 되는 검증이 있다. 비밀번호 확인 필드가 비밀번호와 같은지, 시작일이 종료일보다 앞인지처럼 다른 필드를 참조하는 검증이 대표적이다. 이럴 때 `@ValidatorConstraint`로 직접 만든다.

```typescript
import {
  ValidatorConstraint,
  ValidatorConstraintInterface,
  ValidationArguments,
  registerDecorator,
  ValidationOptions,
} from 'class-validator';

@ValidatorConstraint({ name: 'isMatch', async: false })
export class IsMatchConstraint implements ValidatorConstraintInterface {
  validate(value: any, args: ValidationArguments): boolean {
    const [relatedPropertyName] = args.constraints;
    const relatedValue = (args.object as any)[relatedPropertyName];
    return value === relatedValue;
  }

  defaultMessage(args: ValidationArguments): string {
    const [relatedPropertyName] = args.constraints;
    return `${args.property}이(가) ${relatedPropertyName}와 일치하지 않습니다`;
  }
}

// 데코레이터로 감싸기
export function IsMatch(property: string, options?: ValidationOptions) {
  return function (object: object, propertyName: string) {
    registerDecorator({
      target: object.constructor,
      propertyName,
      options,
      constraints: [property],
      validator: IsMatchConstraint,
    });
  };
}
```

```typescript
export class ResetPasswordDto {
  @IsString()
  @MinLength(8)
  password: string;

  @IsMatch('password', { message: '비밀번호가 일치하지 않습니다' })
  passwordConfirm: string;
}
```

`args.object`로 같은 DTO의 다른 프로퍼티에 접근할 수 있다는 게 핵심이다. `constraints` 배열에 비교 대상 필드명을 넣어두면 `validate`에서 꺼내 쓴다.

### DB 조회가 필요한 비동기 검증

이메일 중복 확인처럼 DB를 봐야 하는 검증은 `async: true`로 만든다. 단, 검증 클래스에서 DI(서비스 주입)를 쓰려면 NestJS의 컨테이너에 등록하는 한 단계가 더 필요하다.

```typescript
import { Injectable } from '@nestjs/common';

@ValidatorConstraint({ name: 'isEmailUnique', async: true })
@Injectable()
export class IsEmailUniqueConstraint implements ValidatorConstraintInterface {
  constructor(private readonly userService: UserService) {}

  async validate(email: string): Promise<boolean> {
    const user = await this.userService.findByEmail(email);
    return !user;
  }

  defaultMessage(): string {
    return '이미 사용 중인 이메일입니다';
  }
}
```

`@Injectable()`만 붙인다고 주입이 되는 게 아니다. `main.ts`에서 `useContainer`를 호출해 class-validator가 NestJS 컨테이너를 쓰도록 연결해야 한다.

```typescript
import { useContainer } from 'class-validator';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  useContainer(app.select(AppModule), { fallbackOnErrors: true });
  app.useGlobalPipes(new ValidationPipe());
  await app.listen(3000);
}
```

그리고 제약 클래스를 모듈의 `providers`에 등록해야 한다. 이 단계를 빼먹으면 `Cannot read properties of undefined`로 터지는데, 에러 메시지가 원인을 직접 가리키지 않아서 처음엔 한참 헤맨다. `useContainer` 호출과 `providers` 등록, 둘 다 했는지 먼저 확인한다.

비동기 검증을 쓸 때 한 가지 더. DB 조회 검증을 DTO에 너무 많이 박으면 요청 하나에 쿼리가 여러 번 나간다. 검증 단계의 중복 체크는 "빠른 실패"용으로만 쓰고, 실제 정합성은 DB의 unique 제약과 트랜잭션으로 잡는 게 안전하다. 검증을 통과해도 그 사이에 같은 이메일이 등록될 수 있는 경쟁 상태가 남기 때문이다.


## @IsCustom — 함수형 커스텀 데코레이터

`@ValidatorConstraint` 클래스를 매번 만드는 게 부담스러우면 `registerDecorator` 한 번으로 끝낼 수 있다. 단순한 정규식 검증이나 한 줄짜리 로직은 함수형이 훨씬 짧다. 패턴을 알고 있으면 새 검증 규칙을 5분 안에 만들어 쓴다.

기본 형태는 검증 함수와 메시지를 인자로 받는 데코레이터 팩토리다.

```typescript
import { registerDecorator, ValidationOptions } from 'class-validator';

export function IsCustom<T = any>(
  validator: (value: T) => boolean,
  message: string,
  options?: ValidationOptions,
) {
  return function (object: object, propertyName: string) {
    registerDecorator({
      name: 'isCustom',
      target: object.constructor,
      propertyName,
      options: { message, ...options },
      validator: {
        validate: (value: T) => validator(value),
      },
    });
  };
}
```

```typescript
export class ProductDto {
  @IsCustom<string>(
    (v) => /^SKU-\d{6}$/.test(v),
    'SKU는 "SKU-숫자6자리" 형식이어야 합니다',
  )
  sku: string;

  @IsCustom<number>(
    (v) => v % 100 === 0,
    '가격은 100원 단위여야 합니다',
  )
  price: number;
}
```

검증 로직이 한 줄이면 이걸로 충분하다. 다른 필드를 참조해야 하거나 비동기 호출이 필요한 검증만 `@ValidatorConstraint` 클래스 방식으로 만든다.

### 도메인 특화 데코레이터로 묶기

같은 규칙을 여러 DTO에서 반복하면 도메인 이름으로 감싼다. 정규식이나 비즈니스 룰을 한 곳에 모아두면 변경할 때 한 군데만 고친다.

```typescript
export function IsKoreanPhone(options?: ValidationOptions) {
  return IsCustom<string>(
    (v) => /^01[0-9]-?\d{3,4}-?\d{4}$/.test(v),
    '올바른 휴대전화 번호가 아닙니다',
    options,
  );
}

export function IsBusinessNumber(options?: ValidationOptions) {
  return IsCustom<string>(
    (v) => /^\d{3}-?\d{2}-?\d{5}$/.test(v),
    '사업자 등록번호 형식이 아닙니다',
    options,
  );
}
```

```typescript
export class SignupDto {
  @IsKoreanPhone()
  phone: string;

  @IsBusinessNumber()
  businessNumber: string;
}
```

데코레이터 이름이 곧 문서 역할을 한다. DTO만 봐도 어떤 형식을 기대하는지 읽힌다.

### 옵션을 받는 데코레이터

길이나 범위처럼 파라미터가 필요한 데코레이터도 같은 패턴으로 만든다.

```typescript
export function IsDivisibleBy(divisor: number, options?: ValidationOptions) {
  return function (object: object, propertyName: string) {
    registerDecorator({
      name: 'isDivisibleBy',
      target: object.constructor,
      propertyName,
      constraints: [divisor],
      options: { message: `${divisor}의 배수여야 합니다`, ...options },
      validator: {
        validate: (value: number, args) => value % args.constraints[0] === 0,
      },
    });
  };
}

export class OrderDto {
  @IsDivisibleBy(10)
  quantity: number;
}
```

`constraints` 배열에 값을 넣어두고 `validate`의 두 번째 인자 `args.constraints`에서 꺼낸다. 이렇게 분리해야 같은 데코레이터를 다른 값으로 여러 번 쓸 수 있다.


## @Transform으로 변환 직접 제어

`@Type`은 클래스 단위로 변환할 때 쓰고, 그것보다 세밀한 변환은 `@Transform`을 쓴다. `@Transform`은 콜백 안에서 원본 값을 마음대로 가공할 수 있다.

```typescript
import { Transform } from 'class-transformer';

export class UserDto {
  // 앞뒤 공백 제거 + 소문자
  @Transform(({ value }) => value?.trim().toLowerCase())
  @IsEmail()
  email: string;

  // 콤마 구분 문자열을 배열로
  @Transform(({ value }) =>
    typeof value === 'string' ? value.split(',').map((s) => s.trim()) : value,
  )
  @IsArray()
  tags: string[];
}
```

쿼리에서 `?tags=red,green,blue`로 받아 배열로 다루고 싶을 때 자주 쓴다. boolean 변환도 `@Transform`이 답이라는 건 앞에서 봤다.

주의할 점은 `@Transform`이 `plainToInstance` 단계에서 실행된다는 것이다. 그러니까 검증 전에 값이 이미 가공된 상태다. 변환에서 예외를 던지면 검증 메시지가 아니라 변환 오류로 500이 날 수 있으니, 콜백 안에서는 가능한 한 안전하게 처리하고 잘못된 값은 원본 그대로 돌려주는 편이 낫다. 그러면 검증 단계에서 잡힌다.

```typescript
@Transform(({ value }) => {
  // 잘못된 형태면 변환 안 하고 그대로 반환 → @IsArray에서 잡힘
  if (typeof value !== 'string') return value;
  return value.split(',').map((s) => s.trim());
})
@IsArray()
tags: string[];
```


## 커스텀 파이프 구현

ValidationPipe로 안 되는 변환·검증은 직접 파이프를 만든다. 파이프는 `PipeTransform` 인터페이스를 구현하면 된다. 자주 만드는 건 특정 형식 검증이나 도메인 값 변환이다.

```typescript
import {
  PipeTransform,
  Injectable,
  ArgumentMetadata,
  BadRequestException,
} from '@nestjs/common';

@Injectable()
export class ParseObjectIdPipe implements PipeTransform<string, string> {
  transform(value: string, metadata: ArgumentMetadata): string {
    if (!/^[0-9a-fA-F]{24}$/.test(value)) {
      throw new BadRequestException('올바른 ID 형식이 아닙니다');
    }
    return value;
  }
}
```

```typescript
@Get(':id')
findOne(@Param('id', ParseObjectIdPipe) id: string) {
  return this.service.findOne(id);
}
```

`transform`의 두 번째 인자 `metadata`에는 파라미터가 어디서 왔는지(`body`, `query`, `param`), 어떤 타입인지가 들어 있다. 이걸 보고 분기할 수 있다.

```typescript
transform(value: any, metadata: ArgumentMetadata) {
  console.log(metadata.type);     // 'body' | 'query' | 'param' | 'custom'
  console.log(metadata.metatype); // 선언된 타입 (String, Number, CreateUserDto ...)
  return value;
}
```

파이프를 만들 때 헷갈리는 게 적용 범위다. 파라미터에 직접 붙이면(`@Param('id', ParseObjectIdPipe)`) 그 파라미터에만 적용된다. 컨트롤러나 글로벌에 붙이면 모든 파라미터를 거치는데, 이때 `metadata.metatype`을 보고 처리할 대상만 골라야 엉뚱한 값까지 건드리지 않는다.

### exceptionFactory로 에러 응답 통일

ValidationPipe의 기본 에러 응답은 메시지가 문자열 배열로 나간다. 프론트에서 필드별로 매핑하려면 형식을 바꾸는 게 낫다. 파이프를 새로 만들 필요 없이 `exceptionFactory` 옵션으로 가공한다.

```typescript
import { ValidationPipe, BadRequestException } from '@nestjs/common';
import { ValidationError } from 'class-validator';

app.useGlobalPipes(
  new ValidationPipe({
    whitelist: true,
    transform: true,
    exceptionFactory: (errors: ValidationError[]) => {
      const formatted = errors.map((err) => ({
        field: err.property,
        messages: Object.values(err.constraints ?? {}),
      }));
      return new BadRequestException({
        statusCode: 400,
        error: 'ValidationError',
        details: formatted,
      });
    },
  }),
);
```

이러면 응답이 `details: [{ field, messages }]` 형태로 나가서 프론트가 필드별로 에러를 띄우기 쉽다. 다만 중첩 객체일 때 `errors`도 `children`을 가지므로, 깊은 구조까지 평탄화하려면 재귀로 펼쳐야 한다.

### 중첩 에러 평탄화

중첩 검증이 실패하면 `ValidationError`는 트리 구조다. `address.city`가 실패하면 최상위 에러의 `property`는 `address`이고 `children[0].property`가 `city`다. 위 코드는 최상위만 보니 중첩 정보가 사라진다. 재귀로 펼쳐서 `address.city` 같은 경로 문자열을 만든다.

```typescript
function flattenErrors(
  errors: ValidationError[],
  parentPath = '',
): Array<{ field: string; messages: string[] }> {
  return errors.flatMap((err) => {
    const path = parentPath ? `${parentPath}.${err.property}` : err.property;
    const own = err.constraints
      ? [{ field: path, messages: Object.values(err.constraints) }]
      : [];
    const nested = err.children?.length
      ? flattenErrors(err.children, path)
      : [];
    return [...own, ...nested];
  });
}

app.useGlobalPipes(
  new ValidationPipe({
    exceptionFactory: (errors) => new BadRequestException({
      statusCode: 400,
      error: 'ValidationError',
      details: flattenErrors(errors),
    }),
  }),
);
```

`items: [{ quantity: -5 }]`처럼 배열 안 객체가 실패하면 `field`가 `items.0.quantity`로 나간다. 점 표기법이 일관돼서 프론트 폼 라이브러리(react-hook-form 등)와 그대로 매핑된다.

배열 인덱스를 `[0]` 형태로 받고 싶다면 평탄화 함수에서 부모 경로가 배열 자식일 때 형식을 바꿔주면 된다. 다만 표기를 자주 바꾸면 클라이언트 코드와 어긋날 수 있으니 한 번 정한 형식을 유지하는 편이 낫다.

### 에러 코드 추가 — i18n과 클라이언트 분기

메시지 문자열만 내려보내면 다국어 처리나 분기가 어렵다. 데코레이터의 `message`에 코드 형식을 박아두거나, 별도의 코드 매핑을 두는 방식이 있다.

```typescript
export class CreateUserDto {
  @IsEmail({}, { message: 'INVALID_EMAIL' })
  email: string;

  @MinLength(8, { message: 'PASSWORD_TOO_SHORT' })
  password: string;
}
```

응답에는 `INVALID_EMAIL` 같은 코드를 그대로 내보내고, 프론트가 코드를 보고 자국어 메시지로 매핑한다. 코드 네이밍 규칙(전부 대문자 SNAKE_CASE)을 정해두면 메시지인지 코드인지 한눈에 구분된다.

비교적 단순한 방식이지만, 검증 데코레이터마다 `message`를 다 채워야 하는 부담이 있다. 데코레이터별로 기본 코드를 추론하는 매핑 함수를 만들어 `exceptionFactory`에서 일괄 처리하는 방법도 있다.

```typescript
function toCode(constraintKey: string): string {
  // constraintKey는 'isEmail', 'minLength' 같은 class-validator 내부 키
  return constraintKey.replace(/([A-Z])/g, '_$1').toUpperCase();
  // 'isEmail' → 'IS_EMAIL'
}

const details = errors.flatMap((err) =>
  Object.entries(err.constraints ?? {}).map(([key, msg]) => ({
    field: err.property,
    code: toCode(key),
    message: msg,
  })),
);
```

이러면 데코레이터에 `message`를 안 써도 `IS_EMAIL`, `MIN_LENGTH` 같은 코드가 자동으로 나간다. 단, class-validator 내부 키 이름이 버전 사이에 바뀌면 코드도 바뀌므로, 응답 스펙으로 굳히기 전에 한 번 점검해야 한다.


## 그룹 검증과 부분 업데이트

같은 DTO를 생성과 수정에 같이 쓰려다 보면 검증 규칙이 충돌한다. 생성 때는 모든 필드가 필수인데 수정(PATCH) 때는 일부만 보내기 때문이다. 두 가지 접근이 있다.

### PartialType

`@nestjs/mapped-types`(또는 `@nestjs/swagger`)의 `PartialType`은 기존 DTO의 모든 필드를 optional로 만든 새 DTO를 만들어준다.

```typescript
import { PartialType } from '@nestjs/mapped-types';

export class UpdateUserDto extends PartialType(CreateUserDto) {}
```

`UpdateUserDto`는 `CreateUserDto`의 검증 규칙을 그대로 가지되 모든 필드가 선택이라, PATCH에서 일부만 보내도 통과한다. 보낸 필드는 여전히 원래 규칙(`@IsEmail()` 등)으로 검증된다. 대부분의 부분 업데이트는 이걸로 충분하다.

### 검증 그룹

같은 필드라도 상황에 따라 다른 규칙을 적용해야 하면 `groups`를 쓴다.

```typescript
export class UserDto {
  @IsString({ groups: ['create', 'update'] })
  name: string;

  @IsEmail({ groups: ['create'] }) // 생성 때만 검증
  email: string;
}
```

```typescript
@Post()
create(@Body(new ValidationPipe({ groups: ['create'] })) dto: UserDto) {}

@Patch()
update(@Body(new ValidationPipe({ groups: ['update'] })) dto: UserDto) {}
```

그룹은 강력하지만 DTO가 복잡해지고 어느 그룹이 어디서 도는지 추적이 어려워진다. 단순한 부분 업데이트면 `PartialType`을 먼저 고려하고, 그룹은 정말 필드별 규칙이 상황마다 갈릴 때만 쓴다.


## 검증 테스트

검증 규칙은 코드보다 의도가 미묘하다. "전화번호 형식이 바뀌면 어디서 막아야 하지"를 6개월 뒤에 다시 보면 기억이 안 난다. DTO 검증에 단위 테스트를 붙여두면 규칙이 문서 역할을 한다.

`validate` 함수를 직접 호출해서 검증한다. ValidationPipe까지 안 거치고 class-validator만 쓰면 된다.

```typescript
import { plainToInstance } from 'class-transformer';
import { validate } from 'class-validator';
import { CreateUserDto } from './create-user.dto';

describe('CreateUserDto', () => {
  it('정상 값은 통과한다', async () => {
    const dto = plainToInstance(CreateUserDto, {
      name: 'kim',
      email: 'a@b.com',
      age: 30,
    });
    const errors = await validate(dto);
    expect(errors).toHaveLength(0);
  });

  it('이메일 형식이 아니면 IS_EMAIL 제약에서 막힌다', async () => {
    const dto = plainToInstance(CreateUserDto, {
      name: 'kim',
      email: 'not-an-email',
      age: 30,
    });
    const errors = await validate(dto);
    expect(errors).toHaveLength(1);
    expect(errors[0].constraints).toHaveProperty('isEmail');
  });
});
```

`plainToInstance`로 DTO 인스턴스를 만들어야 데코레이터가 동작한다. 그냥 객체 리터럴로 만들면 메타데이터가 안 붙어서 검증이 안 돈다. 이 한 줄을 빼먹고 "왜 에러가 0개야"라고 헤매는 경우가 흔하다.

ValidationPipe 단위로 테스트하고 싶으면 파이프를 직접 인스턴스화해서 `transform` 메서드를 호출한다.

```typescript
import { ValidationPipe, BadRequestException } from '@nestjs/common';

describe('ValidationPipe + CreateUserDto', () => {
  const pipe = new ValidationPipe({
    whitelist: true,
    transform: true,
    forbidNonWhitelisted: true,
  });

  const metadata = {
    type: 'body' as const,
    metatype: CreateUserDto,
    data: '',
  };

  it('whitelist에 없는 필드를 보내면 거부한다', async () => {
    await expect(
      pipe.transform({ name: 'kim', email: 'a@b.com', age: 30, isAdmin: true }, metadata),
    ).rejects.toThrow(BadRequestException);
  });

  it('숫자 문자열은 number로 변환된다', async () => {
    const result = await pipe.transform(
      { name: 'kim', email: 'a@b.com', age: '30' },
      metadata,
    );
    expect(typeof result.age).toBe('number');
  });
});
```

이런 테스트가 있으면 ValidationPipe 옵션을 손댈 때 어떤 규칙이 깨지는지 즉시 잡힌다. 특히 `enableImplicitConversion` 같은 전역 옵션을 바꾸기 전에 테스트가 어떻게 깨지는지 보면 영향 범위가 명확해진다. 이 부분은 [Nest_JS_테스트.md](Nest_JS_테스트.md)에서 더 다룬다.


## 자주 막히는 지점 정리

직접 겪으면서 정리한, 검증이 "안 되는 것처럼 보이는" 원인들이다.

검증 자체가 아예 안 돈다면 ValidationPipe를 글로벌로 등록했는지부터 본다. `app.useGlobalPipes`를 빼먹으면 데코레이터를 아무리 붙여도 조용히 통과한다. 특정 컨트롤러만 안 된다면 그 핸들러에 다른 파이프를 직접 붙여서 글로벌 파이프를 덮어쓰지 않았는지 확인한다.

DTO를 인터페이스로 선언하면 검증이 안 된다. class-validator는 런타임에 클래스 메타데이터를 읽기 때문에, `interface`로 만들면 컴파일 후 타입 정보가 사라져서 검증할 게 없다. 반드시 `class`로 선언한다.

`tsconfig.json`에 `emitDecoratorMetadata`와 `experimentalDecorators`가 켜져 있어야 한다. 둘 중 하나라도 꺼져 있으면 `@Type` 같은 데코레이터가 타입 정보를 못 읽어서 변환이 안 된다. NestJS 기본 설정에는 켜져 있지만, 설정을 직접 손대다 끄는 경우가 있다.

쿼리/파라미터 변환이 안 되면 `transform: true`와 `@Type(() => Number)`를 같이 썼는지 본다. 둘 중 하나만으로는 안 될 때가 있다.

중첩 객체 검증이 건너뛰어지면 `@ValidateNested()`와 `@Type()`이 둘 다 있는지, 배열이면 `{ each: true }`까지 있는지 확인한다.

"an unknown value was passed to the validate function"이라는 알 수 없는 에러가 뜨면 class-validator 0.14 이후의 `forbidUnknownValues` 기본값 변경이 원인일 가능성이 높다. NestJS DTO가 정상적으로 메타데이터를 갖고 있는지(클래스인지, `tsconfig`의 데코레이터 옵션이 켜져 있는지) 먼저 확인한다.

비동기 검증(`async: true`)이 안 돌면 `useContainer` 호출과 제약 클래스의 `providers` 등록을 빼먹지 않았는지 본다. 메시지가 원인을 안 가리켜서 가장 헤매기 쉬운 지점이다.

검증 에러 응답에 비밀번호 같은 민감 값이 그대로 박혀 나가면 `validationError.target`과 `validationError.value`를 false로 설정한 뒤 다시 본다. 기본값은 둘 다 true라서 입력 값이 응답으로 흘러간다.
