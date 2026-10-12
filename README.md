# judgment-engine-skill

把**可复核判据引擎**（[verifiable-content-engine](https://github.com/LA-D-13931/verifiable-content-engine)）
封装成一个 agent skill。**引擎本体一行都没改**——这里只有"怎么调、怎么读、何时不用"。

## 它解决什么

引擎很强，但它的用法散落在十几个文档里：两条主命令、四个退出码各自的含义、
处置卡七字段、`--help` 不受支持、在它自己仓库里跑本来就该是红的……
agent 每次都要重新发现一遍，而且这个项目**记过账**：四态退出码里
**`2 没验成` 被当成 `0 通过`** 是它的头号老坑（`README.md` 里"跳过 ≠ 通过"是单独成条的）。

这个 skill 就是把这份操作面钉死成一次性的"告诉"。

## 装在哪

| 项 | 值 |
|---|---|
| skill 源 | `skills/judgment-engine/SKILL.md` |
| 生效位置 | `~/.agents/skills/judgment-engine`（DSH 用户级 skill 根，rank 500，所有工作区可见） |
| 安装方式 | **软链**过去，而不是复制——这样在仓库里改一个字，DSH 下一步就生效（provider 监听 depth 1 变更） |

```bash
ln -s "$(pwd)/skills/judgment-engine" "$HOME/.agents/skills/judgment-engine"
```

装完自检：

```bash
python3 检查结构.py          # 0 = 结构与安装态都通过；2 = **没验成**（比如还没装）
python3 检查结构.py --selftest   # 反证：故意做坏的样本必须红
```

## 更新

```bash
cd <这个仓库> && git pull
```

软链方式下**不需要重新安装**——源变了，DSH 下一步就重新读。
若你当初是复制安装的，就得重新复制一遍；用 `检查结构.py` 会告诉你软链指向哪。

## 卸载

```bash
rm "$HOME/.agents/skills/judgment-engine"     # 只删软链，仓库还在
```

## 隐私说明

- 本 skill **不含任何被检项目的内容**，也不上传任何东西；
- `SKILL.md` 里**刻意不写本机用户名**（用 `$HOME` 展开 + 环境变量 `JUDGMENT_ENGINE_HOME` 探测），
  所以它可以公开；
- `检查结构.py` 只读本地文件，唯一的写操作是 `--selftest` 在**系统临时目录**里造样本，跑完即删。

## 这个仓库里有什么

| 文件 | 作用 |
|---|---|
| `skills/judgment-engine/SKILL.md` | **交付物本体**（agent 读的那份） |
| `检查结构.py` | 结构层检查：能否被 DSH 收录、装得对不对；带 `--selftest` 反证 |
| `触发用例.md` | 语义层验收单（正例/反例话术 + 手工步骤）——**不可脚本化，别假装跑过** |
| `验收记录.md` | 本轮的实测证据（命令 + 退出码 + 输出摘录） |
| `待粘贴片段_SKILLS.md` | 给本机人工索引 `有意思的小项目工作站/SKILLS.md` 的待粘贴文本 |
| `推送到github.sh` | 一条命令推送（网络不通时它会明确报错，不会假绿） |
