
# Git
- 0년차 개발자를 지나 어느덧 1년차 개발자가 되었;'
- 다.. 하지만 개발자에게 필수인 Git에 대해 완벽히
이해하고 있냐? 라고 누군가 질문한다면 나는 아니다라고 대답할 것 같다.
- 따라서 이번 페이지는 Git에 대한 사용법을 알아보고자 한다.


# Git의 사전적 정의
- Git은 매우 빠른 속도와 분산형 저장소 지원이 특징이다. 
- 방대한 Linux 커널 소스 코드를 생각해 보면, 속도 문제는 매우 중요하다.
- 오픈 소스 개발의 특성상 여럿이 달려들어 자기 맘에 드는 걸 하기도 하며, 또한 뭘 하나 잘못 붙였다 이상한 걸 건드려 망하기 쉬운데, Git는 이런 환경의 특성에 맞게끔 잘 만들어져 있다.
- Git clone으로 프로젝트를 클론한 후 빌드해볼 수 있으며, 전체 저장소를 클론하고 싶지 않다면 kernel.org에서 원하는 버전의 tar파일을 찾아서 다운로드 할 수 있다.

# 저장소 받아오기
로컬 저장소를 복제(clone)하려면?

    git clone /로컬/저장소/경로

원격 서버의 저장소를 복제(clone)하려면?

    git clone 사용자명@호스트:/원격/저장소/경로

# 작업의 흐름
- 여러분의 로컬 저장소는 git이 관리하는 세 그루의 나무로 구성되어 있습니다.
- 첫번째 나무인 작업 디렉토리(Working directory)는 실제 파일들로 이루어져 있습니다.
- 두번째 나무인 인덱스(Index)는 준비 영역(staging area)의 역할을 하며,
- 마지막 나무인 HEAD는 최종 확정본(commit)을 나타내요

![](../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_nlkVjw/스크린샷 2022-12-23 오전 12.21.57.png)


# 추가와 확정
- 변경된 파일은 아래 명령어로 (인덱스에) 추가할 수 있습니다.

      git add <파일 이름>
      git add *

- 이것이 바로 git의 기본 작업 흐름에서 첫 단계에 해당됩니다.
- 인덱스에 추가된 내용을 실제로 확정하려면 아래 명령어를 내려야합니다.
       
       git commit -m "이번 확정본에 대한 설명"
    
- 이렇게 add > commit을 진행했다면 변경된 파일이 Head에 반영되었지만, 원격 저장소에는? 아직 반영이 안되었습니다.


# 변경 내용 발행(push)하기
- 현재의 변경 내용은 아직 로컬 저장소의 HEAD 안에 머물고 있어요.
- 변경 내용을 원격 서버로 올려봅시다. 아래 명령을 실행하세요.

        git push origin master

- 만약에 다른 Branch를 Push하려면 master를 원하는 가지 이름을 바꾸시면 됩니다.

        git push origin <Branch>

- 만약 기존에 있던 원격 저장소를 복제한 것이 아니라면, 원격 서버의 주소를 git에게 알려줘야 해요.
- 원격 저장소 복제가 아니라면? 아래의 명령어를 실행하세요

        git remote add origin <원격 서버 주소>

# Branch
- Branch의 필요성을 요새 많이 느낀다. 협업을 하면서 팀원과 나의 업무가 conflict가 난다면 대응하기 힘들 것이다.
- 따라서 Branch는 안전하게 격리된 상태에서 무언가를 만들 때 사용됩니다.
- 여러분이 저장소를 새로 만들면 기본으로 master 가지가 만들어집니다.
- 이제 다른 가지를 이용해서 개발을 진행하고, 나중에 개발이 완료되면 master 가지로 돌아와 병합하면 돼요.

![](../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_oKBfyn/스크린샷 2022-12-23 오전 12.34.27.png)


- 아래 명령으로 "feature_x"라는 이름의 가지를 만들고 갈아탑니다.

       git checkout -b feature_x


- 아래 명령으로 master 가지로 돌아올 수 있어요.
  
       git checkout master

- 아래 명령으로는 가지를 삭제할 수 있어요.
   
       git branch -d feature_x

- 여러분이 새로 만든 가지를 원격 저장소로 전송하기 전까지는 다른 사람들이 접근할 수 없어요.
    
       git push origin feature_x


# 갱신과 병합(merge)

- 여러분의 로컬 저장소를 원격 저장소에 맞춰 갱신하려면 아래 명령을 실행하세요.

       git pull

- 이렇게 하면 원격 저장소의 변경 내용이 로컬 작업 디렉토리에 받아지고(fetch), 병합(merge)된답니다.

- 다른 가지에 있는 변경 내용을 현재 가지(예를 들면, master 가지)에 병합하려면 아래 명령을 실행하세요.

       git merge <가지 이름>




# 출처 모음
- https://namu.wiki/w/Git
- http://rogerdudler.github.io/git-guide/index.ko.html