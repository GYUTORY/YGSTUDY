---
title: NestJS API 버저닝
tags: [nestjs, api-versioning, versioning, dto, swagger, node]
updated: 2026-06-12
---

# NestJS API 버저닝

API를 한번 외부에 공개하면 응답 구조를 마음대로 바꿀 수 없다. 필드 이름 하나 바꾸거나 응답 형태를 객체에서 배열로 바꾸는 순간, 그 API를 쓰던 모바일 앱이나 파트너사 연동이 깨진다. 모바일 앱은 한번 배포되면 사용자가 업데이트하기 전까지 구버전이 계속 돌아가기 때문에, 서버가 일방적으로 응답을 바꾸면 강제 업데이트를 못 받은 사용자는 그냥 앱이 망가진다. 그래서 호환이 깨지는 변경은 새 버전으로 분리하고, 구버전은 한동안 같이 굴리다가 트래픽이 빠지면 내린다.

NestJS는 `enableVersioning`으로 이 버전 분기를 프레임워크 차원에서 지원한다. 직접 라우트 경로에 `/v1`, `/v2`를 박는 방식보다 컨트롤러·라우트 단위로 버전을 선언하는 게 관리가 편하다. 이 문서는 버저닝 타입 세 가지(URI/Header/Media-Type)와 컨트롤러·라우트 단위 지정, 기본 버전과 `VERSION_NEUTRAL`, 버전별 DTO를 어떻게 나누는지, 그리고 구버전 deprecation을 운영하면서 Swagger 문서를 분리할 때 막히는 지점을 실제 겪은 순서대로 정리한다. Swagger 기본 설정은 [Nest_JS_Swagger.md](Nest_JS_Swagger.md)를, DTO 검증은 [Nest_JS_Validation_Pipe.md](Nest_JS_Validation_Pipe.md)를 참고한다.


## enableVersioning 기본 설정

버저닝은 `main.ts`의 bootstrap에서 켠다. `VersioningType`으로 어떤 방식으로 버전을 받을지 정한다.

```typescript
// main.ts
import { NestFactory } from '@nestjs/core';
import { VersioningType } from '@nestjs/common';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.enableVersioning({
    type: VersioningType.URI,
    defaultVersion: '1',
  });

  await app.listen(3000);
}
bootstrap();
```

이렇게 하면 컨트롤러에 버전을 지정한 라우트가 `/v1/...` 형태로 노출된다. `type`에는 세 가지가 들어간다.

- `VersioningType.URI` — `/v1/users` 처럼 경로에 버전이 들어간다. 기본 접두사는 `v`라서 `v1`, `v2`로 찍힌다.
- `VersioningType.HEADER` — 클라이언트가 지정한 헤더 값으로 버전을 판단한다. URL은 그대로고 헤더만 다르다.
- `VersioningType.MEDIA_TYPE` — `Accept` 헤더의 미디어 타입 파라미터로 버전을 판단한다.

세 방식은 동시에 쓰는 게 아니라 하나를 골라야 한다. 실무에서 거의 URI를 쓴다. URL만 보면 버전이 바로 보이고, 브라우저로 직접 때려보거나 curl로 확인하기 편하고, 캐시·로그·CDN에서 경로 단위로 구분이 되기 때문이다. 헤더나 미디어 타입은 URL이 깨끗하게 유지된다는 장점이 있지만, 디버깅할 때 헤더를 일일이 확인해야 하고 CDN 캐시 키에 헤더를 넣어줘야 하는 등 운영 비용이 더 든다.


## 버저닝 타입별 차이

### URI 버저닝

가장 직관적이다. 경로에 버전이 박힌다.

```typescript
app.enableVersioning({
  type: VersioningType.URI,
  prefix: 'v', // 기본값 'v', 'version'으로 바꾸면 /version1/...
});
```

`prefix: false`로 두면 `v` 접두사 없이 `/1/users`처럼 숫자만 들어간다. 보통은 기본값 `v`를 그대로 둔다.

전역 라우트 prefix(`app.setGlobalPrefix('api')`)를 같이 쓰면 `/api/v1/users` 순서로 붙는다. 버전이 글로벌 prefix 뒤에 온다.

### Header 버저닝

지정한 헤더 이름의 값으로 버전을 고른다.

```typescript
app.enableVersioning({
  type: VersioningType.HEADER,
  header: 'X-API-Version',
});
```

클라이언트는 `X-API-Version: 2` 헤더를 실어 보낸다. URL은 `/users` 그대로다. 헤더가 없으면 `defaultVersion`이 적용되고, 기본 버전도 없으면 404가 난다.

### Media-Type 버저닝

`Accept` 헤더에서 버전 파라미터를 읽는다.

```typescript
app.enableVersioning({
  type: VersioningType.MEDIA_TYPE,
  key: 'v=',
});
```

클라이언트는 `Accept: application/json;v=2` 형태로 보낸다. `key`가 `v=`면 세미콜론 뒤의 `v=2`를 찾아 버전 `2`로 해석한다. GitHub API가 이 방식을 쓰는 걸로 유명한데, 실제로 직접 운영해보면 클라이언트가 Accept 헤더를 정확히 맞춰 보내게 만드는 게 생각보다 번거롭다.


## 컨트롤러·라우트 단위 버전 지정

버전은 컨트롤러의 `@Controller` 데코레이터에 `version` 옵션으로 준다.

```typescript
import { Controller, Get } from '@nestjs/common';

@Controller({ path: 'users', version: '1' })
export class UsersV1Controller {
  @Get()
  findAll() {
    return { version: 'v1', users: [] };
  }
}

@Controller({ path: 'users', version: '2' })
export class UsersV2Controller {
  @Get()
  findAll() {
    return { version: 'v2', data: { users: [] } };
  }
}
```

같은 `path: 'users'`라도 버전이 다르면 별개의 컨트롤러로 등록된다. URI 버저닝이면 각각 `/v1/users`, `/v2/users`로 노출된다. 두 컨트롤러를 모두 모듈의 `controllers` 배열에 등록해야 한다.

라우트 하나만 다른 버전으로 두고 싶으면 메서드에 `@Version`을 붙인다.

```typescript
import { Controller, Get, Version } from '@nestjs/common';

@Controller({ path: 'users', version: '1' })
export class UsersController {
  @Get()
  findAllV1() {
    return { version: 'v1' };
  }

  @Version('2')
  @Get()
  findAllV2() {
    return { version: 'v2' };
  }
}
```

메서드의 `@Version`이 컨트롤러 버전보다 우선한다. 컨트롤러 전체는 v1인데 특정 라우트만 v2가 추가됐을 때 쓴다. 다만 컨트롤러 하나에 여러 버전을 섞으면 나중에 코드가 지저분해진다. 버전이 두 개를 넘어가면 컨트롤러 자체를 버전별로 쪼개는 게 읽기 편하다.

한 라우트가 여러 버전을 동시에 받게 하려면 배열로 준다.

```typescript
@Version(['1', '2'])
@Get()
findAll() {
  // v1, v2 둘 다 이 핸들러로 들어옴
}
```

v1과 v2 응답이 같고 v3에서만 바뀌는 경우, v1·v2를 배열로 묶어두고 v3만 따로 빼는 식으로 쓴다.


## 기본 버전과 VERSION_NEUTRAL

`defaultVersion`은 버전을 지정하지 않은 요청에 어떤 버전을 적용할지 정한다. URI 버저닝에서 `defaultVersion: '1'`이면 `@Version`이 없는 컨트롤러도 `/v1` 경로로 묶인다. 배열로 여러 기본 버전을 줄 수도 있다.

```typescript
app.enableVersioning({
  type: VersioningType.URI,
  defaultVersion: ['1', '2'],
});
```

문제는 버전 개념이 아예 없어야 하는 엔드포인트다. 헬스 체크(`/health`), 메트릭, 웹훅 수신 엔드포인트 같은 건 버전을 붙이면 오히려 곤란하다. 로드밸런서 헬스 체크가 `/health`를 때리는데 버저닝 때문에 `/v1/health`로 바뀌면 헬스 체크 설정을 다 같이 고쳐야 한다. 이럴 때 `VERSION_NEUTRAL`을 쓴다.

```typescript
import { Controller, Get, VERSION_NEUTRAL } from '@nestjs/common';

@Controller({ path: 'health', version: VERSION_NEUTRAL })
export class HealthController {
  @Get()
  check() {
    return { status: 'ok' };
  }
}
```

`VERSION_NEUTRAL`로 둔 컨트롤러는 버전 접두사 없이 `/health`로 노출되고, 버전 헤더가 있든 없든 다 받는다. 헬스 체크는 거의 항상 이걸로 둔다. 자세한 헬스 체크 구성은 [Nest_JS_Health_Check.md](Nest_JS_Health_Check.md)를 참고한다.

한 가지 주의할 점은, URI 버저닝에서 `VERSION_NEUTRAL` 컨트롤러와 버전이 붙은 컨트롤러가 같은 경로를 쓰면 매칭이 헷갈린다는 것이다. `VERSION_NEUTRAL`은 `/health` 하나로 끝나는 독립 엔드포인트에 쓰고, 버전 분기가 필요한 리소스에는 쓰지 않는다.


## 버전별 DTO 분기

버전을 나누는 진짜 이유는 응답·요청 구조가 바뀌기 때문이다. 라우트만 갈라놓고 같은 DTO를 쓰면 의미가 없다. v2에서 필드가 추가되거나 이름이 바뀌면 DTO를 따로 만든다.

```typescript
// dto/create-user.v1.dto.ts
import { IsString, IsEmail } from 'class-validator';

export class CreateUserV1Dto {
  @IsString()
  name: string;

  @IsEmail()
  email: string;
}

// dto/create-user.v2.dto.ts
import { IsString, IsEmail, IsOptional } from 'class-validator';

export class CreateUserV2Dto {
  // v2에서 name을 firstName/lastName으로 분리
  @IsString()
  firstName: string;

  @IsString()
  lastName: string;

  @IsEmail()
  email: string;

  @IsOptional()
  @IsString()
  phoneNumber?: string;
}
```

컨트롤러는 각 버전에 맞는 DTO를 받는다.

```typescript
@Controller({ path: 'users', version: '1' })
export class UsersV1Controller {
  constructor(private readonly usersService: UsersService) {}

  @Post()
  create(@Body() dto: CreateUserV1Dto) {
    // v1 입력을 내부 모델로 변환
    return this.usersService.create({
      firstName: dto.name,
      lastName: '',
      email: dto.email,
    });
  }
}

@Controller({ path: 'users', version: '2' })
export class UsersV2Controller {
  constructor(private readonly usersService: UsersService) {}

  @Post()
  create(@Body() dto: CreateUserV2Dto) {
    return this.usersService.create(dto);
  }
}
```

여기서 핵심은 서비스 레이어를 버전마다 복사하지 않는 것이다. `UsersService`는 내부 도메인 모델 하나만 다루고, 컨트롤러가 버전별 DTO를 내부 모델로 변환하는 책임을 진다. 버전 분기는 입출력 경계(컨트롤러·DTO)에서만 일어나고, 비즈니스 로직은 버전을 모르게 유지한다. 이걸 어기고 서비스에 `if (version === '2')` 같은 분기를 넣기 시작하면 버전이 늘어날 때마다 서비스가 if 지옥이 된다.

응답도 마찬가지다. 내부 모델을 그대로 반환하지 말고 버전별 응답 DTO로 매핑한다. v1은 평평한 객체를 주고 v2는 `data`로 한번 감싸는 식으로 응답 형태가 달라지면, 응답 매퍼를 버전별로 둔다. 인터셉터로 공통 래핑을 하는 경우 버전마다 래핑 형태가 다를 수 있으니, 인터셉터 안에서 `request.version` 같은 걸로 분기하기보다 컨트롤러가 이미 완성된 응답 DTO를 반환하게 만드는 편이 추적하기 쉽다.


## 구버전 deprecation 운영

버전을 새로 내는 것보다 구버전을 내리는 게 훨씬 어렵다. v2를 냈는데 v1 트래픽이 안 빠지면 v1을 영원히 들고 가야 한다. deprecation은 두 단계로 본다. 먼저 "이 버전은 곧 사라진다"고 알리는 단계, 그다음 실제로 라우트를 제거하는 단계다.

알리는 단계에서는 응답 헤더에 deprecation 표시를 실어 보낸다. 인터셉터로 처리하면 컨트롤러를 안 건드리고 붙일 수 있다.

```typescript
import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';

@Injectable()
export class DeprecationInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const res = context.switchToHttp().getResponse();
    res.setHeader('Deprecation', 'true');
    res.setHeader('Sunset', 'Wed, 31 Dec 2026 23:59:59 GMT');
    res.setHeader('Link', '</v2/users>; rel="successor-version"');
    return next.handle().pipe(tap(() => {}));
  }
}
```

`Deprecation`, `Sunset`, `Link`는 HTTP 표준으로 정의된 헤더라 클라이언트 쪽 라이브러리가 이걸 보고 경고를 띄울 수 있다. `Sunset`에 실제로 내릴 날짜를 박아두면, 그 날짜 전에 클라이언트가 마이그레이션할 명분이 된다. 다만 헤더만 보내고 끝내면 아무도 안 본다. 실제로는 v1으로 들어오는 트래픽을 로깅해서, 어떤 클라이언트(User-Agent, API 키)가 아직 v1을 쓰는지 집계하는 게 더 중요하다. 누가 쓰는지 알아야 연락해서 옮기라고 할 수 있다.

```typescript
@Injectable()
export class V1UsageLogger implements NestInterceptor {
  private readonly logger = new Logger('V1Usage');

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const req = context.switchToHttp().getRequest();
    this.logger.warn(
      `deprecated v1 호출: ${req.method} ${req.url} ua=${req.headers['user-agent']}`,
    );
    return next.handle();
  }
}
```

실제로 라우트를 내릴 때는 한번에 죽이지 않는다. `Sunset` 날짜가 지나면 곧장 410 Gone을 응답하게 바꿔서 "이 버전은 끝났다"는 신호를 명확히 주고, 일정 기간 뒤에 컨트롤러 코드를 제거한다. 410을 거치지 않고 바로 라우트를 삭제하면 404가 나는데, 클라이언트 입장에서는 경로 오타인지 버전이 사라진 건지 구분이 안 된다.


## Swagger 문서 분리

버저닝을 켜면 Swagger 문서 하나에 모든 버전 라우트가 섞여 나온다. `/v1/users`와 `/v2/users`가 같은 문서에 둘 다 보이면, 프론트엔드가 어느 게 최신인지 헷갈린다. 버전별로 문서를 분리하는 게 깔끔하다.

`SwaggerModule.createDocument`에 옵션을 줘서 특정 버전 라우트만 추리고, 버전마다 다른 경로에 UI를 띄운다.

```typescript
// main.ts
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';

function setupSwagger(app) {
  // v1 문서
  const v1Config = new DocumentBuilder()
    .setTitle('My API')
    .setDescription('v1 (deprecated)')
    .setVersion('1.0')
    .build();
  const v1Doc = SwaggerModule.createDocument(app, v1Config, {
    include: [UsersV1Controller, OrdersV1Controller],
  });
  SwaggerModule.setup('docs/v1', app, v1Doc);

  // v2 문서
  const v2Config = new DocumentBuilder()
    .setTitle('My API')
    .setDescription('v2 (current)')
    .setVersion('2.0')
    .build();
  const v2Doc = SwaggerModule.createDocument(app, v2Config, {
    include: [UsersV2Controller, OrdersV2Controller],
  });
  SwaggerModule.setup('docs/v2', app, v2Doc);
}
```

`include`에 그 버전에 속한 컨트롤러만 넣으면 문서가 버전별로 깔끔하게 갈린다. `/docs/v1`, `/docs/v2`로 따로 접근한다.

여기서 실제로 막히는 지점이 몇 개 있다.

첫째, `include`에 컨트롤러를 직접 나열하는 방식은 버전별로 컨트롤러가 완전히 분리돼 있을 때만 깔끔하다. 한 컨트롤러 안에서 `@Version`으로 라우트만 버전을 섞어두면 `include`로는 라우트 단위로 못 거른다. 컨트롤러 통째로 들어오거나 안 들어오거나 둘 중 하나다. 그래서 Swagger를 버전별로 깔끔하게 나눌 생각이면 컨트롤러도 버전별로 분리하는 게 맞다.

둘째, URI 버저닝이 아닌 Header/Media-Type 버저닝을 쓰면 Swagger UI에서 버전 헤더를 자동으로 안 붙여준다. URL이 다 `/users`로 똑같아서 UI에서 "Try it out"을 눌러도 어느 버전을 호출하는지 UI가 모른다. 이 경우 `addGlobalParameters`나 문서별 헤더 설정으로 버전 헤더를 명시해줘야 그나마 테스트가 된다. URI 버저닝이면 경로가 달라서 이 문제가 없다. Swagger를 깔끔하게 쓰고 싶다는 것도 URI 버저닝을 고르는 이유 중 하나다.

셋째, deprecated된 v1 문서를 운영 환경에서 계속 노출할지 정해야 한다. v1을 내리는 중이라도 아직 쓰는 클라이언트가 있으면 문서는 살려둬야 한다. 대신 `setDescription`에 deprecated 표시를 박고, OpenAPI의 `deprecated: true`를 라우트에 달아 UI에서 취소선으로 보이게 한다. 운영 환경에서 Swagger 자체를 닫는 경우 v1·v2 문서를 한꺼번에 막게 되니, 환경별 노출 정책은 [Nest_JS_Swagger.md](Nest_JS_Swagger.md)에서 다룬 방식과 같이 처리한다.


## 정리

URI 버저닝을 기본으로 잡고, 호환이 깨지는 변경이 생길 때만 새 버전을 낸다. 필드 추가처럼 기존 클라이언트가 무시하면 그만인 변경은 굳이 버전을 올리지 않는다. 버전을 올릴 때마다 컨트롤러·DTO·Swagger 문서가 통째로 복제되기 때문에, 버전이 늘어날수록 유지 비용이 빠르게 커진다. 버전 분기는 컨트롤러와 DTO 경계에서만 일어나게 하고 서비스 레이어는 버전을 모르게 두는 것, 그리고 새 버전을 내는 것만큼 구버전을 어떻게 내릴지를 같이 설계하는 것이 핵심이다.
