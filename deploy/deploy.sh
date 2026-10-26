#!/bin/bash
# 이미지를 만들어 ECR 에 latest 로 올리고 ECS 서비스를 새로 배포한다(2학년 13단원).
# GitHub Actions 와 CloudShell 어디서든 같은 스크립트를 쓴다.
set -euo pipefail

REGION="${AWS_REGION:-ap-northeast-2}"
CLUSTER="${ECS_CLUSTER:-guestbook}"
SERVICE="${ECS_SERVICE:-guestbook}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
REGISTRY="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
REPO="${REGISTRY}/${ECR_REPO:-guestbook}"

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"
docker build -t "$REPO:latest" .
docker push "$REPO:latest"
aws ecs update-service --region "$REGION" --cluster "$CLUSTER" --service "$SERVICE" \
  --force-new-deployment --query 'service.deployments[0].status' --output text
