# patent-skill

从真实研发代码、设计文档、测试和实验记录中提炼技术方案，主动找出证据缺口和矛盾，通过分阶段提问补齐上下文，再生成供发明人与中国专利专业人员复核的中国发明专利案件包。

`patent-skill` 是主流程和唯一案件事实源：

- [yjmm10/patent-skills](https://github.com/yjmm10/patent-skills) 仅用于增强 CNIPA 查新；
- [HuangXinzhe/cn-patent-drafting](https://github.com/HuangXinzhe/cn-patent-drafting) 仅用于最终独立审稿和分件 DOCX 输出；
- 三套工具不会并行撰写，也不会互相覆盖案件事实。

[GitHub 仓库](https://github.com/shannonchen37/patent-skill)

## 正确流程

Skill 不会收到代码后立即端到端生成专利。代码不能代替完整的技术交底；凡是会影响发明点、区别特征或权利要求范围的不确定内容，都需要用户确认。

```text
上传或指定真实代码
→ 询问拟用专利名称（没有则回复“无”）
→ 冻结证据版本（Git commit、上传 ZIP 或确定性目录清单）
→ 提取代码证据，指出“已证明/推断/缺失/矛盾”
→ 询问最关键的技术缺口并等待回答
→ 挖掘 3–5 个候选发明
→ 对候选发明做第一次查新（Shannon 主分析，yjmm10 可选增强 CNIPA）
→ 检索后排序；明显最优则继续，存在战略歧义时由用户确认主方向/拆案
→ 展示最接近现有技术和拟采用的区别特征，由用户确认
→ Claims V1 → 中国权利要求结构校验 → 用户确认独权技术链
→ 说明书 V1 → support-candidates → Claims V2 + 独权限定结构
→ claim-support-map 与独权限定逐项一致
→ 每项独权组合及关键区别限定的第二次检索和模拟审查
→ 内容达到 CONTENT_READY_FOR_ATTORNEY_REVIEW
→ Huang 独立审稿 → Shannon 逐项协调 → 经 OOXML 有效性检查的成套 DOCX
→ 中国专利代理师终审
```

每轮默认只问一个、最多三个问题，并解释该问题为什么会影响专利内容。不会要求用户操作内部阶段或理解候选编号。

申请人、发明人、地址、权属等信息不是内容生成门槛，缺少时统一保留 `【待填写】`。

专利名称只是用户意图和检索入口。名称相同不等于技术方案相同，名称不同也不代表不存在冲突；Skill 必须继续比较技术方案和权利要求。发现高度重合时，不得只换标题，而应寻找代码中真实存在的区别特征并重新检索；找不到时必须报告高重合风险。

由于数据库覆盖、索引延迟、未公开申请和检索误差，任何工具都不能保证“绝对不撞车”。本 Skill 输出有记录的检索范围、逐项特征对比和残余风险，不作零风险承诺。

## 在 ChatGPT 中使用

1. 在 GitHub 选择 **Code → Download ZIP**。
2. 在 ChatGPT 中上传 `patent-skill` ZIP 完成 Skill 安装。
3. 发送：

```text
使用 $patent-skill 开始生成中国发明专利。
```

Skill 会主动要求上传待分析项目的代码 ZIP。`patent-skill` 安装包只是工具，绝不能作为待申请项目。

收到项目后，Skill 应首先询问：

```text
你是否已有拟申请的专利名称？有则直接提供；没有请回复“无”，我将根据代码挖掘核心发明并生成候选名称。
```

用户回答后，Skill 先扫描证据并提出第一轮关键问题。后续按“证据确认→候选检索与排序→必要时方向确认→现有技术差异确认→权利要求范围确认”逐步推进，不要求用户操作 `discover`、`analyze`、`draft` 或候选编号。

## 在 Codex 中使用

安装：

```bash
git clone https://github.com/shannonchen37/patent-skill.git ~/.codex/skills/patent-skill
```

更新：

```bash
git -C ~/.codex/skills/patent-skill pull
```

在 Codex 中打开真实项目仓库，或提供准确路径，然后发送：

```text
使用 $patent-skill 根据当前项目生成中国发明专利内容包。
```

如果没有打开真实项目，Skill 会要求选择项目路径或上传代码。Skill 安装目录永远不是分析目标。

## 输出

```text
patent-case/
├── case-status.json
├── context-ledger.md
├── 00-project-snapshot/
├── 01-code-evidence-map.md
├── 02-invention-candidates.md
├── 02-candidate-ranking.json
├── 03-prior-art-search/{shannon,yjmm10}/
├── 04-feature-matrix.md
├── 05-claims-v1.md
├── 06-specification-v1.md
├── 07-support-candidates.md
├── 08-claims-v2.md
├── 08-claims-v2-structure.json
├── 09-claim-support-map.md
├── 10-final-search/{shannon,yjmm10}/
├── 11-final-audit.md
└── filing-package/{huang-audit,docx}/
```

初始化案件目录：

```bash
python -m patent_skill.cli init-case patent-case \
  --project /absolute/path/to/project \
  --title "可选的拟申请名称"
```

`--project` 可指向 Git/普通目录或 ZIP。初始化只记录快照类型、整体摘要、逐文件 SHA-256、可用的 Git 状态和安全警告，不复制源代码，也不会自动创建 commit/tag。后续阶段只能依次推进：

```bash
python -m patent_skill.cli advance-stage patent-case EVIDENCE_MAP
python -m patent_skill.cli validate-case patent-case
```

阶段推进会验证当前产物，不允许手工跳过权利要求结构检查、查新、支持性映射或审计。Claims V2 的每个独权限定必须单独标记并同时出现在结构文件、支持映射和检索覆盖中。DOCX 必须是真实、非空的 OOXML 文件。技术内容问题会阻断内容完成；公开日期、贡献人、申请主体等申请背景可稍后补充，除非它们已直接影响当前的新颖性或权属判断。

输出不得虚构技术事实、实验数据、专利文献或区别特征，也不得标记为可直接提交。最终申请文本应由中国专利专业人员复核。

## 安全边界

- 不要上传未经授权的公司机密、客户数据、密钥或受限制代码。
- 只分析用户明确指定的真实项目。
- 不以改名、替换术语或更换权利要求类别规避现有技术。
- 外部 Skill 不得覆盖 Shannon 的 evidence map、候选发明、Claims 或案件状态。
- 本项目不提交专利申请，也不自动作出授权保证。

## 相关文件

- [Skill 主入口](SKILL.md)
- [完整工作流](docs/workflow.md)
- [安全政策](SECURITY.md)
- [MIT License](LICENSE)
