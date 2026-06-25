# Eval / Rubric Loop

## 顺序

1. 结构校验：Constraint DSL、MoE 决策、生产简报和提示词必须通过 JSON Schema。
2. 硬标准：问询门禁、几何锁定、证据来源、禁止虚构、图层遮挡、中文后期策略。
3. 软评分：证据几何 25、分析逻辑 20、图底层级 20、可读性 15、风格一致 10、生产可用 10。
4. 决策：任一硬标准失败为 `block`；无硬失败但总分低于 80 为 `revise`；其余为 `pass`。
5. 修复：返回最早出错层，不允许只靠后期风格掩盖上游证据或几何问题。
6. 回归：修改后重跑失败用例、相邻类型用例和 50 张随机回归；不重跑全部数据。

## 修复路由

- 问询不足 → `brief-intake`
- 来源、数据或几何不实 → `evidence-geometry`
- 分类、论点或因果错误 → `analysis-taxonomy`
- 图底、线型、颜色语义错误 → `figure-ground-graphics`
- 排版、文字、艺术媒介错误 → `style-layout`
- 模型参数、格式或中文后期错误 → `model-production`
- 重复失败达到 3 次 → `evolution-governance`

每个修订循环保存失败检查、分数、修复层和改动摘要。最多两轮定向修订；仍未达标则向用户报告阻碍或呈现候选取舍。
## Pinterest 风格附加检查

当 `style_source=pinterest_dataset` 时，检查 Pinterest 风格一致性，包括媒介、边缘、纹理、阴影、色板、图底、版式与反向词。风格分只属于“艺术风格一致性”维度，不得覆盖几何忠实度。复制代表样本内容、伪造样本级 RAG、风格导致 F2/F3 漂移，或未启用却隐式应用 Pinterest Style Token，均为 `block`。
