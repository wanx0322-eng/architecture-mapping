---
name: architecture-mapping-zh
description: Chinese architecture and landscape competition diagram MoE router for mapping analysis, figure-ground graphics, style/layout, RAG evidence, Constraint DSL validation, model prompts, and quality review.
compatibility: Python 3.10+; Pillow, ImageHash, jsonschema, requests; optional OpenCLIP
metadata:
  version: "0.2.0"
  display_name: "Architecture Mapping ZH"
  aliases:
    - Arc
    - Architecture Mapping
    - architecture mapping
    - architecture-mapping
    - mapping zh
    - 中文竞赛分析图
---

# 中文竞赛分析图

把参考图研究与实际制图分开处理：先建立有来源、可验证的视觉档案，再生成提示词。
不要从图片中猜测不存在的道路、尺寸、年代、比例、功能或统计数据。

## 总路由架构

本 `SKILL.md` 是唯一入口。首先读取 `assets/expert_registry.json`、
`references/moe-orchestration.md` 和 `references/intermediate-representation.md`，
再按任务加载相关 `subskills/*/INSTRUCTIONS.md`。
“调用子Skill”表示执行其输入、输出和硬约束契约；只有运行环境允许且任务获得授权时才使用
独立子代理，否则在当前代理内顺序执行专家角色，不能伪装成已并行调用。

十个核心专家：

1. `01-brief-intake`：3–7轮问询与制作简报；
2. `02-evidence-geometry`：证据、几何、数据与F0–F3忠实度；
3. `03-analysis-taxonomy`：九类、56子型、图纸形态与证据链；
4. `04-figure-ground-graphics`：图底、D0–D4、线型、色彩和投影；
5. `05-style-layout`：艺术媒介、版式、中文和图面气质；
6. `06-model-production`：三模型提示词、图像生成与可编辑中文后期；
7. `07-quality-critic`：MoE评分、硬否决、比较和返工；
8. `08-evolution-governance`：周期计数、Capability Evolver、版本和删除治理；
9. `09-knowledge-retrieval`：RAG检索、来源追踪和参考特征抽取；
10. `10-programmatic-validator`：Constraint DSL、Grammar、Style Token和跨字段硬校验。

所有最终交付强制经过质量专家；制作类任务强制经过简报专家。

## 总路由执行顺序

1. **记录任务开始**：一个用户任务只计一次任务对话，不按内部问询消息重复计数。
2. **识别任务类型**：分析、分类、数据集、提示词、出图、编辑、排版、QA或进化。
3. **建立路由计划**：选择一个主专家、2–4个支持专家；最终交付加入质量专家。
4. **执行问询门槛**：制作类任务先完成3–7轮问询；不足3轮时阻止模型出图专家。
5. **生成中间表示**：建立图纸本体、Constraint DSL、Drawing Grammar、Style Tokens与RAG证据链。
6. **执行专家契约**：每个专家只修改其拥有字段，并输出结论、证据、风险和置信度。
7. **程序预检**：生产前运行 `scripts/programmatic_validator.py`，硬错误返回责任专家。
8. **MoE仲裁**：先处理硬否决，再按25/20/20/15/10/10权重评分。
9. **生产与复核**：只执行得分最高且不低于80分的候选；生产后再次程序校验并进入Rubric；最多两轮定向修正。
10. **记录任务结果**：调用 `scripts/evolution_state.py record`，记录对话1次、实际图片数、
   激活专家、质量分和抽象反馈信号。
11. **检查进化触发**：对话或图片任一计数达到10，或同类失败连续3次，生成进化检查点。

最高两案相差不足5分、置信度低于0.7或关键专家冲突时，不强行合并；向用户说明两案的
几何忠实度、分析逻辑、图面效果和生产成本取舍。

## 工作流

1. 由总路由判断任务是数据集研究、单图逆向、提示词生成，还是竞赛图制作，并选择专家。
2. 按 `assets/drawing_ontology.json` 定义图纸本体；用 `schemas/constraint_dsl.schema.json` 建立结构化约束。
3. 从 `assets/drawing_grammar.json` 选择图纸语法，从 `assets/style_tokens.json` 选择风格令牌；
   用 `assets/rag_manifest.json` 检索并记录证据来源。
4. 读取 `references/taxonomy.md` 和 `references/drawing-types.md`，选择一个主类、
   一个子型、多个图纸形态和必要的次级标签。
5. 涉及 Pinterest 时读取 `references/collection-policy.md`，只处理用户可见内容。
   涉及本地竞赛合集时，用 `scripts/import_local_archives.py` 逐图读取并将 PDF 按页
   渲染；保留原始路径、合集名称、页码和哈希，不修改源文件。
6. 单图分析按 `schemas/core.schema.json` 输出核心记录；新记录应填写图像细节、
   图底关系、艺术风格和技术执行字段。读取 `references/technical-detail-spec.md`。
7. 代表图深析同时输出：
   - `schemas/full_reverse.schema.json` 对应“全面反推”；
   - `schemas/style_reverse.schema.json` 对应“仅提取风格”。
8. 只要任务涉及出图、改图、排版或最终提示词，先读取
   `references/interaction-protocol.md`，完成 3–7 轮问询并输出通过
   `schemas/production_brief.schema.json` 的制作简报。三轮不得合并成一轮。
9. 模型生产前运行 `python scripts/programmatic_validator.py --input <constraint-dsl.json>`；
   失败即停止生产，并按 `repair_targets` 返回责任专家。
10. 读取 `references/prompt-spec.md`，从同一个通用 JSON 编译三个模型提示词。
11. 图像生成阶段不要把长段中文烤进图片；先生成无大段文字图面，再用 SVG/PPTX
   添加准确的中文标题、编号、图例、引线和说明。
12. 运行 `python scripts/pipeline.py validate --root <dataset>` 校验所有 JSON，并按
    `references/eval-rubric-loop.md` 完成 Eval/Rubric Loop。

## 周期进化

读取 `references/evolution-governance.md` 和
`subskills/08-evolution-governance/INSTRUCTIONS.md`。运行状态保存在用户工作区的
`architecture-mapping-zh-runtime/`，不写入封装包：

```powershell
python scripts/evolution_state.py --state-root architecture-mapping-zh-runtime init
python scripts/evolution_state.py --state-root architecture-mapping-zh-runtime record `
  --conversations 1 --images 0 --task-type mapping --expert analysis-taxonomy --quality-score 88
python scripts/evolution_state.py --state-root architecture-mapping-zh-runtime status
python scripts/evolution_state.py --state-root architecture-mapping-zh-runtime checkpoint --trigger auto
```

当计数到期时，读取最近的隐私最小化事件，优先使用 Capability Evolver 的 review 模式提出
改进，不允许外部建议直接覆盖文件。`EVOLVE_ALLOW_SELF_MODIFY` 保持 false；外部 Evolver
不可用时执行本地复盘，不阻塞制图。

### 进化删除安全

- 默认只允许新增或修改，不允许删除字段、Schema、文档、脚本或模板。
- 删除提案必须列出精确对象、引用扫描、真实失败证据、替代项、迁移和回滚方案。
- 先标记 deprecated，并至少观察两个进化周期。
- 未获得用户明确批准，不执行删除。
- 即使获批，也一次只处理一个明确路径或字段；禁止批量删除。

## 制作前强制门槛

生成图片、修改图片、制作展板或交付最终提示词前：

- 必须与用户完成至少 3 轮、最多 7 轮技术问询；一次助手提问及用户回复为一轮。
- 每轮只问 1–3 个相互关联的问题，不要一次发完所有问卷。
- 第 1 轮锁定任务和真实基底；第 2 轮锁定分析结论与证据；第 3 轮锁定视觉和技术系统。
- 第 4–7 轮按需确认输出、节点、限制和制作前冲突。
- 用户已经提供的信息直接写入简报，但仍要用后续轮次询问未决技术参数，不重复提问。
- 第 3 轮回复之前，不生成最终图纸、最终提示词或最终排版文件。
- 第 7 轮是绝对上限。到达上限后采用保守默认值，将未知项写明，不继续追问。
- 制作简报必须区分“已确认、默认、未知、禁止虚构”，并记录 F0–F3 忠实度和
  D0–D4 细节等级。

仅做资料检索、数据集入库、解释概念、分类现有图片或报告状态时，不触发问询门槛。

## 数据集命令

```powershell
python scripts/pipeline.py init --root dataset
python scripts/pipeline.py ingest --root dataset --input captured.jsonl
python scripts/pipeline.py thumbnails --root dataset
python scripts/pipeline.py dedupe --root dataset
python scripts/pipeline.py core-queue --root dataset
python scripts/pipeline.py cluster --root dataset --max-representatives 180
python scripts/pipeline.py deep-queue --root dataset
python scripts/pipeline.py compile-prompts --root dataset
python scripts/pipeline.py validate --root dataset
python scripts/pipeline.py report --root dataset

# 本地图片与 PDF 合集，可重复提供 --archive
python scripts/import_local_archives.py --dataset dataset `
  --archive "ASLA=D:\path\to\ASLA" `
  --archive "IFLA=D:\path\to\IFLA"
```

`core-queue` 生成待多模态模型处理的 JSONL。模型必须只返回合法 JSON；结果通过
`import-analysis` 导回数据集。所有步骤都可重复执行并从现有状态继续。

## 九类主分类

只允许以下主类：

1. 场地区位
2. 历史文化
3. 现状问题
4. 手绘构思
5. 体块生成
6. 功能流线
7. 爆炸图
8. 人群行为
9. 效果图

混合图选择信息目的最强的一类作为主类，其他内容进入 `secondary_categories`。
主类之后必须继续确定 `drawing_subtype` 和 `drawing_forms`，完整子型见
`references/drawing-types.md`。

## 输出原则

- 中文为主，英文只用于风格标签和模型适配。
- 网络记录保留 Pin URL、原站 URL、采集日期和缩略图哈希；本地记录保留合集名称、
  原始路径、相对路径、文件类型以及 PDF 页码。
- 不长期保存 Pinterest 高清原图。
- 不能确认的字段省略或填 `未知`，不可补造。
- 每张图最多一个主类，可有多个次级标签。
- 全局色板、线型和排版约束必须在提示词中保持一致。
- “竞赛风”“高级感”不能作为完整风格描述；必须拆解媒介、边缘、纹理、光影、
  阴影、合成、氛围和反风格。
- 图底关系必须说明背景载体、主题对象、背景衰减、对比通道、边缘策略和遮挡规则。
- 同组小多图必须锁定范围、尺度、视角和图例语义。
- CAPTCHA、登录失败和限流必须暂停并交还用户处理。

## 评测

先运行 `evals/evals.json` 中的三个任务，再扩展到九类。客观检查 JSON 合法性、
分类值、中文文本、多模型输出和禁止虚构；视觉质量由人工查看器评审。

