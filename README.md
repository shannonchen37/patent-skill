# patent-skill

从真实研发代码、设计文档、测试和实验记录中，提炼可追溯、可复核的中国专利撰写材料。

[GitHub 仓库](https://github.com/shannonchen37/patent-skill)

`patent-skill` 面向中国软件、算法、人工智能和计算机实现发明，支持：

- 发明点挖掘与技术交底；
- 工程证据链和现有技术分析；
- 权利要求、说明书与摘要草案；
- 支持性、优先权、修改依据、单一性和披露风险复核。

输出只用于发明人与中国专利专业人员复核，不代表法律意见，也不得标记为可直接提交。

## 在 ChatGPT 中使用

1. 在 GitHub 选择 **Code → Download ZIP**。
2. 在 ChatGPT 中进入 **插件 → 技能 → 创建 → 从计算机上传**。
3. 上传 `patent-skill` ZIP 完成 Skill 安装。
4. **另行上传一个独立的目标项目 ZIP**，其中包含已获授权使用的代码、设计文档、测试和实验材料。

`patent-skill` ZIP 只是工具，不是待申请项目。仅上传 Skill、尚未上传目标项目时，不要执行 `discover`。

如果看不到“技能”或“上传”入口，请检查套餐、工作空间权限或管理员设置。

首次使用 Prompt：

```text
使用 $patent-skill 对我单独上传的目标项目《PROJECT.zip》执行 discover。
《patent-skill》安装包及其中的 SKILL.md、references、scripts、schemas、assets、tests 和包源码只是工具，禁止作为待申请发明进行分析。
如果无法确认或访问《PROJECT.zip》，立即停止并要求我重新上传，不得改为分析 Skill 自身文件。
先检查申请背景、权属、公开情况和敏感信息，再分析技术问题、技术手段、技术效果及候选发明点。
输出工程证据和必须由发明人回答的问题，不要直接撰写权利要求。
```

## 在 Codex 中使用

安装为全局 Skill：

```bash
git clone \
  https://github.com/shannonchen37/patent-skill.git \
  ~/.codex/skills/patent-skill
```

更新：

```bash
git -C ~/.codex/skills/patent-skill pull
```

在 Codex 中打开待分析的真实代码仓库，而不是打开 `~/.codex/skills/patent-skill`，然后发送：

```text
使用 $patent-skill 对当前仓库执行 discover。
当前仓库是用户明确指定的目标研发项目；~/.codex/skills/patent-skill 及其文件只是工具，禁止作为待申请发明进行分析。
如果当前工作区不是独立的目标研发项目，立即停止并要求我选择正确仓库。
先检查申请背景、权属、公开情况和敏感信息，再分析技术问题、技术手段、技术效果及候选发明点。
输出工程证据和必须由发明人回答的问题，不要直接撰写权利要求。
```

Skill 可放在 `~/.codex/skills` 中跨仓库使用，并可通过 `$skill-name` 显式调用，参见 [OpenAI 官方 Codex Skill 指南](https://learn.chatgpt.com/use-cases/reusable-codex-skills)。

## 必要 Prompt

所有阶段都必须遵守：不得虚构技术事实、实验数据、现有技术、发明人、权属或日期；证据不足时应提问或停止；不得输出 `FILING_READY`。

### 1. 深入分析发明点

```text
使用 $patent-skill analyze P001。
基于已确认的发明点生成技术交底、工程证据链、初步权利要求骨架和检索式，并分别分析新颖性、创造性和单一性。
明确未核实事实与风险，不得拼接多篇文献直接否定新颖性。
```

### 2. 生成专利草案

```text
使用 $patent-skill draft P001。
仅依据已确认的技术事实和检索材料，生成权利要求 V1、说明书、实施例、摘要、权利要求 V2及支持矩阵。
不得加入研发材料中不存在的技术特征，所有输出标记为供发明人和专利代理师复核。
```

### 3. 最终复核

```text
使用 $patent-skill review P001。
复核权利要求 V2 的专利客体、新颖性、创造性、清楚性、支持性、单一性、优先权、修改依据、发明人权属和披露风险。
输出阻断问题、风险和人工确认清单，不得给出“可以直接提交”的结论。
```

## 模式

| 模式 | 用途 |
|---|---|
| `discover` | 扫描材料，抽象技术方案，形成候选发明点和问题清单 |
| `analyze P001` | 形成技术交底、权利要求骨架和现有技术分析 |
| `draft P001` | 生成权利要求、说明书、摘要及支持矩阵 |
| `draft P001 --pre-search` | 生成明确标记的检索前草案，不进入代理师复核状态 |
| `review P001` | 进行最终专利与披露风险复核 |
| `full` | 尝试全部阶段，并在证据或人工确认缺失处停止 |

## 可选命令行工具

需要 Python 3.11 或更高版本：

```bash
python -m pip install -e .
patent-skill scan /path/to/project --output ./patent-workspace
patent-skill validate ./patent-workspace
```

## 安全与边界

- 不要上传未经授权的公司机密、客户数据、密钥或受限制代码。
- 只有用户独立指定或上传的目标项目可以作为专利分析对象；Skill 自身文件永远不是目标项目。
- 工程证据、说明书支持、现有技术披露和优先权基础必须分别记录。
- 本项目不自动连接 CNIPA、Google Patents 或 Espacenet，也不提交专利申请。
- 专利性、发明人、权属、优先权和申请策略必须由专业人员最终判断。

## 相关文件

- [Skill 主入口](SKILL.md)
- [完整工作流](docs/workflow.md)
- [安全政策](SECURITY.md)
- [MIT License](LICENSE)
