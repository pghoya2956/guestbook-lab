# 메뉴 7(심화). VPC 를 코드로 다시 만들기

쓰는 서비스: CloudShell, Terraform · 완료 기준: `terraform apply` 로 손으로 만든 것과 같은 구조(서브넷 2개, 인터넷 게이트웨이, 경로)가 생긴다

2학년과 빨리 끝낸 학생용입니다. 10단원에서 손으로 만든 VPC 를 코드로 다시 만들고, 한 번에 지워 봅니다.

## 바뀌는 구조

콘솔에서 클릭하던 것을 파일에 적어 두면, 같은 구조를 몇 번이든 똑같이 만들고 지울 수 있습니다. 대역은 손으로 만든 `guestbook-vpc`(10.0.0.0/16)와 겹치지 않게 10.1.0.0/16 을 씁니다.

## 만들 것

1. 콘솔 위쪽의 CloudShell 아이콘을 눌러 엽니다(리전이 서울인지 확인).
2. 저장소를 받고 Terraform 을 설치합니다.

```bash
git clone https://github.com/pghoya2956/guestbook-lab.git
bash guestbook-lab/terraform/setup-terraform.sh
```

3. 1단계: VPC 하나만 만듭니다.

```bash
cd guestbook-lab/terraform/step1
terraform init
terraform plan      # 무엇이 생길지 먼저 읽는다: + aws_vpc.main
terraform apply     # yes
```

4. 2단계: `step1/main.tf` 에 퍼블릭 서브넷 2개, 인터넷 게이트웨이, 경로표를 직접 더해 봅니다. 막히면 정답 `../step2/main.tf` 를 봅니다. 고칠 때마다 `terraform plan` 으로 무엇이 바뀌는지 읽고 `apply` 합니다.

## 확인

VPC 콘솔의 리소스 맵에서 `tf-lab` VPC 가 손으로 만든 `guestbook-vpc` 와 같은 모양(서브넷 2개 → 경로표 → 인터넷 게이트웨이)인지 비교합니다.

마지막에 `terraform destroy` 로 한 번에 지웁니다. 손으로 지울 때와 비교해 봅니다.

## 막히면

- `terraform: command not found`: 2번 설치 스크립트를 다시 돌리고 안내대로 `source ~/.bashrc`
- `UnauthorizedOperation` 이나 `AccessDenied`: 리전이 서울(ap-northeast-2)인지 봅니다. 수업 계정은 서울만 씁니다
- `InvalidSubnet.Conflict`: 서브넷 대역이 겹칩니다. `cidrsubnet()` 으로 나눈 값을 확인합니다
- CloudShell 을 닫았다 열었으면 `cd guestbook-lab/terraform/step1` 로 돌아가면 상태 파일(`terraform.tfstate`)이 그대로 있습니다
