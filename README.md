# Patent Skill

**从真实软件、AI 与算法项目中提取工程证据，生成可追溯的中国发明专利案件包。**

Patent Skill 不是“把代码交给大模型，然后生成一篇专利”的工具。它先从真实代码和研发材料中恢复技术机制，再经过发明点筛选、现有技术检索、权利要求设计、说明书支持性追踪和结构化审计。

> Engineering evidence → Invention → Prior art → Claims → Specification → Support → Audit

[![CI](https://github.com/shannonchen37/patent-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/shannonchen37/patent-skill/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Why Patent Skill?

普通的一次性生成通常是：

```text
Source Code → LLM → Patent Draft
```

Patent Skill 使用证据优先、分阶段校验的路径：

```text
Source Code
    ↓
Engineering Evidence
    ↓
Invention Candidates
    ↓
Prior-art Search
    ↓
Claims & Specification
    ↓
Support Trace & Final Search
    ↓
Audit & Attorney Review
```

核心原则：

- **Evidence-first**：不能由代码、设计文档、测试、实验记录或用户确认支持的技术特征，不能凭空进入权利要求。
- **Search-before-claims**：在确定保护中心前先检索候选发明，最终权利要求形成后再次检索。
- **Claim traceability**：权利要求限定能够回溯到工程证据、说明书支持和对应技术效果。
- **Stale-analysis protection**：权利要求或最终申请内容发生实质修改后，旧检索和旧审计不能静默继续使用。

## Capabilities

| 能力 | 说明 |
|---|---|
| Engineering Evidence | 从源码、配置、测试和设计材料中恢复技术机制，而不是只依赖 README |
| Inventor Disclosure | 将尚未编码、但经发明人或开发者确认且达到充分公开要求的技术设计，与代码证据严格区分后纳入方案 |
| Invention Discovery | 从一个项目中挖掘多个候选发明，并筛选更值得保护的特征组合 |
| Prior-art Search | 在确定保护中心前检索，并在最终权利要求形成后再次检索 |
| Claims Engineering | 起草并校验中国发明专利独立权利要求与从属权利要求 |
| Specification Drafting | 根据权利要求和工程证据组织说明书、摘要及必要附图 |
| Support Traceability | 将权利要求限定关联到工程证据、说明书支持和技术效果 |
| Revision Control | 出现新现有技术或审稿意见时正式回退，并使旧分析失效 |
| Patent Audit | 检查新颖性、创造性、专利客体、支持性、充分公开和单一性等风险 |
| Attorney Review Package | 输出供中国专利专业人员继续复核和修改的案件材料 |

## Quick Start

### ChatGPT

1. 在 GitHub 选择 **Code → Download ZIP**，将本仓库 ZIP 作为 Skill 安装。
2. 上传真正需要分析的研发项目代码 ZIP，而不是再次上传 Patent Skill 安装包。
3. 发送：

```text
使用 $patent-skill 分析这个项目，
从工程证据开始挖掘可以申请的中国发明专利。
```

Patent Skill 不会直接从代码跳到专利全文。它会先冻结项目快照、建立工程证据，并仅在缺失信息会影响技术方案或保护范围时向你提问。

### Codex

安装：

```bash
git clone https://github.com/shannonchen37/patent-skill.git \
  ~/.codex/skills/patent-skill
```

在 Codex 中打开真实项目仓库，或提供项目的准确路径，然后发送：

```text
使用 $patent-skill 分析当前项目，
从代码证据开始生成中国发明专利案件。
```

Patent Skill 自身只是工具，永远不是待申请项目。更新已安装 Skill：

```bash
git -C ~/.codex/skills/patent-skill pull
```

## How It Works

```text
真实研发项目
    ↓
工程证据与技术机制
    ↓
候选发明筛选
    ↓
第一次现有技术检索
    ↓
权利要求与说明书
    ↓
支持性追踪与最终检索
    ↓
最终申请内容与结构化审计
    ↓
专利代理师复核
```

Patent Skill 使用分阶段工作流，而不是一次性生成。只有会实质影响发明点、区别特征、技术效果或保护范围的不确定内容才会阻断推进；申请人、地址等表单信息可以稍后填写。

完整流程、校验 Gate 和正式修订规则见 [工作流文档](docs/workflow.md)。普通 Skill 用户不需要手动管理内部状态；CLI 主要用于开发、调试和工作流集成，可运行：

```bash
python -m patent_skill.cli --help
```

## What You Get

| 最终材料 | 内容 |
|---|---|
| Patent Claims | 清除内部标记后的最终权利要求书 |
| Specification | 与最终权利要求和工程证据同步的说明书 |
| Abstract | 说明书摘要 |
| Figures | 技术方案确有需要时生成的附图和附图说明 |
| Prior-art Report | 检索记录、最接近现有技术和覆盖范围说明 |
| Claim Support Map | 权利要求与工程证据、说明书支持及技术效果的对应关系 |
| Patentability Audit | 新颖性、创造性、支持性和其他主要风险分析 |
| Review Package | 供中国专利代理师进一步修改和确认的案件材料 |

Patent Skill 维护唯一的案件事实源，并记录证据、检索、修订和审计之间的关系。完整案件结构与实现机制见 [架构文档](docs/architecture.md)。

## Scope

**适合的项目**

软件系统、AI/机器学习、算法系统、后端基础设施、调度、缓存、数据库、网络、数据处理，以及其他能够通过代码、设计文档、测试或实验记录提供工程证据的项目。

**不适合的场景**

- 只有抽象想法，没有可实施技术方案或研发材料；
- 要求模型虚构实验结果、实现细节或区别特征；
- 要求工具保证专利授权，或替代专利代理师作出最终法律判断。

## Optional Integrations

Patent Skill 的核心工作流可以独立运行。以下项目仅提供可选增强：

- **CNIPA search** — [yjmm10/patent-skills](https://github.com/yjmm10/patent-skills)：增强国知局检索；检索材料返回 Patent Skill 的案件记录。
- **Independent drafting review** — [HuangXinzhe/cn-patent-drafting](https://github.com/HuangXinzhe/cn-patent-drafting)：用于最终独立撰写审查和 DOCX 输出，不得覆盖既有工程证据、权利要求或案件状态。

这些工具不是三个并行的专利生成器。Patent Skill 始终维护唯一的案件事实源。

## Safety & Limitations

- 不要上传未经授权的公司机密、客户数据、账号凭据或密钥。
- 不虚构技术事实、实验数据、专利文献或区别特征。
- 不通过修改标题、替换术语或更换权利要求类别规避真实现有技术。
- 输出用于中国专利专业人员复核，不构成授权保证或法律意见。

任何检索都可能受到数据库覆盖、索引延迟、未公开申请和检索表达的限制。Patent Skill 会记录检索范围和残余风险，但不能承诺“绝对不撞车”。更多信息见 [安全政策](SECURITY.md)。

## Documentation

- [SKILL.md](SKILL.md) — Agent 执行规则和交互契约
- [完整工作流](docs/workflow.md) — 专利流程、Gate 与 revision 规则
- [架构说明](docs/architecture.md) — 案件事实源、Schema、证据链和外部集成
- [安全政策](SECURITY.md) — 代码、敏感信息和负责任披露
- [贡献指南](CONTRIBUTING.md) — 开发、测试和贡献方式

## Contributing

欢迎提交 Issue 和 Pull Request。开始前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)，并确保测试与静态检查通过。

## License

本项目采用 [MIT License](LICENSE)。
