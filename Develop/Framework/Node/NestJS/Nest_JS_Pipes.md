---
title: NestJS Pipes
tags:
  - nestjs
  - pipes
  - parsepipe
  - transform
  - validation
  - node
updated: 2026-06-02
---

# NestJS Pipes

Pipe는 컨트롤러 핸들러에 도달하기 직전에 인자를 가로채는 컴포넌트다. 입력값을 변환하거나(transform), 입력값이 조건을 만족하는지 검사한다(validate). 두 역할 모두 가능하지만 한 파이프 안에서 두 가지를 다 하지는 않는 게 깔끔하다. `ParseIntPipe`는 변환만 하고, `ValidationPipe`는 검증과 변환을 같이 한다.

처음 보면 데코레이터 하나 더 붙이는 정도로 보이지만, 실제로 다루다 보면 헷갈리는 지점이 많다. "왜 `@Query('page', ParseIntPipe)`는 되는데 `@Body()`에 붙이면 안 도는 것처럼 보이지", "글로벌로 ValidationPipe를 등록해 두면 ParseIntPipe와 충돌하나", "ParseArrayPipe로 쿼리스트링 배열을 받았는데 `items=1`처럼 단일 값이 오면 왜 터지지" 같은 문제가 줄줄이 나온다. 대부분 파이프의 실행 시점과 적용 범위, 그리고 빌트인 파이프의 내부 동작을 모르고 쓰기 때문이다.

이 문서는 ValidationPipe 단독 주제는 [Nest_JS_Validation_Pipe.md](Nest_JS_Validation_Pipe.md)에 분리해 두고, 그 외 일반 파이프 전반을 다룬다.


## 파이프의 자리 — 언제 실행되는가

NestJS 요청 처리 흐름에서 파이프는 Guard 이후, 핸들러 직전에 실행된다.

```
Request
  └─ Middleware
       └─ Guard
            └─ Interceptor (before)
                 └─ Pipe        ← 여기
                      └─ Handler
                 └─ Interceptor (after)
                      └─ Exception Filter
                           └─ Response
```

순서가 중요하다. Guard가 통과시킨 요청만 파이프에 도달한다. 그래서 인증·인가는 Guard에서 끝내고, 파이프에서는 입력값의 형식과 유효성만 본다. 두 책임이 섞이면 디버깅이 어려워진다.

또 하나 자주 헷갈리는 점이 있다. 파이프는 **핸들러의 인자 단위로 실행된다.** 컨트롤러 메서드에 인자가 세 개 있으면 각 인자에 대해 파이프가 별도로 돈다. `@Param('id', ParseIntPipe)`는 `id` 하나만 보고, 다른 인자는 손대지 않는다. 이 점이 미들웨어와 가장 큰 차이다. 미들웨어는 `req.body` 전체를 다루지만, 파이프는 `@Body()`로 꺼낸 값 하나, `@Param('id')`로 꺼낸 값 하나를 본다.

이런 인자 단위 동작 때문에 파이프는 데코레이터의 두 번째 인자로 넘기는 패턴이 가장 흔하다.

```typescript
@Get(':id')
findOne(@Param('id', ParseIntPipe) id: number) {
  return this.userService.findOne(id);
}
```

위 예에서 파이프가 받는 값은 라우트 파라미터 `id`의 문자열이고, 파이프가 반환하는 값은 핸들러 인자 `id`로 들어간다. 파이프가 던지는 예외는 핸들러 호출 전이라 비즈니스 로직이 아예 안 돈다.


## 빌트인 파이프

NestJS는 자주 쓰는 변환·검증을 미리 만들어 둔 빌트인 파이프를 제공한다. `@nestjs/common`에서 직접 import 한다.

### ParseIntPipe

가장 많이 쓰는 파이프다. 문자열을 정수로 변환하고, 변환에 실패하면 400 에러를 던진다.

```typescript
@Get(':id')
findOne(@Param('id', ParseIntPipe) id: number) {
  return id; // number 타입 보장
}
```

`/users/abc`로 요청이 오면 이렇게 막힌다.

```json
{
  "statusCode": 400,
  "message": "Validation failed (numeric string is expected)",
  "error": "Bad Request"
}
```

조심할 점이 있다. `ParseIntPipe`는 내부적으로 `parseInt`가 아니라 `Number()` 변환과 정규식 체크를 같이 한다. `"30abc"`처럼 일부만 숫자인 문자열도 거른다. 또 빈 문자열 `""`도 막는다. 단, `0`은 통과한다. "0이 들어오면 거부하고 싶다"는 요구가 있으면 별도 검증을 추가해야 한다.

옵션을 주려면 클래스가 아니라 인스턴스로 넘긴다.

```typescript
@Get(':id')
findOne(
  @Param('id', new ParseIntPipe({ errorHttpStatusCode: HttpStatus.NOT_ACCEPTABLE }))
  id: number,
) {
  return id;
}
```

`errorHttpStatusCode`는 변환 실패 시 응답 상태 코드를 바꾸고, `exceptionFactory`는 던지는 예외 자체를 교체한다. API 응답 포맷을 통일하려면 `exceptionFactory`로 커스텀 예외를 던지는 패턴이 깔끔하다.

### ParseFloatPipe

`ParseIntPipe`의 실수 버전이다. 동작 방식과 옵션은 동일하다. 가격, 좌표, 비율처럼 정수가 아닌 숫자가 쿼리로 올 때 쓴다.

```typescript
@Get('search')
nearby(
  @Query('lat', ParseFloatPipe) lat: number,
  @Query('lng', ParseFloatPipe) lng: number,
) {
  return this.placeService.findNearby(lat, lng);
}
```

내부 변환은 `parseFloat`이 아닌 `Number()`로 한다. 그래서 `"1.5e2"` 같은 지수 표기도 통과한다. 의도와 다른 입력을 막고 싶으면 별도 검증을 붙여야 한다.

### ParseBoolPipe

문자열 `"true"`, `"false"`, `"1"`, `"0"`을 boolean으로 변환한다. 쿼리스트링은 무조건 문자열로 오기 때문에 `?active=true`를 받으면 그냥은 `"true"` 문자열이 들어온다.

```typescript
@Get()
list(@Query('active', ParseBoolPipe) active: boolean) {
  return this.userService.list({ active });
}
```

여기서 한 가지 함정이 있다. `?active=yes`나 `?active=on` 같은 폼 입력 스타일은 거부한다. 정확히 위 네 값(true/false/1/0)만 통과한다. 폼에서 체크박스를 받는다면 컨트롤러 직전에 어댑터를 두거나, 커스텀 파이프를 만든다.

### ParseArrayPipe

콤마 구분 문자열을 배열로 만드는 파이프다. 쿼리스트링으로 여러 ID를 받을 때 자주 쓴다.

```typescript
@Get()
findByIds(
  @Query('ids', new ParseArrayPipe({ items: Number, separator: ',' }))
  ids: number[],
) {
  return this.userService.findByIds(ids);
}
```

`?ids=1,2,3`이 오면 `[1, 2, 3]`이 된다. 그런데 이 파이프는 실무에서 사고가 잘 나는 편이다. 주의할 점이 세 가지 있다.

첫째, **빈 문자열 처리.** `?ids=`처럼 값이 비어 있으면 기본적으로 빈 배열이 아니라 검증 실패가 난다. `optional: true`를 켜야 빈 값을 허용한다.

```typescript
new ParseArrayPipe({ items: Number, separator: ',', optional: true })
```

둘째, **단일 값 대 배열 값의 형태 차이.** 클라이언트가 `?ids=1`만 보내면 ParseArrayPipe는 `[1]`로 잘 만든다. 그런데 `?ids=1&ids=2`처럼 같은 키를 반복하는 패턴으로 보내면 Express의 쿼리 파서가 이미 `["1", "2"]` 배열로 만든 뒤 파이프에 넘어간다. ParseArrayPipe가 둘 다 처리하긴 하지만, 클라이언트 쪽에서 두 스타일이 섞이면 디버깅이 어려워진다. API 스펙에서 한쪽으로 통일하는 게 낫다.

셋째, **items 옵션으로 변환만 일어나지 검증은 강하지 않다.** `items: Number`로 줘도 내부적으로 각 요소를 `Number()`로 바꾸는 정도다. 음수, 범위 제한 같은 건 따로 안 본다. 검증이 더 필요하면 DTO 안에 배열을 넣고 `@ArrayMinSize()`, `@IsInt({ each: true })` 같은 데코레이터를 쓰는 ValidationPipe 쪽이 낫다.

### ParseUUIDPipe

UUID 형식 검증 전용이다. 형식만 맞으면 통과시키고, 그 외에는 400을 던진다. 변환은 하지 않는다(문자열 그대로).

```typescript
@Get(':id')
findOne(@Param('id', ParseUUIDPipe) id: string) {
  return this.orderService.findOne(id);
}
```

버전을 지정하지 않으면 모든 UUID 버전을 통과시킨다. 운영 환경에서 v4만 받기로 정했다면 명시한다.

```typescript
@Param('id', new ParseUUIDPipe({ version: '4' })) id: string
```

조심할 점은 대소문자다. 표준 UUID는 소문자가 일반적이지만 ParseUUIDPipe는 대문자 UUID도 통과시킨다. 데이터베이스에 저장할 때 정규화가 필요하면 변환 로직을 별도로 둬야 한다.

### ParseEnumPipe

enum 값으로 받고 싶을 때 쓴다. 문자열이 enum의 멤버 중 하나와 정확히 일치해야 통과한다.

```typescript
enum UserRole {
  Admin = 'admin',
  User = 'user',
  Guest = 'guest',
}

@Get()
list(@Query('role', new ParseEnumPipe(UserRole)) role: UserRole) {
  return this.userService.listByRole(role);
}
```

`?role=admin`은 통과, `?role=root`는 거부한다. 주의할 점은 enum 값이 문자열이어야 의도대로 동작한다는 점이다. 숫자 enum(`Admin = 0` 같은)을 쓰면 쿼리스트링의 `"0"`이 들어왔을 때 비교가 깨질 수 있다. 쿼리에서 받는 enum은 문자열 enum으로 정의하는 게 안전하다.

### DefaultValuePipe

값이 `undefined`나 `null`일 때 기본값을 넣어주는 파이프다. ParsePipe 계열과 같이 쓰는 패턴이 흔하다.

```typescript
@Get()
list(
  @Query('page', new DefaultValuePipe(1), ParseIntPipe) page: number,
  @Query('limit', new DefaultValuePipe(20), ParseIntPipe) limit: number,
) {
  return this.userService.list({ page, limit });
}
```

순서가 중요하다. `DefaultValuePipe`가 먼저 돌아서 `undefined`를 `1`로 바꾸고, 그다음 `ParseIntPipe`가 그 값을 받는다. 순서를 바꾸면 `ParseIntPipe`가 먼저 `undefined`를 받아서 검증 실패가 난다. 핸들러에 적용하는 파이프는 적힌 순서대로 실행된다는 점을 기억해야 한다.

또 하나, `DefaultValuePipe`는 빈 문자열을 기본값으로 바꿔주지 않는다. `?page=` 같은 입력은 `undefined`가 아니라 `""`로 들어오기 때문에 기본값이 적용되지 않고 `ParseIntPipe`에서 막힌다. 쿼리스트링 파싱 단계에서 빈 값을 어떻게 다루는지 확인하고 써야 한다.

### ParseFilePipe

파일 업로드 검증용이다. 멀티파트로 들어오는 파일의 크기, MIME 타입을 거른다. 다른 파이프와 모양이 좀 다르다.

```typescript
@Post('upload')
@UseInterceptors(FileInterceptor('file'))
upload(
  @UploadedFile(
    new ParseFilePipe({
      validators: [
        new MaxFileSizeValidator({ maxSize: 1024 * 1024 * 5 }),
        new FileTypeValidator({ fileType: /image\/(png|jpeg)/ }),
      ],
    }),
  )
  file: Express.Multer.File,
) {
  return { name: file.originalname, size: file.size };
}
```

내부적으로 `MaxFileSizeValidator`, `FileTypeValidator` 같은 검증기를 등록하는 구조다. 변환은 하지 않고 검증만 한다.

실무에서 자주 부딪히는 문제는 `FileTypeValidator`의 동작이다. 이 검증기는 기본적으로 클라이언트가 보낸 `mimetype` 헤더를 본다. 클라이언트가 헤더를 위조하면 통과한다. 진짜 파일 시그니처(매직 넘버)를 보고 싶으면 `file-type` 같은 라이브러리를 써서 커스텀 검증기를 만들어야 한다. NestJS 9 이후 버전에서는 `FileTypeValidator`가 `file-type` 패키지를 사용하도록 옵션을 줄 수 있지만, 옵션을 명시하지 않으면 헤더 기반이다. 보안이 중요하다면 반드시 확인해야 한다.

또 하나, `MaxFileSizeValidator`는 Multer가 이미 파일을 메모리나 디스크에 받은 뒤에 동작한다. 즉, 100MB 파일을 거부하더라도 100MB는 이미 메모리에 올라와 있다. 진짜 큰 파일을 막으려면 Multer의 `limits.fileSize` 옵션으로 업로드 단계에서 차단해야 한다. ParseFilePipe는 보조 검증이지 1차 방어선이 아니다.

```typescript
FileInterceptor('file', {
  limits: { fileSize: 1024 * 1024 * 10 },
})
```

이 옵션이 깔린 뒤에 ParseFilePipe로 비즈니스 규칙(이미지만 받기, 5MB 이하 등)을 검증한다.


## 변환 파이프 — transform이라는 단어의 두 가지 뜻

NestJS 문서에서 "transform"이라는 단어가 두 군데에서 쓰이는데 의미가 다르다. 파이프를 처음 다루면 가장 헷갈리는 지점이다.

첫째, **파이프 자체의 `transform` 메서드**. 모든 파이프는 `PipeTransform` 인터페이스의 `transform(value, metadata)` 메서드를 구현한다. 이 메서드가 반환하는 값이 핸들러 인자가 된다. 변환 파이프든 검증 파이프든 메서드 이름이 같다. 검증만 하는 파이프는 받은 값을 그대로 반환하고, 변환이 필요한 파이프는 바뀐 값을 반환한다.

둘째, **ValidationPipe의 `transform: true` 옵션**. 이건 ValidationPipe가 plain object를 DTO 클래스 인스턴스로 변환할지를 결정하는 옵션이다. ParseIntPipe와는 무관하다.

이름이 겹치다 보니 "ValidationPipe의 transform 옵션을 켜면 ParseIntPipe가 안 도는 건가?" 같은 오해가 생긴다. 두 개는 완전히 다른 레이어다. ParseIntPipe는 핸들러 인자 단위로 돌고, ValidationPipe의 transform 옵션은 DTO 객체 안의 프로퍼티 단위로 돈다.

### 변환 파이프가 반환하는 값의 흐름

```typescript
@Get(':id')
findOne(@Param('id', ParseIntPipe) id: number) {
  return id;
}
```

- 요청: `/users/42`
- `@Param('id')`이 꺼낸 값: `"42"` (문자열)
- ParseIntPipe의 `transform("42", metadata)` 호출
- 반환값: `42` (숫자)
- 핸들러 인자 `id`: `42`

이 흐름이 머리에 있어야 다중 파이프 체인이 헷갈리지 않는다. 파이프를 여러 개 붙이면 앞 파이프의 반환값이 다음 파이프의 입력이 된다.

```typescript
@Get()
list(
  @Query('page', new DefaultValuePipe(1), ParseIntPipe, new MinValuePipe(1))
  page: number,
) {
  return this.userService.list({ page });
}
```

- 입력이 없으면 `DefaultValuePipe`가 `1`을 만들고
- `ParseIntPipe`가 받아서 정수로 확인하고(이미 숫자면 그대로)
- `MinValuePipe`(커스텀)가 1 이상인지 검증한다

순서가 잘못되면 의도와 다르게 돈다. `ParseIntPipe`를 `DefaultValuePipe`보다 앞에 두면 `undefined`가 ParseIntPipe로 가서 400이 난다.


## 커스텀 파이프 작성

`PipeTransform` 인터페이스를 구현하면 끝이다. 인터페이스는 `transform(value, metadata)` 하나뿐이다.

```typescript
import { PipeTransform, Injectable, BadRequestException, ArgumentMetadata } from '@nestjs/common';

@Injectable()
export class TrimPipe implements PipeTransform<string, string> {
  transform(value: string, metadata: ArgumentMetadata): string {
    if (typeof value !== 'string') {
      return value;
    }
    return value.trim();
  }
}
```

`@Injectable()`을 붙이면 NestJS의 DI 컨테이너가 관리한다. 클래스 자체로 데코레이터에 넘길 수 있다. 다른 서비스가 필요하면 생성자 주입도 된다.

```typescript
@Injectable()
export class UserExistsPipe implements PipeTransform<string, Promise<User>> {
  constructor(private readonly userService: UserService) {}

  async transform(value: string): Promise<User> {
    const user = await this.userService.findOne(value);
    if (!user) {
      throw new BadRequestException(`User ${value} not found`);
    }
    return user;
  }
}
```

이렇게 만들면 핸들러에서 ID 대신 객체가 바로 들어온다.

```typescript
@Get(':id')
findOne(@Param('id', UserExistsPipe) user: User) {
  return user;
}
```

편해 보이지만 단점이 있다. 파이프 안에서 DB를 조회하면 핸들러 진입 전에 쿼리가 한 번 더 도는 셈이다. 컨트롤러에서 같은 객체를 또 쓰면 또 조회한다. 조회 결과를 핸들러로 넘기는 패턴은 단순한 라우트에서만 쓰고, 복잡한 로직에서는 ID만 받고 서비스 안에서 한 번만 조회하는 게 추적이 쉽다.

### ArgumentMetadata 활용

`transform`의 두 번째 인자 `ArgumentMetadata`는 파이프가 어떤 컨텍스트에서 호출되었는지 알려준다.

```typescript
interface ArgumentMetadata {
  type: 'body' | 'query' | 'param' | 'custom';
  metatype?: Type<unknown>;
  data?: string;
}
```

- `type`: `@Body()`, `@Query()`, `@Param()` 중 어디서 왔는지
- `metatype`: 핸들러 인자에 선언된 타입(예: `CreateUserDto`)
- `data`: 데코레이터에 넘긴 값(`@Query('page')`의 `'page'`)

ValidationPipe가 DTO 클래스를 알아내는 비결이 `metatype`이다. 핸들러 시그니처에 `dto: CreateUserDto`라고 적어 두면 NestJS가 reflect-metadata로 그 타입을 읽어 `metatype`에 넣는다. ValidationPipe는 `metatype`이 있으면 plain object를 그 클래스로 변환한 뒤 검증한다.

커스텀 파이프에서 `metatype`을 쓰는 경우는 드물지만, "이 파이프는 primitive 타입에는 적용하지 않는다" 같은 분기를 만들 때 활용한다.

```typescript
@Injectable()
export class SanitizePipe implements PipeTransform {
  transform(value: any, metadata: ArgumentMetadata) {
    const primitives = [String, Boolean, Number, Array, Object];
    if (primitives.includes(metadata.metatype as any)) {
      return value;
    }
    return sanitize(value);
  }
}
```


## 파이프 적용 범위

파이프는 네 군데에 붙일 수 있다. 적용 범위가 좁아질수록 우선순위가 명확해진다.

### 글로벌

`main.ts`에서 `app.useGlobalPipes()`로 등록한다. 모든 컨트롤러, 모든 핸들러, 모든 인자에 적용된다.

```typescript
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalPipes(new ValidationPipe({ transform: true, whitelist: true }));
  await app.listen(3000);
}
```

ValidationPipe는 거의 항상 글로벌로 등록한다. 모든 DTO에 일관된 검증이 돌게 하려면 이 방법이 가장 깔끔하다. 단, 이렇게 등록한 파이프는 DI 컨테이너 바깥에서 인스턴스화되기 때문에 다른 서비스를 주입받지 못한다. DI가 필요하면 `APP_PIPE` 토큰으로 모듈에 등록한다.

```typescript
import { APP_PIPE } from '@nestjs/core';

@Module({
  providers: [
    {
      provide: APP_PIPE,
      useClass: ValidationPipe,
    },
  ],
})
export class AppModule {}
```

이 방식은 NestJS의 의존성 그래프 안에서 인스턴스가 만들어지기 때문에 다른 프로바이더를 생성자에서 주입받을 수 있다. 다만 옵션을 줘야 한다면 `useFactory`를 써야 한다.

```typescript
{
  provide: APP_PIPE,
  useFactory: () => new ValidationPipe({ transform: true, whitelist: true }),
}
```

### 컨트롤러

`@UsePipes()`를 컨트롤러 클래스에 붙이면 그 컨트롤러 안의 모든 핸들러에 적용된다.

```typescript
@Controller('users')
@UsePipes(new ValidationPipe({ transform: true }))
export class UsersController {
  // ...
}
```

특정 컨트롤러만 다른 검증 정책을 쓰고 싶을 때 유용하지만, 컨트롤러마다 다른 정책을 쓰는 코드베이스는 일관성이 깨지기 쉽다. 가능하면 글로벌 정책으로 통일하고, 예외만 핸들러 단위에서 다룬다.

### 메서드

`@UsePipes()`를 핸들러에 붙이면 그 핸들러의 모든 인자에 적용된다.

```typescript
@Post()
@UsePipes(new ValidationPipe({ transform: true, forbidNonWhitelisted: true }))
create(@Body() dto: CreateUserDto) {
  return this.userService.create(dto);
}
```

이 핸들러만 더 엄격한 정책을 적용하고 싶을 때 쓴다. 다만 글로벌 ValidationPipe가 이미 있다면 두 파이프가 모두 돈다(중복 호출). 같은 종류의 파이프가 여러 단계에서 호출되면 디버깅이 복잡해지니, 메서드 단위에서 오버라이드할 때는 글로벌 파이프와 충돌하지 않는지 확인해야 한다.

### 파라미터

데코레이터의 두 번째 이후 인자로 파이프를 직접 넘기는 방식이다. 가장 좁은 범위, 가장 흔한 사용법이다.

```typescript
@Get(':id')
findOne(@Param('id', ParseIntPipe) id: number) {
  return id;
}
```

이 방식은 `ParseIntPipe` 같은 인자 단위 변환 파이프에서 거의 유일하게 쓴다. ValidationPipe를 파라미터 단위로 붙이는 경우는 드물다.


## 파이프 실행 순서

같은 인자에 파이프를 여러 개 붙이면 적힌 순서대로 실행된다.

```typescript
@Query('page',
  new DefaultValuePipe(1),
  ParseIntPipe,
  new MinValuePipe(1),
) page: number
```

- `DefaultValuePipe(1)` → `ParseIntPipe` → `MinValuePipe(1)` 순서로 돈다.
- 앞 파이프의 반환값이 뒤 파이프의 입력이 된다.
- 중간에 예외가 나면 뒤 파이프는 실행되지 않는다.

여러 레벨(글로벌, 컨트롤러, 메서드, 파라미터)에 파이프가 등록돼 있으면 등록된 모든 파이프가 다 실행된다. 우선순위가 아니라 누적이다. 순서는 글로벌 → 컨트롤러 → 메서드 → 파라미터다. 그래서 글로벌 ValidationPipe와 파라미터의 ParseIntPipe가 같이 있으면 둘 다 돈다. 다만 ValidationPipe는 `metatype`이 primitive(`Number`, `String` 같은) 거나 없으면 변환·검증을 건너뛰기 때문에 `@Param('id') id: number`에서는 ValidationPipe가 사실상 통과만 시킨다.

여기서 흔한 오해가 있다. "글로벌 ValidationPipe가 있으면 ParseIntPipe가 필요 없는 거 아닌가?" 아니다. ValidationPipe는 DTO 클래스가 metatype일 때만 검증·변환을 한다. `@Param('id') id: number`처럼 primitive 타입이면 ValidationPipe는 손대지 않는다. 그래서 라우트 파라미터를 숫자로 받으려면 여전히 ParseIntPipe가 필요하다.


## ValidationPipe와의 차이

빌트인 파이프와 ValidationPipe는 같은 인터페이스를 구현하지만 책임이 다르다.

`ParseIntPipe`, `ParseUUIDPipe` 같은 파이프는 **단일 값**을 본다. 입력은 문자열, 출력은 변환된 값이거나 동일한 값이다. metatype은 거의 보지 않는다. 핸들러 인자 단위로 적용하는 게 자연스럽다.

`ValidationPipe`는 **객체 전체**를 본다. metatype을 읽어 plain object를 DTO 클래스로 만들고, 클래스의 데코레이터 메타데이터로 각 프로퍼티를 검증한다. `@Body()` 한 자리에서 수십 개 필드를 한꺼번에 다룬다. 글로벌로 등록하는 게 자연스럽다.

언제 어느 쪽을 쓰는지 정리하면 이렇다.

- `@Param('id')`나 `@Query('page')`처럼 **단일 primitive 값**: 빌트인 파이프(ParseIntPipe 등)
- `@Body()`나 `@Query()`로 받는 **객체 형태의 데이터**: DTO + ValidationPipe
- 쿼리스트링이지만 **여러 필드가 같이 오는 검색 조건**: DTO 형태로 묶고 ValidationPipe

쿼리스트링도 필드가 많으면 DTO로 묶는 게 낫다. `@Query('page', ParseIntPipe) page, @Query('limit', ParseIntPipe) limit, @Query('sort') sort, ...` 식으로 인자가 많아지면 시그니처가 더러워진다. `PaginationQueryDto`를 만들고 `@Query() query: PaginationQueryDto`로 받는 패턴이 깔끔하다. 단, 쿼리스트링은 모든 값이 문자열로 들어오기 때문에 ValidationPipe의 `transform: true`와 `enableImplicitConversion: true`가 필요하다. 이 부분은 [Nest_JS_Validation_Pipe.md](Nest_JS_Validation_Pipe.md)에 자세히 다뤄 두었다.


## 실무에서 자주 보는 문제

### 글로벌 ValidationPipe가 있는데 ParseIntPipe가 동작 안 한다

대부분 등록 순서나 옵션 문제가 아니라, 핸들러 시그니처를 잘못 적은 경우다.

```typescript
// 잘못된 예
@Get(':id')
findOne(@Param('id') id: number) {
  // id는 사실 문자열. number 타입 선언은 컴파일러만 속을 뿐
  return typeof id; // "string"
}
```

타입스크립트의 타입 선언은 런타임에 사라진다. `id: number`라고 적어도 ParseIntPipe를 명시하지 않으면 실제 런타임 값은 그냥 라우트 파라미터의 문자열이다. ValidationPipe도 metatype이 `Number`(primitive)이면 손대지 않는다. 명시적으로 ParseIntPipe를 붙여야 한다.

### 옵셔널 쿼리에 ParseIntPipe를 붙이면 400이 난다

`?page=`가 안 들어오면 값은 `undefined`다. ParseIntPipe는 `undefined`를 거부한다. 옵셔널이 명확하면 DefaultValuePipe와 같이 쓰거나, 파이프에 `optional: true` 옵션을 준다(NestJS 10 이후).

```typescript
@Query('page', new ParseIntPipe({ optional: true })) page?: number
```

이 옵션이 켜져 있으면 값이 없을 때 그냥 `undefined`를 그대로 통과시킨다. 단, `?page=`처럼 빈 문자열은 여전히 거부한다. 빈 문자열을 옵셔널로 처리하려면 별도의 어댑터 파이프를 앞에 둬야 한다.

### 커스텀 파이프에서 비동기 작업이 핸들러를 느리게 만든다

파이프 안에서 DB 조회나 외부 API 호출을 하면, 그 시간만큼 핸들러 진입이 늦어진다. 핸들러에서 같은 데이터를 또 조회하면 두 번 조회되는 일도 생긴다. 파이프는 가능하면 입력값의 형식 검증·변환에 한정하고, 도메인 데이터 조회는 서비스 계층에서 한 번에 처리하는 패턴이 추적과 캐싱 모두에 유리하다.

### 파이프 안의 에러가 ExceptionFilter에서 잡히지 않는 것처럼 보인다

파이프 안에서 던지는 예외는 정상적으로 ExceptionFilter로 전파된다. 잡히지 않는 것처럼 보이는 경우는 보통 두 가지다. 첫째, 파이프 안에서 비동기 함수의 reject를 await 없이 흘려보냈을 때. 둘째, 글로벌 ExceptionFilter가 컨트롤러 단위 필터에 가려졌을 때. ExceptionFilter는 [Nest_JS_Exception_Filters.md](Nest_JS_Exception_Filters.md)에 별도로 다룬다.

### ParseArrayPipe로 받은 배열의 검증이 약하다

ParseArrayPipe의 `items` 옵션은 각 요소를 지정한 타입으로 변환하는 정도다. "1 이상의 정수만", "최대 100개" 같은 검증은 하지 않는다. 정밀한 검증이 필요하면 DTO로 받는다.

```typescript
import { IsInt, ArrayMaxSize, ArrayMinSize, Min } from 'class-validator';
import { Transform, Type } from 'class-transformer';

export class FindByIdsQuery {
  @Transform(({ value }) => (typeof value === 'string' ? value.split(',').map(Number) : value))
  @IsInt({ each: true })
  @Min(1, { each: true })
  @ArrayMinSize(1)
  @ArrayMaxSize(100)
  @Type(() => Number)
  ids: number[];
}

@Get()
findByIds(@Query() query: FindByIdsQuery) {
  return this.userService.findByIds(query.ids);
}
```

`@Transform`으로 콤마 구분 문자열을 배열로 바꾸고, `@IsInt({ each: true })`와 `@Min(1, { each: true })`로 각 요소를 검증한다. ValidationPipe가 글로벌로 등록돼 있어야 동작한다.


## 파이프 디버깅

파이프가 의도대로 동작하는지 확인할 때 가장 빠른 방법은 `transform` 메서드에 임시 로그를 찍는 것이다.

```typescript
@Injectable()
export class DebugPipe implements PipeTransform {
  transform(value: any, metadata: ArgumentMetadata) {
    console.log('value:', value, 'metadata:', metadata);
    return value;
  }
}
```

이 파이프를 의심되는 인자에 붙이면 어떤 값이 들어오는지, metatype은 무엇인지 바로 확인할 수 있다. 글로벌 파이프와 메서드 파이프가 모두 적용된 상태에서 순서가 헷갈리면, 각 단계에 다른 라벨의 DebugPipe를 두고 출력 순서를 보면 흐름이 명확해진다.

또 한 가지, ValidationPipe가 던진 에러 메시지가 단편적으로 보일 때는 `disableErrorMessages: false`(기본값)를 유지하고, 응답 본문에 실제로 어떤 메시지 배열이 담겼는지 확인한다. 운영 환경에서 메시지를 숨기려고 `disableErrorMessages: true`로 켜두면 디버깅 단계에서 원인 추적이 어려워진다. 개발 환경과 운영 환경의 설정을 분리해 두는 게 안전하다.


## 참고

- [Nest_JS_Validation_Pipe.md](Nest_JS_Validation_Pipe.md) — ValidationPipe와 DTO 검증 상세
- [Nest_JS_요청_라이프사이클.md](Nest_JS_요청_라이프사이클.md) — 미들웨어·Guard·Pipe·Interceptor 실행 순서
- [Nest_JS_Exception_Filters.md](Nest_JS_Exception_Filters.md) — 파이프가 던진 예외 처리
- [Nest_JS_Decorator.md](Nest_JS_Decorator.md) — 파라미터 데코레이터와 파이프 결합
