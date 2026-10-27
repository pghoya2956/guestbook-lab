#!/bin/bash
# CloudShell 에 Terraform 을 설치한다(2학년 9단원). 홈 디렉터리에 두므로 세션이 끝나도 남는다.
set -euo pipefail
V="${TF_VERSION:-1.14.7}"
case "$(uname -m)" in
  x86_64) ARCH=amd64 ;;
  aarch64|arm64) ARCH=arm64 ;;
  *) echo "지원하지 않는 CPU: $(uname -m)" >&2; exit 1 ;;
esac
mkdir -p "$HOME/bin"
cd "$(mktemp -d)"
curl -fsSLO "https://releases.hashicorp.com/terraform/${V}/terraform_${V}_linux_${ARCH}.zip"
unzip -o -q "terraform_${V}_linux_${ARCH}.zip" -d "$HOME/bin"
grep -q 'HOME/bin' "$HOME/.bashrc" 2>/dev/null || echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.bashrc"
"$HOME/bin/terraform" version
echo "새 창에서는 바로 terraform 을 쓸 수 있습니다. 지금 창에서는 source ~/.bashrc"
