
todo 개념만 알도록 출처에서 가져왔으므로 재정리 필, 

# EFS란? 
- EC2에서 확장 사용 가능한 파일 스토리지
- 파일을 추가/제거할 때마다 스토리지 용량이 탄력적으로 자동 확장 및 축소
- Network File System 버전 4.0 및 4.1(NFSv4) 프로토콜 지원
- 한 리전 내 여러 가용 영역에 데이터 및 메타데이터 저장(페타바이트 규모까지 확장 가능)
- 강력한 데이터 일관성 및 파일 잠금 지원
- 파일 시스템 확장에 따라 처리량 및 IOPS가 늘어남
- VPC를 Direct Connect와 연결하면 EFS를 On-Premises 환경과 연결


## 사용조건 및 제약사항
- nfs-utils Deamon이 설치되어 있어야 함
- MS Windows에서는 EFS를 사용할 수 없음
