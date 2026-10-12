#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""结构层检查：这个 skill 能不能被 DSH 发现、装得对不对。

**为什么必须有这个脚本**（不是洁癖）：
DSH 的 skill provider 对不合法的条目是**静默丢弃**的——非法 `name`、缺 `description`、
布尔字段拼错，都只是写一条 logger warning，模型侧目录里**看不到任何诊断**。
也就是说"skill 没生效"和"skill 不存在"在界面上长得一模一样。
所以判据必须落在磁盘上，能跑、能红、能反证。

用法：
    python3 检查结构.py              # 查源 + 查安装态
    python3 检查结构.py --selftest   # 反证：故意做坏的样本必须红，做对的必须绿

退出码（与引擎同款四态）：
    0 全部通过 ／ 1 有失败 ／ 2 **没验成**（例如还没安装——那不是绿）
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'skills', 'judgment-engine')
AGENTS_SKILLS = os.path.join(os.path.expanduser('~'), '.agents', 'skills')
INSTALLED = os.path.join(AGENTS_SKILLS, 'judgment-engine')

#: 本机 14 个 skill **无一使用** `allowed-tools`；本项目也刻意不用
#: （本机惯例是正文写明命令与边界）。`disable-model-invocation` 会让本 skill
#: 从模型技能目录里消失，与"要能被自动触发"的目标冲突。
FORBIDDEN_KEYS = ('allowed-tools', 'disable-model-invocation')
REQUIRED_KEYS = ('name', 'description', 'whenToUse')
NAME_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')


def parse_frontmatter(text):
    """返回 (dict, 错误列表)。只认文件开头的 `---` 块，不引第三方 yaml。"""
    errs = []
    lines = text.split('\n')
    if not lines or lines[0].rstrip('\r') != '---':
        return {}, ['缺少 YAML frontmatter（文件必须以单独一行 --- 开头）']
    end = None
    for i in range(1, len(lines)):
        if lines[i].rstrip('\r') == '---':
            end = i
            break
    if end is None:
        return {}, ['frontmatter 没有结束的 ---']
    data = {}
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        if ':' not in raw:
            errs.append('frontmatter 这一行不是 key: value —— %r' % raw)
            continue
        k, _, v = raw.partition(':')
        k = k.strip()
        v = v.strip()
        if '# ' in v or v.startswith('#'):
            errs.append('值里疑似行尾注释，YAML 会吃掉后半截 —— %r' % raw)
        if k in data:
            errs.append('重复的键 —— %s' % k)
        data[k] = v
    return data, errs


def check_skill(dirpath, want_name='judgment-engine'):
    """对一个 skill 目录跑全部结构判据。返回问题列表（空 = 通过）。"""
    problems = []
    skill_md = os.path.join(dirpath, 'SKILL.md')
    if not os.path.isfile(skill_md):
        return ['缺 SKILL.md（发现规则只认 <名字>/SKILL.md 或顶层 <名字>.md）']

    with open(skill_md, encoding='utf-8') as f:
        text = f.read()
    fm, errs = parse_frontmatter(text)
    problems += errs

    for k in REQUIRED_KEYS:
        if k not in fm:
            problems.append('frontmatter 缺必填/约定键 —— %s' % k)
        elif not fm[k]:
            problems.append('frontmatter 的 %s 是空值（空值等同没有）' % k)

    name = fm.get('name', '')
    if name and not NAME_RE.match(name):
        problems.append('name 不是 kebab-case（provider 会**静默丢弃**整条）—— %r' % name)
    if name and name != os.path.basename(dirpath.rstrip('/')):
        problems.append('name 与目录名不一致（会造成同名遮蔽，且无 API 可查）—— %r vs %r'
                        % (name, os.path.basename(dirpath.rstrip('/'))))
    if want_name and name and name != want_name:
        problems.append('name 不是约定的 %r —— %r' % (want_name, name))

    desc = fm.get('description', '')
    if desc:
        if ': ' in desc:
            problems.append('description 里有 ASCII 冒号+空格，YAML 会把它当成映射——请改全角')
        if '不用于' not in desc:
            problems.append('description 里没有「不用于」——没有反例边界的 skill 只会被误触发')
        if len(desc) < 60:
            problems.append('description 太短，触发面说不清（本机同类 skill 都在 60 字以上）')

    for k in FORBIDDEN_KEYS:
        if k in fm:
            problems.append('出现了本项目约定不用的键 —— %s' % k)

    # 锚点匹配前先剥掉 Markdown 强调符与空白：标题里写 `**不**该用它` 也是同一个锚点，
    # 判据要盯"说了没有"，不是盯"怎么排版的"。
    body = text.split('---', 2)[-1]
    body_norm = body.replace('*', '').replace('`', '').replace(' ', '').replace('\u3000', '')
    for anchor in ('退出码', '处置卡', '不该用它'):
        if anchor not in body_norm:
            problems.append('正文缺关键锚点 —— %s（正文是给 agent 读的操作面）' % anchor)
    if len(body.strip()) < 500:
        problems.append('正文过短（<500 字），大概率没写清"怎么调、怎么读"')

    # 会漂的硬编码：正文里出现写死的项数。
    # 例外：**讲"不要写死数字"这件事本身**必然要引用数字——那一行里有否定/取证词就放过。
    neg = ('不要', '不许', '禁止', '别写', '曾写', '例如', '比如', '如「')
    for line in body.split('\n'):
        if any(w in line for w in neg):
            continue
        for m in re.finditer(r'\d+\s*[项条]', line):
            problems.append('正文写死了会漂的数字 —— %r；引擎文档明文禁止，'
                            '改成"跑 --stats 取值"' % m.group(0))
    return problems


def check_installed():
    """返回 (状态, 说明)。状态 ∈ {'ok','not-installed','broken','other-copy'}。

    `other-copy` 是个**独立状态**，不是失败：你手上这一份源**不是**已安装的那一份
    （典型场景：从 GitHub 下载了第二个副本、或在别处 clone 了一份来跑检查）。
    这时候既不能说"装对了"，也不能说"装坏了"——只能如实说**没验成**。
    之所以要单列，是因为干净房间测试里它曾经退 1：一个下载副本跑自己的检查器
    却报"失败"，那是**假红**，会把人引去修一个不存在的问题。
    """
    if not os.path.lexists(INSTALLED):
        return 'not-installed', '未安装：%s 不存在' % INSTALLED
    if not os.path.islink(INSTALLED):
        return 'ok', '已安装（实体目录，非软链）：%s' % INSTALLED
    target = os.path.realpath(INSTALLED)
    if not os.path.isfile(os.path.join(target, 'SKILL.md')):
        return 'broken', '软链断了：%s → %s 里没有 SKILL.md' % (INSTALLED, target)
    if target != os.path.realpath(SRC):
        return 'other-copy', ('已安装的是**另一份副本**：%s → %s（本份源在 %s）'
                              % (INSTALLED, target, SRC))
    return 'ok', '软链正确：%s → %s' % (INSTALLED, target)


def run_selftest():
    """反证：坏样本必须红。**没有这一段的检查器可能只是在空转。**"""
    good = '''---
name: judgment-engine
description: 这是一段刻意写长的合法描述，用来当反证的对照组，长度必须超过六十个字符，否则判红。当一个 skill 的 description 说不清触发面时，模型就只会在碰巧的时候才想起它。不用于做别的事情。
whenToUse: 什么时候用它的时候。
---

## 退出码
## 处置卡
## 什么时候不该用它
''' + '正文占位。' * 100 + '\n'

    cases = [
        ('合法样本', good, False),
        ('name 非 kebab-case', good.replace('name: judgment-engine', 'name: Judgment_Engine'), True),
        ('缺 description', '\n'.join(l for l in good.split('\n') if not l.startswith('description:')), True),
        ('description 无「不用于」', good.replace('不用于做别的事情。', '只做这一件事。'), True),
        ('description 含 ASCII 冒号', good.replace('这是一段刻意写长', '这是一段刻意写长: '), True),
        ('出现 disable-model-invocation', good, True),
        ('写死项数', good.replace('正文占位。', '共 29 项。正文占位。'), True),
    ]
    tmp = tempfile.mkdtemp(prefix='skill-struct-')
    bad = 0
    try:
        for label, text, want_red in cases:
            d = os.path.join(tmp, 'judgment-engine')
            shutil.rmtree(d, ignore_errors=True)
            os.makedirs(d)
            with open(os.path.join(d, 'SKILL.md'), 'w', encoding='utf-8') as f:
                f.write(text)
            if label == '出现 disable-model-invocation':
                text2 = text.replace('whenToUse:', 'disable-model-invocation: true\nwhenToUse:')
                with open(os.path.join(d, 'SKILL.md'), 'w', encoding='utf-8') as f:
                    f.write(text2)
            probs = check_skill(d)
            got_red = bool(probs)
            flag = '✓' if got_red == want_red else '✗'
            if got_red != want_red:
                bad += 1
            print('  %s %-28s 期望%s，实际%s%s' % (
                flag, label, '红' if want_red else '绿', '红' if got_red else '绿',
                ('  ← ' + probs[0]) if (got_red and not want_red) else ''))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return bad


def main():
    if '--selftest' in sys.argv:
        print('反证检查器本身（坏样本必须红、好样本必须绿）：')
        bad = run_selftest()
        print('\n%s' % ('反证通过：检查器确实能红' if bad == 0 else
                        '反证失败 %d 例 —— 检查器有洞' % bad))
        return 0 if bad == 0 else 1

    print('=== 结构检查 ===')
    print('源：%s' % SRC)
    problems = check_skill(SRC)
    for p in problems:
        print('  ✗ %s' % p)
    if not problems:
        print('  ✓ 源结构通过（frontmatter 合法、name kebab-case、description 带反例边界）')

    state, note = check_installed()
    print('  %s 安装态：%s' % ({'ok': '✓', 'not-installed': '–', 'other-copy': '–',
                               'broken': '✗'}[state], note))

    if problems:
        print('\n结论：结构 ✗（退出码 1）')
        return 1
    if state == 'not-installed':
        print('\n结论：结构 ✓，但**安装态没验成**（退出码 2）——'
              '软链到 ~/.agents/skills 之前，它在 DSH 里不可见。')
        return 2
    if state == 'other-copy':
        print('\n结论：结构 ✓，但**安装态没验成**（退出码 2）——'
              '本份源并不是已安装的那一份。要装它，先删旧软链再重建。')
        return 2
    if state == 'broken':
        print('\n结论：结构 ✓，安装态 ✗（退出码 1）——软链断了，去重建。')
        return 1
    print('\n结论：结构与安装态都通过（退出码 0）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
