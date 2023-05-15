# 1. 인터페이스 개념과 역할


인터페이스란?
- 동일한 목적의 동일한 기능을 수행하도록 도와주는 것
- 자바의 다형성을 극대화하여 개발코드 수정을 줄이고 프로그램 유지보수성을 높이기 위해 인터페이스를 사용한다.

어떻게 사용할까?
- 인터페이스는 interface 키워드를 통해 선언

    
    public interface MemberRepository {

      Member save(Member member) 
      Optional<Member> findById(Long Id);
      Optional<Member> findByName(String name);
      List<Member> findAll();

      }

어떻게 구현할까?
- implements 키워드를 통해 일반 클래스에서 인터페이스를 구현


    package BootBase.Start.repository;
    
    import BootBase.Start.domain.Member;
    import java.util.HashMap;
    import java.util.List;
    import java.util.Map;
    import java.util.Optional;

    public class MemoryMemberRepository implements MemberRepository {

        private static Map<Long, Member> store = new HashMap<>();
        private static long sequence = 0L;


        @Override
        public Member save(Member member) {
            member.setId(++sequence);
            store.put(member.getId(), member);
            return member;
        }

        @Override
        public Optional<Member> findById(Long Id) {
            return Optional.ofNullable(store.get(Id));
        }

        @Override
        public Optional<Member> findByName(String name) {
            return store.values().stream()
                    .filter(member -> member.getName().equals(name))
                    .findAny();
        }

        @Override
        public List<Member> findAll() {
            return null;
        }
    }
