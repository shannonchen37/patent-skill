# patent-skill

> 从真实研发代码、设计文档、测试与实验记录中提炼可追溯、可复核的中国专利撰写材料。

[GitHub 仓库](https://github.com/shannonchen37/patent-skill)

`patent-skill` 是面向中国软件、算法、人工智能和计算机实现发明的开源 Agent Skill。它把研发证据转化为发明点、工程证据链、权利要求、说明书、摘要及审查清单，同时明确区分：

- 工程来源证据；
- 说明书支持依据；
- 现有技术披露；
- 优先权基础。

本项目不会把 AI 输出标记为“可直接提交”。最终申请文件、申请策略、发明人和权属判断应由发明人与中国专利专业人员复核。

## 工作流程

```text
研发代码与工程材料
  → 申请背景、权属、披露和优先权信息
  → 仓库安全扫描与技术抽象
  → 专利客体适格性判断
  → 发明点挖掘与工程证据链
  → 发明人问题清单与技术交底书
  → 初步权利要求骨架
  → 有记录的现有技术检索
  → 新颖性、创造性与单一性分析
  → 权利要求 V1
  → 说明书、实施例与摘要
  → 权利要求 V2
  → 支持性、修改依据、优先权和披露风险复核
  → READY_FOR_ATTORNEY_REVIEW
```

## 使用 ChatGPT

根据 [OpenAI 官方的 ChatGPT 技能说明](https://help.openai.com/zh-hans-cn/articles/20001066)，符合条件的 ChatGPT 账号可以从电脑上传 Skill。个人 Skill 的可用范围取决于套餐、工作空间权限和管理员设置。

### 1. 下载 Skill

在 GitHub 仓库页面选择 **Code → Download ZIP**，或在本地执行：

```bash
git clone https://github.com/shannonchen37/patent-skill.git
```

### 2. 上传到 ChatGPT

1. 在 ChatGPT 边栏中选择 **插件**。
2. 进入插件目录的 **技能** 页面。
3. 选择 **创建 → 从你的计算机上传**。
4. 上传下载的 Skill 压缩包；确保压缩包中包含 `SKILL.md`、`references/`、`scripts/`、`schemas/` 和 `assets/`。
5. 等待 ChatGPT 完成安全扫描并安装。

如果你的账号看不到“技能”或“上传”入口，请检查工作空间套餐、角色权限或联系管理员。

### 3. 在 ChatGPT 中调用

安装完成后，可以直接描述任务，也可以显式指定 Skill：

```text
使用 $patent-skill 分析我上传的研发项目，先执行 discover 模式。
不要虚构技术事实、实验数据、现有技术、发明人或权属信息。
遇到证据缺失时，请输出问题清单，不要自行补全。
```

建议先上传或提供：

- 已获授权使用的源代码或代码摘录；
- 架构说明、设计文档和接口说明；
- 测试、实验记录和性能数据；
- 发明人提供的技术背景；
- 申请主体、首次公开、优先权和权属信息。

不要上传未经授权的公司机密、客户数据、凭据、密钥或受限制代码。

## 使用 Codex

[OpenAI 官方 Codex Skill 指南](https://learn.chatgpt.com/use-cases/reusable-codex-skills)说明，放在 `~/.codex/skills` 中的 Skill 可以在不同代码仓库中使用，并可通过 `$skill-name` 调用。

### 1. 安装为全局 Skill

```bash
git clone \
  https://github.com/shannonchen37/patent-skill.git \
  ~/.codex/skills/patent-skill
```

如已安装，可更新：

```bash
git -C ~/.codex/skills/patent-skill pull
```

### 2. 在 Codex 中打开真实研发仓库

让 Codex 的工作区指向待分析的代码仓库，然后发送：

```text
使用 $patent-skill 对当前代码仓库执行 discover。
先进行敏感信息与申请背景检查，再分析代码，不要直接生成权利要求。
```

完成发明点确认后，可继续：

```text
使用 $patent-skill analyze P001
```

```text
使用 $patent-skill draft P001
```

```text
使用 $patent-skill review P001
```

### 3. 可用模式

| 模式 | 作用 |
|---|---|
| `discover` | 收集申请背景，扫描仓库，抽象技术方案并形成发明候选与问题清单 |
| `analyze P001` | 形成技术交底、权利要求骨架、检索记录及新颖性/创造性分析 |
| `draft P001` | 在已有检索快照基础上生成权利要求 V1/V2、说明书和支持矩阵 |
| `draft P001 --pre-search` | 生成明确标记的检索前草案，不得进入代理师复核状态 |
| `review P001` | 复核权利要求、支持性、优先权、单一性、修改依据和披露风险 |
| `full` | 尝试执行全部阶段，在证据或人工确认缺失处停止 |

## 命令行工具

Python 3.11 或更高版本：

```bash
python -m pip install -e .
```

如需开发依赖和 DOCX 输出：

```bash
python -m pip install -e '.[dev,docx]'
```

常用命令：

```bash
patent-skill init-context
patent-skill scan /path/to/real-project --output ./patent-workspace
patent-skill status ./patent-workspace
patent-skill validate ./patent-workspace
patent-skill render ./patent-workspace P001
```

## 四类证据映射

| 映射 | 回答的问题 |
|---|---|
| 工程证据链 | 技术特征来自哪些代码、文档、测试或实验？ |
| 说明书支持 | 申请文件在哪里支持权利要求特征？ |
| 现有技术披露 | 已核实的单篇文献在哪里披露该特征？ |
| 优先权基础 | 优先权文件是否支持相同技术方案？ |

其中任何一种映射都不能自动证明另一种映射成立。

## 当前能力

已经实现：

- 安全扫描代码仓库并排除常见密钥、二进制和超大文件；
- 提取 Python、JavaScript、TypeScript、Go、Java、Rust、C/C++ 符号；
- 建立工程证据链、权利要求快照和检索快照；
- 检查新颖性分析中不当拼接多篇文献的问题；
- 检查中国权利要求引用关系、摘要长度和说明书支持；
- 检查修改依据、优先权基础、披露脱敏和工作区状态；
- 生成供中国专利代理师复核的 DOCX 草案；
- 提供完整的合成代码与专利工作区示例。

需要 Agent 和人工共同完成：

- 发明点选择与技术效果确认；
- 检索式设计、真实数据库检索和文献核实；
- 新颖性、创造性、单一性和保护范围判断；
- 说明书、实施例和权利要求策略；
- 发明人、权属、优先权和保密审查确认。

尚未实现：

- Google Patents、Espacenet 或 CNIPA 数据接口；
- 自动作出法律结论；
- CNIPA 电子申请提交；
- 审查意见答复流程。

## 示例

[自适应计算资源调度示例](examples/adaptive-compute-scheduler)是完全合成的演示项目。示例中的 D1 是测试夹具，不是真实专利文献，不能用于生产检索或专利性结论。

```bash
patent-skill validate \
  ./examples/adaptive-compute-scheduler/patent-workspace
```

## 隐私与安全

扫描器会排除常见敏感文件，但任何自动过滤都不可能覆盖全部风险。向 ChatGPT、Codex 或其他模型提供代码前，应确认：

- 你有权处理和上传这些材料；
- 已删除凭据、客户数据和无关商业秘密；
- 符合公司保密、知识产权、数据和模型使用政策；
- 面向外部的专利草案不包含内部路径和内部证据标注。

## 法律与专业声明

Patent-Skill 是研发分析和专利撰写辅助工具。本项目不提供法律意见，也不对专利性、新颖性、创造性、发明人身份、权属、优先权、申请策略、保密审查义务、数据合规或专利法律效力作最终判断。在提交中国专利申请或据此作出法律决策前，应由具备相应专业能力的专利专业人员进行审查。

## 项目文件

- [Skill 主入口](SKILL.md)
- [工作流说明](docs/workflow.md)
- [技术架构](docs/architecture.md)
- [贡献指南](CONTRIBUTING.md)
- [安全政策](SECURITY.md)
- [MIT License](LICENSE)
