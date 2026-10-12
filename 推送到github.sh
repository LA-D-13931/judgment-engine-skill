#!/usr/bin/env bash
# 把本仓库推到 GitHub。**退出码即结论**——失败时它不会说"已上 GitHub"。
#
# 用法：  bash 推送到github.sh
# 前置：  仓库已建（public），且本机有可用的 GitHub 凭据。
set -uo pipefail

REMOTE="${REMOTE:-https://github.com/LA-D-13931/judgment-engine-skill.git}"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$HERE" || exit 1

echo "== 0. 本地状态 =="
git status --short || exit 1
if [ -n "$(git status --porcelain)" ]; then
  echo "✗ 工作区不干净：先提交（本项目的规矩：提交信息一律 git commit -F 文件，" \
       "别用内联 -m——反引号会被 shell 吃掉）" >&2
  exit 1
fi

echo
echo "== 1. 远程可达性（网络/反代不通时，这一步就拦住，不会走到推送才失败）=="
if ! git ls-remote "$REMOTE" >/dev/null 2>&1; then
  echo "✗ 连不上 $REMOTE" >&2
  echo "  排查顺序（2026-10-12 实测有效）：" >&2
  echo "    ① 本机 /etc/hosts 把 github.com 指到 127.0.0.1，需要本地反代（如 Steam++）在跑；" >&2
  echo "    ② 反代没起来时，独立探测 github.com / api.github.com 都会是 000；" >&2
  echo "    ③ 只读下载的退路是 codeload tarball（见 README）。" >&2
  exit 2
fi
echo "✓ 远程可达"

echo
echo "== 2. 推送 =="
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE"
else
  git remote add origin "$REMOTE"
fi

if ! GIT_TERMINAL_PROMPT=0 git push -u origin "$BRANCH"; then
  echo "✗ 推送失败（凭据或权限问题）——**不要**对外声称已上 GitHub" >&2
  exit 1
fi

echo
echo "== 3. 复核（推送成功也要验，不信自己的退出码）=="
git ls-remote --heads origin "$BRANCH" >/dev/null 2>&1 \
  && echo "✓ 远程已能看到 $BRANCH" \
  || { echo "✗ 推完却读不到远程分支——以这条为准，推送不算成功" >&2; exit 1; }
echo
# 注意：变量名后用全角括号/标点时**必须加花括号**。
# bash 按字节解析标识符，UTF-8 的高位字节会被当成变量名的一部分，
# 于是 `$BRANCH）` 变成「名为 BRANCH）的变量」，`set -u` 下直接退出 1 ——
# 而推送其实已经成功了。**退出码与事实相反**，正是本项目最忌讳的那种假信号。
echo "✓ 完成：${REMOTE} （分支 ${BRANCH}）"
