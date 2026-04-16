# 🩺 Skill Doctor

> 当 AI 不知道怎么办时，它需要一个能问的地方。
> *When your AI doesn't know what to do, it needs somewhere to ask.*

![Skill Doctor Architecture](https://github.com/LpcPaul/skill-doctor/raw/main/hero_preview.png)

## 你是不是也遇到过这些情况：

> 装了一堆 skill，AI 总要来回折腾好久才能选对那一个——试错、切换、重试。时间浪费了，token 也烧完了。

> 我装了好几个做 PPT 的 skill，每个都说自己能做。但哪个更好？哪个更适合当前这份演示？每次 AI 和我都陷入迷茫。

> skill 调用失败了，AI 反过来问你"该怎么办"。可你装它就是为了不用操心这些——你也不知道怎么办。

**Skill Doctor 就是来解决这个问题的。**

它本身也是一个 skill，装上之后在 AI 背后默默工作：当 skill 选错了、冲突了、或者失败了，它负责搞清楚这次是谁的问题、应该怎么修，然后把答案给 AI 和你。

---

<details>
<summary>🌐 English Version</summary>

### Skill Doctor — Failure diagnosis for AI agent skills

You've probably been here before:

> You've installed a pile of skills, and your AI bounces between them forever trying to pick the right one — trying, switching, retrying. Time wasted. Tokens burned.

> You've got several skills that all claim to make slide decks. But which one is better? Which one fits this particular presentation? Every time, both you and your AI are stuck guessing.

> A skill call fails, and the AI turns around and asks you what to do. But the whole reason you installed skills was so you wouldn't have to think about this stuff — and you don't know either.

**Skill Doctor fixes this.**

It's a skill itself. Once installed, it works quietly in the background: when a skill gets picked wrong, conflicts with another skill, or fails outright, Skill Doctor figures out what went wrong, who's responsible, and what to do about it — and tells both you and your AI.

</details>

---

## 它是什么

Skill Doctor 本身就是一个 skill（meta-skill）。它运行在 agent 内部，做三件事：

1. **诊断** — 当 skill 失败或产出不符预期时，分类失败原因
2. **检索** — 从社区案例库中查找已知的类似问题和修复方案
3. **上报** — 用户确认后，将脱敏案例贡献回社区（可选）

## 安装

### Claude Code

```bash
# 克隆到个人 skill 目录（所有项目可用）
git clone https://github.com/LpcPaul/skill-doctor.git ~/.claude/skills/skill-doctor

# 或者克隆到项目级 skill 目录（仅当前项目可用）
git clone https://github.com/LpcPaul/skill-doctor.git .claude/skills/skill-doctor
```

### OpenClaw / ClawHub

```bash
# 如果已发布到 ClawHub
clawhub install LpcPaul/skill-doctor

# 或手动安装
git clone https://github.com/LpcPaul/skill-doctor.git
# 将 skill-doctor/ 目录放入你的 OpenClaw skills 目录
```

### Codex / Cursor / Gemini CLI

```bash
# SKILL.md 遵循 Agent Skills 开放标准，直接放入对应平台的 skills 目录
git clone https://github.com/LpcPaul/skill-doctor.git ~/.codex/skills/skill-doctor
```

## 使用方式

### 自动触发

Skill Doctor 会在检测到以下信号时自动激活：

- 工具调用返回错误
- 你说了"不对""换一个""重试"
- Agent 中途切换了 skill
- 输出明显不符合你的请求

### 手动触发

```
/skill-doctor
```

或直接问：

> "刚才那个 skill 为什么选错了？"
> "为什么生成了 Excel 而不是 markdown？"

### 贡献案例

诊断完成后，Skill Doctor 会问你是否愿意贡献案例。如果你同意：

1. 它会生成一份脱敏后的案例草稿
2. 展示给你确认（**不会自动提交**）
3. 运行本地脱敏脚本做二次检查
4. 通过 `gh` CLI 创建一条 GitHub Issue

前提：你需要已认证 GitHub CLI（`gh auth login`）。

## 案例库结构

```
cases/
  index.json          ← 所有案例的轻量索引（agent 优先读这个）
  by-skill/           ← 按 skill 分类的案例（xlsx.json, pdf.json, ...）
  by-type/            ← 按失败类型分类（wrong_skill_selected.json, ...）
schema/
  case.schema.json    ← 案例字段定义和约束
rules/
  failure_types.yaml  ← 失败类型分类法
scripts/
  redact.py           ← 确定性脱敏脚本（43 个单元测试覆盖）
  submit_case.sh      ← 提交脚本（调用 gh issue create）
hooks/
  tool_error_autodiagnose.sh  ← tool error 时自动触发诊断
  README.md           ← hooks 使用说明
tests/
  test_redact.py      ← redact.py 的 pytest 单元测试
```

## 隐私设计

Skill Doctor 采用**三层隐私保护**：

**第一层（模型层）**：SKILL.md 中明确指示 agent 只输出工程信息，不输出业务内容。

**第二层（确定性层）**：`redact.py` 脚本在提交前强制运行，自动检测并移除：
- 邮箱、手机号、API 密钥
- 文件路径、URL、IP 地址
- 业务关键词（季度报告、客户数据等）
- 任何超出 schema 定义的额外字段

如果检测到过多敏感内容，脚本会直接**阻止提交**。

**第三层（CI 层）**：GitHub Actions 对每条提交的 Issue 自动做二次验证。

## 失败类型

| 类型 | 说明 |
|---|---|
| `wrong_skill_selected` | 选错了 skill |
| `skill_conflict` | 多个 skill 争抢同一任务 |
| `skill_not_triggered` | 该触发的 skill 没触发 |
| `tool_error` | Skill 对了但底层工具报错 |
| `environment_issue` | 权限、包、网络、OS 问题 |
| `context_overflow` | 上下文太长导致 skill 指令丢失 |
| `description_mismatch` | Skill 描述与实际功能不符 |
| `should_use_hook` | 这个任务应该用 hook 而不是 skill |
| `output_quality` | Skill 执行了但输出质量差 |
| `unknown` | 无法判定 |

## 贡献

欢迎贡献案例！你可以：

1. **通过 Skill Doctor 自动提交**（推荐）— 使用 skill 内置的诊断+提交流程
2. **手动创建 Issue** — 使用 Issue 模板填写
3. **直接提 PR** — 在 `cases/` 目录下添加 JSON 文件并更新 `index.json`

所有案例必须：
- 通过 `redact.py` 脚本检查
- 符合 `schema/case.schema.json` 定义
- **不包含任何业务内容或用户个人信息**

## 路线图

- [x] v0.1 — 基础诊断 + 静态案例库 + GitHub Issue 提交
- [x] v0.2 — 案例库按 skill/type 拆分 + 案例扩充至 21 条
- [x] v0.2 — redact.py 单元测试覆盖（43 tests）+ hooks 集成
- [ ] v0.3 — 案例库自动索引生成（GitHub Actions）
- [ ] v0.4 — 支持按 skill 名 + 失败类型的模糊匹配检索
- [ ] v0.5 — OpenClaw ClawHub 正式发布
- [ ] v0.6 — 案例统计仪表盘（GitHub Pages）
- [ ] v1.0 — 跨 agent 案例共享协议

## 许可证

MIT

## 致谢

Skill Doctor 的灵感来自 SRE 领域的故障归因和修复检索思路：
把人类工程中的监控、故障分类、回归案例库、最佳实践检索搬到 AI agent 生态中。

---

*Skill Doctor 的第一用户不是人，而是 agent。人类是第二用户，负责审核、沉淀、修正规则。*
