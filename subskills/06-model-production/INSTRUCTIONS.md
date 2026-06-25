# 模型出图专家

## 前置条件

只接受 `rounds_completed` 为3至7且 `ready_to_produce=true` 的制作简报。若条件不满足，
退回简报专家，不生成最终图。
Constraint DSL 还必须先通过 `../../scripts/programmatic_validator.py` 的生产前校验。

## 输出

- 通用结构化 JSON；
- Nano Banana/Gemini、GPT Image、Midjourney 三套适配；
- 图像生成或编辑执行计划；
- SVG/PPTX 中文标题、编号、图例和说明覆盖层；
- 候选图版本号和所用简报哈希。

## 稳定出图流程

1. 先生成不含长中文的结构与图面；
2. 保持几何、图层、色板和视角锁定；
3. 由质量专家评分；
4. 最多进行两轮有针对性的视觉修正，避免反复生成导致漂移；
5. 使用确定性工具添加中文并执行打印检查。
6. 把实际输出参数写回 DSL，再交程序校验与质量 Rubric。
## Pinterest 模型适配

当 `style_source=pinterest_dataset` 时读取 `../../references/pinterest-style-system.md`，并保留结构化 `style_reference`，不得把“Pinterest 风”当作唯一视觉描述。分别为 Gemini、GPT Image、Midjourney 编译可观察的媒介、边缘、纹理、阴影、色板、图底、版式词和反向词。low / medium / high 只调整风格显著度，不改变 F2/F3 几何、证据、比例和锁定道路。
