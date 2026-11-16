# 2학년 14단원, 심화 메뉴 6 의 3단계: 2일차에 손으로 만든 네 단원(10~13단원)을 코드 한 벌로 만든다.
# terraform apply 한 번으로 만들고, 로드 밸런서 주소로 급식 앱을 본 뒤, terraform destroy 한 번으로 지운다.
#
# 이름은 모두 tf-day2 로 시작한다. 손으로 만든 guestbook-* 자원은 읽지도 바꾸지도 않는다.
# 예외는 둘이다. 4단원에서 만든 서버 역할 guestbook-ec2-role 을 이름으로 가리키고,
# 9단원에서 만든 내 공지 버킷 이름을 변수 notice_bucket 으로 받는다.
terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.68"
    }
    # Lambda 코드를 zip 으로 묶는 데만 쓴다
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
  }
}

provider "aws" {
  region = "ap-northeast-2"
}

# 학생이 바꿀 값은 이것 하나다. 9단원에서 만든 공지 버킷 이름(예: guestbook-notice-s01-1112)
variable "notice_bucket" {
  description = "9단원에서 만든 내 공지 버킷 이름. S3 버킷 목록에서 guestbook-notice- 로 시작하는 이름"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.notice_bucket))
    error_message = "버킷 이름은 영어 소문자, 숫자, 점, 하이픈만 씁니다. S3 버킷 목록에서 guestbook-notice- 로 시작하는 이름을 그대로 넣습니다."
  }
}

locals {
  name = "tf-day2"
  # 10단원의 public-a, public-c 자리. 로드 밸런서는 가용 영역 두 곳이 있어야 만들어진다
  azs = ["ap-northeast-2a", "ap-northeast-2c"]
}

# ───────────────────────────────────────────────
# 10단원 VPC: VPC, 퍼블릭 서브넷 2개, 인터넷 게이트웨이, 라우팅 테이블
# 대역 10.2.0.0/16 은 손으로 만든 guestbook-vpc(10.0.0.0/16), 1, 2단계 tf-lab(10.1.0.0/16)과 겹치지 않는다
# ───────────────────────────────────────────────

resource "aws_vpc" "main" {
  cidr_block = "10.2.0.0/16"
  tags       = { Name = local.name }
}

# 10.2.1.0/24(2a), 10.2.2.0/24(2c). 서브넷 설정 편집의 「퍼블릭 IPv4 주소 자동 할당」이 map_public_ip_on_launch 다
resource "aws_subnet" "public" {
  count                   = length(local.azs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index + 1)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true
  tags                    = { Name = "${local.name}-public-${substr(local.azs[count.index], -1, 1)}" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name}-igw" }
}

# 「라우팅 편집」에서 더한 0.0.0.0/0 → 인터넷 게이트웨이 줄
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "${local.name}-public-rt" }
}

# 「서브넷 연결 편집」에서 두 서브넷을 체크한 것
resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ───────────────────────────────────────────────
# 13단원 Lambda 와 API 게이트웨이: 급식실 한마디
# 시작 템플릿의 사용자 데이터가 이 API 주소를 HELLO_API_URL 에 적으므로 먼저 둔다
# ───────────────────────────────────────────────

# 13단원에서 편집기에 붙여 넣은 것과 같은 코드(저장소 lambda/hello/lambda_function.py)를 zip 으로 묶는다
data "archive_file" "hello" {
  type        = "zip"
  source_file = "${path.module}/../../lambda/hello/lambda_function.py"
  output_path = "/tmp/${local.name}-hello.zip"
}

# 콘솔이 함수를 만들 때 「기본 실행 역할」로 저절로 만들어 주던 역할. 로그를 남기는 권한만 있다
resource "aws_iam_role" "hello" {
  name = "${local.name}-hello-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "hello_logs" {
  role       = aws_iam_role.hello.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# 함수가 처음 불릴 때 저절로 생기는 로그 그룹을 미리 만들어 둔다. 그래야 destroy 가 같이 지운다
resource "aws_cloudwatch_log_group" "hello" {
  name              = "/aws/lambda/${local.name}-hello"
  retention_in_days = 1
}

# 「새로 작성」, 런타임 Python 3.13 으로 만든 함수
resource "aws_lambda_function" "hello" {
  function_name    = "${local.name}-hello"
  role             = aws_iam_role.hello.arn
  runtime          = "python3.13"
  handler          = "lambda_function.lambda_handler"
  filename         = data.archive_file.hello.output_path
  source_code_hash = data.archive_file.hello.output_base64sha256

  depends_on = [aws_iam_role_policy_attachment.hello_logs, aws_cloudwatch_log_group.hello]
}

# 「트리거 추가」의 새 API 생성, HTTP API, 보안 열기. target 을 주면 경로와 단계($default)가 함께 생긴다
resource "aws_apigatewayv2_api" "hello" {
  name          = "${local.name}-hello-api"
  protocol_type = "HTTP"
  target        = aws_lambda_function.hello.arn
}

# 트리거를 붙일 때 콘솔이 저절로 넣던 허가: 이 API 가 함수를 불러도 된다
resource "aws_lambda_permission" "hello_api" {
  statement_id  = "AllowHttpApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.hello.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.hello.execution_arn}/*"
}

# ───────────────────────────────────────────────
# 11단원 시작 템플릿: 서버 보안 그룹, 사용자 데이터, 서버 역할
# ───────────────────────────────────────────────

# 12단원 로드 밸런서 보안 그룹(guestbook-alb-sg 자리). 서버 보안 그룹이 이것을 가리키므로 먼저 둔다
resource "aws_security_group" "alb" {
  name        = "${local.name}-alb-sg"
  description = "tf-day2 alb"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name}-alb-sg" }
}

# 인터넷에서 오는 HTTP
resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"
}

# 12단원과 같이 HTTPS 도 연다. 브라우저가 https 로 먼저 열어 볼 때 바로 거절되어 http 로 돌아오게 하려는 것이다
resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

# 로드 밸런서가 서버로 요청을 넘기고 상태 검사를 하는 길
resource "aws_vpc_security_group_egress_rule" "alb_all" {
  security_group_id = aws_security_group.alb.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# 서버 보안 그룹(guestbook-web 자리). 11단원은 80 을 「위치 무관」으로 열었지만,
# 여기서는 로드 밸런서 보안 그룹에서 오는 80 만 받는다. 서버 공인 IP 로 바로 열면 열리지 않는다
resource "aws_security_group" "web" {
  name        = "${local.name}-web"
  description = "tf-day2 web"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name}-web" }
}

resource "aws_vpc_security_group_ingress_rule" "web_from_alb" {
  security_group_id            = aws_security_group.web.id
  ip_protocol                  = "tcp"
  from_port                    = 80
  to_port                      = 80
  referenced_security_group_id = aws_security_group.alb.id
}

# 서버가 dnf, git clone, pip, S3 공지, 한마디 API 를 부르러 나가는 길
resource "aws_vpc_security_group_egress_rule" "web_all" {
  security_group_id = aws_security_group.web.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# 「Quick Start」 → 「Amazon Linux」에서 고르던 Amazon Linux 2023 최신 이미지
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

resource "aws_launch_template" "web" {
  name                   = "${local.name}-lt"
  image_id               = data.aws_ami.al2023.id
  instance_type          = "t3.micro" # 수업 계정은 t3.micro, t3.small 만 켤 수 있다
  vpc_security_group_ids = [aws_security_group.web.id]

  # 「IAM 인스턴스 프로파일」에서 고르던 4단원 역할. 손으로 만든 것을 이름으로 가리키기만 한다
  iam_instance_profile {
    name = "guestbook-ec2-role"
  }

  # 11단원 사용자 데이터에 13단원 HELLO_API_URL 한 줄을 더한 대본. 빈칸은 Terraform 이 채운다
  user_data = base64encode(templatefile("${path.module}/user-data.sh.tftpl", {
    notice_bucket = var.notice_bucket
    hello_api_url = aws_apigatewayv2_api.hello.api_endpoint
  }))

  # 오토 스케일링이 켠 서버에 이름표를 붙인다. 손으로 만든 12단원 서버는 Name 칸이 비어 있었다
  tag_specifications {
    resource_type = "instance"
    tags          = { Name = "${local.name}-server" }
  }

  tags = { Name = "${local.name}-lt" }
}

# ───────────────────────────────────────────────
# 12단원 로드 밸런서와 오토 스케일링: 대상 그룹, Application Load Balancer, 오토 스케일링 그룹
# ───────────────────────────────────────────────

resource "aws_lb_target_group" "web" {
  name     = "${local.name}-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  # 「상태 검사 경로」를 /health 로 바꾼 것
  health_check {
    path    = "/health"
    matcher = "200"
  }

  # 서버를 뺄 때 기다리는 시간. 기본 300초를 줄여 destroy 를 빠르게 한다
  deregistration_delay = 30
}

# 체계 「인터넷 경계」, 가용 영역 2a 와 2c
resource "aws_lb" "web" {
  name               = "${local.name}-alb"
  load_balancer_type = "application"
  internal           = false
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  # 인터넷 경계 로드 밸런서는 서브넷에 인터넷 게이트웨이가 붙은 뒤에 만들어야 한다(지울 때는 반대 순서)
  depends_on = [aws_internet_gateway.main]
}

# 「리스너 및 라우팅」: 80 으로 온 요청을 대상 그룹으로 보낸다
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.web.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

# 원하는 2, 최소 2, 최대 4. 「Elastic Load Balancer 상태 확인 켜기」가 health_check_type = "ELB" 다
resource "aws_autoscaling_group" "web" {
  name                      = "${local.name}-asg"
  desired_capacity          = 2
  min_size                  = 2
  max_size                  = 4
  vpc_zone_identifier       = aws_subnet.public[*].id
  target_group_arns         = [aws_lb_target_group.web.arn]
  health_check_type         = "ELB"
  health_check_grace_period = 300

  # 두 서버가 대상 그룹에서 Healthy 가 될 때까지 apply 가 기다린다. 그래서 apply 가 끝나면 주소가 바로 열린다
  wait_for_elb_capacity = 2

  launch_template {
    id      = aws_launch_template.web.id
    version = aws_launch_template.web.latest_version
  }

  # 시작 템플릿을 고쳐 다시 apply 하면 서버를 새 판으로 하나씩 바꾼다
  instance_refresh {
    strategy = "Rolling"
  }

  # 서버가 인터넷으로 나가 앱을 받으려면 라우팅 테이블이 서브넷에 붙어 있어야 한다
  depends_on = [aws_lb_listener.http, aws_route_table_association.public]
}

# ───────────────────────────────────────────────
# 출력: apply 가 끝나면 맨 아래에 보인다. 다시 보려면 terraform output
# ───────────────────────────────────────────────

output "app_url" {
  description = "급식 앱 주소(로드 밸런서). 새 탭에서 연다"
  value       = "http://${aws_lb.web.dns_name}"
}

output "hello_api_url" {
  description = "급식실 한마디 API 주소(13단원 API 엔드포인트 자리)"
  value       = aws_apigatewayv2_api.hello.api_endpoint
}
