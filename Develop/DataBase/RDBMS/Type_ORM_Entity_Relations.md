---
title: TypeORM 엔티티 관계 매핑 심화
tags: [typeorm, entity, relations, onetomany, manytomany, joincolumn, cascade, soft-delete, self-referential, owning-side]
updated: 2026-07-28
---

# TypeORM 엔티티 관계 매핑 심화

## 개요

TypeORM 관계 매핑은 데코레이터 한 줄로 끝나는 것처럼 보이지만, 실제로는 owning side 지정, cascade 동작, Soft Delete와의 충돌 같은 문제들이 뒤따른다. 문서나 예제를 그대로 따라가다 보면 개발 환경에서는 잘 동작하다가 데이터가 쌓이면 예상치 못한 곳에서 터진다.

이 문서는 데코레이터 사용법보다 "왜 그렇게 써야 하는가", "잘못 쓰면 어떻게 망가지는가"에 집중한다.

---

## OneToOne

가장 단순하지만 owning side를 잘못 지정하면 FK가 엉뚱한 테이블에 생긴다.

```typescript
// user.entity.ts
@Entity()
export class User {
  @PrimaryGeneratedColumn()
  id: number;

  @OneToOne(() => Profile, (profile) => profile.user, { cascade: true })
  @JoinColumn()
  profile: Profile;
}

// profile.entity.ts
@Entity()
export class Profile {
  @PrimaryGeneratedColumn()
  id: number;

  @OneToOne(() => User, (user) => user.profile)
  user: User;
}
```

`@JoinColumn()`은 반드시 owning side에만 붙인다. FK 컬럼(`profile_id`)은 `@JoinColumn()`이 붙은 테이블에 생성된다. 위 예시에서는 `user` 테이블에 `profile_id`가 생긴다.

양쪽에 `@JoinColumn()`을 붙이거나 아무 쪽에도 안 붙이면 TypeORM이 마이그레이션을 생성할 때 이상한 컬럼을 만들거나 관계 로딩 자체가 깨진다.

FK를 어느 쪽에 둘지는 비즈니스 로직으로 결정한다. 사용자를 삭제해도 프로필 데이터를 남겨야 한다면 `profile` 테이블에 `user_id`를 두는 게 맞고, 반대로 사용자가 생성되면 프로필도 같이 만들어지는 구조라면 `user` 테이블에 `profile_id`를 두는 게 자연스럽다.

---

## OneToMany / ManyToOne

```typescript
// team.entity.ts
@Entity()
export class Team {
  @PrimaryGeneratedColumn()
  id: number;

  @OneToMany(() => Member, (member) => member.team)
  members: Member[];
}

// member.entity.ts
@Entity()
export class Member {
  @PrimaryGeneratedColumn()
  id: number;

  @ManyToOne(() => Team, (team) => team.members)
  @JoinColumn({ name: 'team_id' })
  team: Team;
}
```

FK는 항상 `ManyToOne` 쪽에 생긴다. `@JoinColumn()`을 명시하지 않아도 TypeORM이 자동으로 FK를 `ManyToOne` 쪽 테이블에 만들지만, 컬럼 이름을 직접 제어하려면 `@JoinColumn({ name: 'team_id' })`처럼 명시하는 편이 낫다. 명시하지 않으면 `teamId`같은 카멜케이스 컬럼이 생기는데, 팀에 따라 스네이크케이스를 강제하는 경우 나중에 마이그레이션이 꼬인다.

`OneToMany`는 단독으로 존재할 수 없다. 반드시 반대편에 `ManyToOne`이 있어야 하고, `@JoinColumn()`은 `ManyToOne` 쪽에만 붙인다.

---

## 양방향 관계에서 owning side를 잘못 지정할 때 발생하는 문제

양방향 관계의 핵심은 `inverseSide` 파라미터다. 잘못 지정하면 쿼리 결과가 비어오거나, 저장했는데 관계가 안 걸리는 현상이 생긴다.

```typescript
// 잘못된 예시
@Entity()
export class Post {
  @OneToMany(() => Comment, (comment) => comment.post)
  comments: Comment[];
}

@Entity()
export class Comment {
  // inverseSide를 잘못 연결
  @ManyToOne(() => Post, (post) => post.id)  // post.comments 가 아니라 post.id
  post: Post;
}
```

위처럼 `inverseSide`에 컬렉션이 아닌 id 프로퍼티를 지정하면 TypeORM 내부에서 관계 메타데이터 매핑이 깨진다. `find` 옵션의 `relations`를 써도 결과가 빈 배열로 오거나 아예 에러가 난다.

```typescript
// 올바른 예시
@Entity()
export class Comment {
  @ManyToOne(() => Post, (post) => post.comments)
  post: Post;
}
```

`inverseSide`는 반드시 반대 엔티티의 실제 프로퍼티 이름을 가리켜야 한다. FK가 저장되는 owning side(ManyToOne)와 inverseSide(OneToMany)의 `inverseEntityRelationId`가 일치해야 TypeORM이 조인 쿼리를 올바르게 생성한다.

실수가 생기는 패턴이 있다. 복붙하다가 화살표 함수 안의 프로퍼티를 고치지 않는 경우다. 리팩토링으로 프로퍼티 이름을 바꿨는데 양쪽 중 한 쪽만 반영되면 마찬가지로 깨진다. 타입스크립트가 컴파일 에러를 안 잡아주는 경우도 있어서 런타임에서야 발견한다.

---

## ManyToMany

### 기본 사용법

```typescript
// post.entity.ts
@Entity()
export class Post {
  @PrimaryGeneratedColumn()
  id: number;

  @ManyToMany(() => Tag, (tag) => tag.posts)
  @JoinTable({
    name: 'post_tag',
    joinColumn: { name: 'post_id', referencedColumnName: 'id' },
    inverseJoinColumn: { name: 'tag_id', referencedColumnName: 'id' },
  })
  tags: Tag[];
}

// tag.entity.ts
@Entity()
export class Tag {
  @PrimaryGeneratedColumn()
  id: number;

  @ManyToMany(() => Post, (post) => post.tags)
  posts: Post[];
}
```

`@JoinTable()`은 owning side 한 쪽에만 붙인다. 양쪽에 붙이면 중간 테이블이 두 개 생기거나 마이그레이션이 충돌한다.

### @JoinTable의 한계와 커스텀 중간 테이블

`@JoinTable`로 자동 생성된 중간 테이블은 두 FK 외에 컬럼을 추가할 수 없다. 연결에 메타데이터가 필요한 순간 문제가 된다.

예를 들어 사용자와 역할(Role) 관계에서 "이 권한이 언제 부여됐는지", "누가 부여했는지" 같은 정보가 필요하면 자동 중간 테이블로는 저장할 방법이 없다.

```typescript
// 커스텀 중간 테이블 엔티티
@Entity('user_role')
export class UserRole {
  @PrimaryGeneratedColumn()
  id: number;

  @ManyToOne(() => User, (user) => user.userRoles)
  @JoinColumn({ name: 'user_id' })
  user: User;

  @ManyToOne(() => Role, (role) => role.userRoles)
  @JoinColumn({ name: 'role_id' })
  role: Role;

  @Column({ type: 'timestamp' })
  grantedAt: Date;

  @Column({ nullable: true })
  grantedBy: number;
}

// user.entity.ts
@Entity()
export class User {
  @OneToMany(() => UserRole, (userRole) => userRole.user)
  userRoles: UserRole[];
}

// role.entity.ts
@Entity()
export class Role {
  @OneToMany(() => UserRole, (userRole) => userRole.role)
  userRoles: UserRole[];
}
```

커스텀 중간 테이블을 쓰면 `@ManyToMany`를 아예 사용하지 않는다. 대신 각 엔티티에서 `@OneToMany`로 중간 테이블을 가리키는 구조가 된다. 조회할 때 `find`의 `relations` 옵션을 두 번 타야 하는 불편함이 있지만, 중간 테이블에 비즈니스 데이터가 필요한 경우라면 이 구조가 유일한 방법이다.

---

## 자기참조(Self-referential) 관계

카테고리나 댓글 계층처럼 같은 엔티티 내에서 부모-자식 관계를 표현할 때 쓴다.

```typescript
@Entity()
export class Category {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  name: string;

  @ManyToOne(() => Category, (category) => category.children, { nullable: true })
  @JoinColumn({ name: 'parent_id' })
  parent: Category | null;

  @OneToMany(() => Category, (category) => category.parent)
  children: Category[];
}
```

자기참조에서 주의할 점이 두 가지다.

첫째, `nullable: true` 처리다. 최상위 카테고리는 `parent`가 없으므로 `parent_id`가 null이어야 한다. 기본값이 `nullable: false`라서 명시하지 않으면 최상위 카테고리 저장 시 FK 제약 위반이 난다.

둘째, 깊은 트리 조회다. TypeORM `find`의 `relations`로는 `['parent', 'parent.parent', 'parent.parent.parent']` 식으로 고정 depth를 지정해야 하는데, 트리 깊이가 동적이라면 이 방식은 쓸 수 없다. 이 경우 `getTreeRepository()`나 Raw 쿼리(CTE 활용)를 사용한다.

```typescript
// 재귀 CTE로 전체 트리 조회
const result = await dataSource.query(`
  WITH RECURSIVE category_tree AS (
    SELECT id, name, parent_id, 0 AS depth
    FROM category
    WHERE parent_id IS NULL
    
    UNION ALL
    
    SELECT c.id, c.name, c.parent_id, ct.depth + 1
    FROM category c
    INNER JOIN category_tree ct ON c.parent_id = ct.id
  )
  SELECT * FROM category_tree ORDER BY depth, id
`);
```

---

## cascade 옵션

cascade는 부모 엔티티 조작 시 자식 엔티티에 자동으로 같은 작업을 전파하는 옵션이다.

```typescript
@OneToMany(() => Comment, (comment) => comment.post, {
  cascade: ['insert', 'update', 'remove', 'soft-remove', 'recover'],
})
comments: Comment[];
```

개별 옵션 지정이 가능하고, `cascade: true`는 `['insert', 'update', 'remove', 'soft-remove', 'recover']` 전부를 의미한다.

### cascade: true 의 데이터 삭제 함정

`cascade: true`를 무심코 달아놓으면 부모를 삭제할 때 연관된 자식이 전부 삭제된다. 개발 환경에서 시드 데이터가 적을 때는 "편하다"고 느끼다가, 운영 환경에서 사용자 한 명을 탈퇴 처리했는데 해당 사용자의 주문 내역이 전부 날아가는 경우가 생긴다.

```typescript
// 위험한 패턴
@OneToMany(() => Order, (order) => order.user, {
  cascade: true,  // user 삭제 시 order 전부 삭제
})
orders: Order[];

// 안전한 패턴
@OneToMany(() => Order, (order) => order.user, {
  cascade: ['insert'],  // 저장할 때만 전파
})
orders: Order[];
```

주문 같은 비즈니스 데이터는 사용자가 탈퇴해도 보존해야 한다. `cascade: ['insert']`만 쓰거나 cascade를 아예 쓰지 않는 편이 안전하다.

### onDelete 옵션과 cascade의 차이

`cascade`는 TypeORM 레벨에서 동작하고, `onDelete`는 DB FK 제약 레벨에서 동작한다.

```typescript
@ManyToOne(() => Post, (post) => post.comments, {
  onDelete: 'CASCADE',  // DB FK 레벨 CASCADE
})
post: Post;
```

`onDelete: 'CASCADE'`를 쓰면 TypeORM을 거치지 않고 DB가 직접 자식 레코드를 삭제한다. TypeORM의 Soft Delete 훅이 실행되지 않아서, Soft Delete를 쓰는 테이블에 `onDelete: 'CASCADE'`를 달면 자식이 물리적으로 삭제되어 버린다.

---

## Soft Delete와 관계 조회 충돌

`@DeleteDateColumn()`으로 Soft Delete를 구현하면 관계 조회가 깨지는 케이스가 생긴다.

### 문제 상황 1: 관계 로딩 시 삭제된 자식도 포함

```typescript
@Entity()
export class Post {
  @PrimaryGeneratedColumn()
  id: number;

  @DeleteDateColumn()
  deletedAt: Date | null;

  @OneToMany(() => Comment, (comment) => comment.post)
  comments: Comment[];
}

@Entity()
export class Comment {
  @PrimaryGeneratedColumn()
  id: number;

  @DeleteDateColumn()
  deletedAt: Date | null;

  @ManyToOne(() => Post, (post) => post.comments)
  post: Post;
}
```

`postRepository.findOne({ where: { id: 1 }, relations: ['comments'] })`를 실행하면 `comments`에 `deletedAt`이 있는 댓글도 포함된다. TypeORM은 기본 `find` 쿼리에 `WHERE deletedAt IS NULL`을 붙이지만, 관계 로딩 시 조인되는 자식 테이블에는 이 조건이 자동으로 붙지 않는 버전이 있다.

버전에 따라 다르게 동작하는데, TypeORM 0.3.x 기준으로 `relations`로 로딩한 자식에는 `withDeleted` 설정 없이도 삭제된 레코드가 포함될 수 있다.

```typescript
// QueryBuilder로 명시적 처리
const post = await postRepository
  .createQueryBuilder('post')
  .leftJoinAndSelect('post.comments', 'comment', 'comment.deletedAt IS NULL')
  .where('post.id = :id', { id: 1 })
  .getOne();
```

### 문제 상황 2: 부모가 Soft Delete됐는데 자식 조회 가능

`commentRepository.find({ where: { post: { id: 1 } } })`로 조회할 때 post가 Soft Delete 상태면 TypeORM이 자동으로 필터링하지 않는다. 댓글 테이블에는 `deletedAt`이 없기 때문에 삭제된 포스트의 댓글이 정상적으로 반환된다.

```typescript
// 명시적으로 부모 상태 체크
const comments = await commentRepository
  .createQueryBuilder('comment')
  .innerJoin('comment.post', 'post', 'post.deletedAt IS NULL')
  .where('post.id = :postId', { postId: 1 })
  .getMany();
```

### 문제 상황 3: cascade soft-remove가 전파 안 되는 케이스

`cascade: ['soft-remove']`를 설정해도 `remove()` 메서드를 쓰면 cascade가 동작하지 않는다. `softRemove()`를 써야 한다.

```typescript
// soft-remove cascade가 동작하지 않음
await postRepository.remove(post);

// soft-remove cascade 정상 동작
await postRepository.softRemove(post);
```

`remove()`와 `softRemove()`는 내부적으로 다른 cascade 체인을 타기 때문에, Soft Delete를 전파하려면 반드시 `softRemove()`를 사용해야 한다.

---

## 정리

TypeORM 관계 매핑에서 실수가 잦은 지점은 크게 세 군데다.

첫째, `@JoinColumn()` 위치다. owning side에만 붙여야 하고, 잘못 붙이면 FK가 엉뚱한 테이블에 생기거나 관계 조회가 깨진다.

둘째, `cascade: true` 남발이다. 편하다고 달아놓으면 부모 삭제 시 자식이 전부 날아간다. 운영 데이터에서 이 문제가 터지면 복구가 어렵다.

셋째, Soft Delete와 관계 로딩의 조합이다. TypeORM이 자동으로 처리해주지 않는 경우가 있어서 QueryBuilder로 명시적으로 필터링해야 한다. `find` 옵션만 믿으면 삭제된 데이터가 관계 로딩 결과에 포함되는 상황이 생긴다.
