# 中间表示与多 Agent 子任务链

总控不得把用户原话直接交给出图模型。所有制作任务先转换为可审计的中间表示，再由专家链逐层补全。

## 七层流水线

1. **Task Router**：识别任务类型、交付物、问询轮次和硬约束，选择主专家与支持专家。
2. **Drawing Ontology**：用 `assets/drawing_ontology.json` 确定主类、子型、图纸形态、证据链和允许的复合关系。
3. **Constraint DSL**：用 `schemas/constraint_dsl.schema.json` 表达输入锁定、F0-F3、D0-D4、几何、分析、图底、版式、文字、输出和禁止事项。
4. **Drawing Grammar**：按 `assets/drawing_grammar.json` 将内容组织为可解析的画布、区域、图层、节点、边、标注和图例。
5. **Style Tokens**：从 `assets/style_tokens.json` 选择令牌，不使用“高级感”等空泛形容词。
6. **RAG Evidence**：按 `assets/rag_manifest.json` 检索本地分类、技术规范、数据集统计和代表样本；每条采用内容必须保留来源 ID。
7. **Validator + Eval/Rubric**：程序校验硬标准，质量专家评审软标准；低于 80 分或触发硬否决时返回最早可修复层。

## 多 Agent 子任务链

```text
总控
  -> brief-intake
  -> evidence-geometry
  -> analysis-taxonomy
  -> [figure-ground-graphics || style-layout]
  -> model-production
  -> programmatic-validator
  -> quality-critic
  -> evolution-governance（仅达到触发条件时）
```

方括号中的专家可以并行提出方案，但必须写入同一份 DSL 和 Grammar；不能各自创建互相冲突的隐藏假设。程序校验失败时直接返回对应专家；软质量不达标时由 MoE 比较候选，最多两轮定向修正。

## 统一交接包

每个专家接收并返回同一结构：

- `task_id`、`expert_id`、`input_revision`、`output_revision`；
- `confirmed`、`defaults`、`unknowns`、`forbidden_fabrication`；
- `ontology_refs`、`constraint_patch`、`grammar_patch`、`style_token_refs`、`rag_evidence_refs`；
- `findings`、`risks`、`confidence`、`vetoes`、`next_expert`。

专家只修改自己拥有的字段。跨域修改必须作为 proposal 交给字段所有者确认，避免后续专家悄悄覆盖几何、数据或用户决定。
