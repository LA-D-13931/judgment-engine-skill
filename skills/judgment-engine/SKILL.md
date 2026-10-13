---
name: judgment-engine
description: 用「可复核判据引擎」体检教学内容项目——跑它的命令、读它的四态退出码、把失败翻译成可直接交接的缺陷报告。用于「验收/体检某个教学内容站点、教材、讲义或实验项目」「核对内容与作者自己声明的判据是否一致」「要一份带证据与修法的缺陷清单」。不用于：判定内容对不对（数学与表述正确性仍需人）、替代被检项目自带的测试套件、修改被检项目的内容（它只报告，不改）。
whenToUse: 用户要求体检、验收、门禁某个教学内容项目，或要求产出一份可复核的缺陷报告（结论/证据/缺陷所在/照着谁改/改法/泛化/验证命令）时。
---

# 判定引擎

**它只做三件事：诊断 → 出证据 → 给修法。** 不生成内容、不画界面、不代改被检项目。

它的招牌是**退出码即结论**；最容易出事的地方**也是**这四个码——
**`2` 是「没验成」，不是「通过」**。把 2 读成绿，是这个引擎最典型的误用。

## 1. 先找到引擎，并报出版本

引擎是一个仓库，根下有两块：`apps/linalg-lab/`（判题域套件）与 `engine-core/`（引擎本体 + 适配层）。
**不知道用的是哪一版，结论就没有意义**，所以第 1 步永远包含"报版本"。

```bash
find_engine() {
  for c in "$JUDGMENT_ENGINE_HOME" "$HOME/Desktop/引擎开发工作区/工作台/线代交互实验台"; do
    [ -n "$c" ] && [ -f "$c/apps/linalg-lab/tools/verify-all.py" ] && { printf '%s\n' "$c"; return 0; }
  done
  d="$PWD"
  while [ "$d" != "/" ]; do
    [ -f "$d/apps/linalg-lab/tools/verify-all.py" ] && { printf '%s\n' "$d"; return 0; }
    d=$(dirname "$d")
  done
  return 1
}
ENGINE=$(find_engine) || { echo "未找到引擎（见下方「装一份」）"; exit 2; }
echo "引擎：$ENGINE"
git -C "$ENGINE" rev-parse --short HEAD 2>/dev/null \
  || echo "(非 git 副本；看 dist/ 里的 tar.gz 文件名里的版本与 commit)"
```

**装一份**（首选 `git clone`；`github.com` 不通时用下面的 tarball 通道，2026-10-12 实测返回 200 且解包正常）：

```bash
git clone https://github.com/LA-D-13931/verifiable-content-engine.git

# 或者（只读、免 clone）——**注意下面这条 caveat**
curl -sSL -o /tmp/engine.tgz \
  "https://codeload.github.com/LA-D-13931/verifiable-content-engine/tar.gz/refs/heads/main" \
  && tar xzf /tmp/engine.tgz
```

⚠️ **tarball 按「分支名」取会拿到缓存里的陈旧快照。** 2026-10-12 实测：
按 `main` 取的包比按 commit SHA 取的**小了一个提交的量**，加查询参数也不刷新；
换成**按 commit SHA 取**立刻拿到最新内容（sha256 与源一致）：

```bash
SHA=$(git -C "$ENGINE" rev-parse HEAD)   # 或从 GitHub 页面上的 commit 复制
curl -sSL -o /tmp/engine.tgz \
  "https://codeload.github.com/LA-D-13931/verifiable-content-engine/tar.gz/$SHA"
```

**所以第 1 步的"报出版本"不是仪式**：它是你唯一能发现"手里这份是旧快照"的手段。
拿到 tarball 之后先 `git log -1`（或看 `dist/` 里的文件名）确认版本，**再**下结论。

## 2. 第 0 步：先看缺什么，再谈结论

```bash
cd "$ENGINE/apps/linalg-lab" && python3 tools/就绪自检.py
```

它逐项列出缺什么、该补哪里（Python / Node / puppeteer-core / 浏览器 / 仓库外被检对象 / 材料线）。
**缺项时它退 2，而不是 0——缺项不是"通过"。**

## 3. 先问一句：**你的项目在不在声明里**（不在的话，后面全是白跑）

内容规范域**只判 `manifest.json` 里被声明过的产物**。那份 manifest 在引擎自己的目录下，
里面声明的来源**全是引擎自己的**（含它自己那批反证夹具）。所以：

- **你的项目不在声明里** ⇒ 引擎**判不了**它。这时候跑出来的任何失败**都与你无关**，
  **一条都不许往上报**。要让它判你的项目，得**写一份声明**（声明产物路径、判据、期望），
  **不是换个路径就行**。
- **已在声明里** ⇒ 用 `--source <id>` 缩到那一个来源。

⚠️ `--source` **确实在过滤**，但**表头恒印 manifest 的总量**：实测 `--source gaoshu-site`
的表头仍写「来源 6 ｜ 产物 78」，只有「判定 N 条」那一项变了（561 → 0）。
**别拿表头判断过滤生效没有——看判定数。**（这是引擎侧的报告缺陷，已如实记录，别当成自己用错。）

## 4. 跑两条主命令

```bash
# ① 套件自检：判题域 + 矩阵原语 + 静态站点内容
cd "$ENGINE/apps/linalg-lab" && python3 tools/verify-all.py --all

# ② 内容规范域：在「产物 × 检查」上逐条判定，失败处直接打印处置卡
cd "$ENGINE/engine-core/adapters/content-spec" && python3 runner.py --report --scope repo

# ③ 只想看某一个来源时（先确认它已在 manifest 里声明）
cd "$ENGINE/engine-core/adapters/content-spec" && python3 runner.py --report --scope repo --source <来源ID>
```

**不要给这些命令加 `--help`**：它不解析这个参数，会落到默认的全量自检（含浏览器项）上长时间无输出。
要选项清单就读 `runner.py` 顶部的模块 docstring。

## 5. 分辨「预期内的失败」和「真缺陷」——**不做这一步，你交出去的全是噪音**

`--report` 把两种失败**混在一起打印**，而且**不告诉你哪条是哪条**。判据在 `--json` 的 `expect` 字段里：

| 情形 | 含义 | 该怎么办 |
|---|---|---|
| `verdict == expect` | **设计如此**：这是一条**反证用的坏例**（C2 契约：每条检查必须先有一个能变红的例子） | **什么都别报** |
| `verdict != expect` | **真问题**：内容变了，或检查器坏了 | **这条才值得写进缺陷报告** |

**实测（2026-10-13，在引擎自己的 manifest 上）：`--scope repo` 的失败全部落在第一行，
`verdict != expect` 的条数为零。** 换句话说，在引擎自己仓库里跑出来的那些 ✗，
**没有一条是给用户看的**——上面的第 3 节已经说了为什么。

现场取这个数（别抄）：

```bash
cd "$ENGINE/engine-core/adapters/content-spec" && python3 runner.py --json --scope repo \
  | python3 -c "
import json,sys
v=json.load(sys.stdin)['verdicts']
bad=[x for x in v if x['verdict']=='fail' and x.get('expect')!='fail']
print('值得报的条数 =', len(bad))
"
```

名字里带 `-bad` / `-mutant` 的通常是夹具，但**别靠名字猜**：一个产物算不算夹具，
看 `manifest.json` 里的声明与它的 `expect`。

## 6. 四个退出码：唯一的读法

| 码 | 意思 | 你该做什么 |
|---|---|---|
| `0` | 通过 | 报告「通过」，并附上引擎版本与命令 |
| `1` | **失败**（真发现问题） | 先按第 5 节分清是不是预期内的；**剩下的**才逐条读 `reason` 与证书 |
| `2` | **没验成**（环境不足） | 按提示补齐后**重跑**；**不许当通过**，也不许当失败 |
| `3` | **检查器崩了**（引擎的 bug） | 不是被检内容的问题；报给引擎维护者 |

**「跳过 ≠ 通过」是这套东西的底线**：`–` 不适用是**自成一态**，不是没检测到的绿。

## 7. 失败了怎么读：只读处置卡

`runner.py --report` 在每条失败处打印**七字段处置卡**——照这个顺序读，不要自己重新组织：

| 字段 | 内容 |
|---|---|
| 结论 | 一句话说清违反了哪条判据 |
| 证据 | 判定所依据的实测事实（证书），可独立复核 |
| 缺陷所在 | `file:line`，精确到行 |
| 照着谁改 | 同一仓库里**已经做对的那一处**，照抄即可 |
| 改法 | 具体动作，含已知的坑 |
| 泛化 | 这类问题还会在哪些地方出现（不止修这一处） |
| 验证命令 | **可执行命令**；"我改了代码"不算修好 |

**你要交给用户的，就是把处置卡翻成这份格式的清单**，不要交原始输出（一次跑动辄上千行）。
机器可读的一份用 `--json`（含证书与 `expect`/`known_defect` 字段）。

## 8. 规模数字别抄，现场取

```bash
cd "$ENGINE/apps/linalg-lab" && python3 tools/verify-all.py --stats     # 套件项数等，JSON 单行
cd "$ENGINE/engine-core/adapters/content-spec" && python3 runner.py --json | python3 -c "import json,sys;print(json.load(sys.stdin)['tally'])"
```

**不要在报告里写死"29 项""561 条"**：数字随套件变化而失真（这个引擎的文档曾写「13 项」而实际已是 21 项）。
要写就写"取数命令 + 当时的输出"。

## 9. 什么时候**不**该用它

- **判内容对不对**：它只判形态与量测，数学与表述正确性仍需人。它是**审计员的裁判，不是审计员**。
- **当测试套件用**：它判的是"内容与作者声明的判据是否一致"，不是"代码功能是否正确"。
- **改被检项目**：它的产出是**可交接的缺陷报告**，不是补丁。**不要拿它的输出去改别人的仓库**——
  改由被检项目那条线的人做。
- **没有声明的地方**：判据是**声明驱动**的（见第 3 节）。被检产物要在 `manifest.json` 里被声明才会被验；
  没声明 = 没验，**不是通过**。内容规范域的 `manifest.json` 目前固定在该域目录下，
  换一个被检项目要**写一份声明**，不是改个路径就行。

## 10. 如果你手上是那个 `.zip`

离线包 `教学内容门禁引擎_给agent用.zip` 是同一引擎的**整仓快照（含 `.git`）**，入口是它自带的 `AGENTS.md`
与 `包说明.txt`（含 `校验清单.txt` 的 sha256）。**不是 DSH 环境时走它**；在 DSH 里就用本 skill。
两者是同一引擎的两条入口，不要混着引用。

## 11. 维护

- 本 skill 是**薄封装**：引擎本体在另一个仓库，这里只放"怎么调、怎么读、何时不用"。
- **改引擎不要在 skill 里改**：改引擎走引擎仓库自己的流程（它有 `AGENTS.md` 与套件）。
- 本文件的源在 `skills/judgment-engine/SKILL.md`，由 `检查结构.py` 守结构；
  触发话术的正反例见 `触发用例.md`。
- **第 3、5 节是实战补出来的**：2026-10-13 有个 agent 照着本 skill 跑，交回一份"缺陷报告"，
  里面全是引擎自己的反证夹具。原因不是它用错，是**本 skill 当时只说了一句散文警告、没给判据**。
  修复原则：**凡是"这样做会出错"的警告，必须同时给出"怎么分辨"的可执行判据**——
  否则它只是一句正确的废话。
