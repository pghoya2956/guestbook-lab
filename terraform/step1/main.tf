# 2학년 9단원 1단계: VPC 하나를 코드로 만든다.
# 대역 10.1.0.0/16 은 콘솔로 만든 lab2 VPC(10.0.0.0/16)와 겹치지 않게 골랐다.
terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.68"
    }
  }
}

provider "aws" {
  region = "ap-northeast-2"
}

resource "aws_vpc" "main" {
  cidr_block = "10.1.0.0/16"
  tags       = { Name = "tf-lab" }
}

output "vpc_id" {
  value = aws_vpc.main.id
}
