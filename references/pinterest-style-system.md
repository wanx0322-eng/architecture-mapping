# Pinterest 风格系统

仅在用户明确指定 `style_source=pinterest_dataset` 时启用。未指定时保持原有 Style Token 和提示词行为。

## 接口

```json
{
  "style_source": "pinterest_dataset",
  "style_cluster": "ecological_layered_wash",
  "style_strength": 0.7
}
```

强度：`0–0.39` low，`0.4–0.79` medium，`0.8–1.0` high。风格不得覆盖 F2/F3 几何和证据约束。

可选风格：

- `minimal_grey_competition`
- `ecological_layered_wash`
- `desaturated_paper_collage`
- `precision_vector_analysis`
- `layered_landscape_axonometric`
- `diagnostic_heat_overlay`
- `hand_drawn_mixed_media`
- `dark_high_contrast_narrative`

按主类、子型、投影和风格簇检索至少两个不同 Pin 来源。只抽象媒介、边缘、纹理、阴影、色板、图底和版式；不得复制场地、道路、文字、数据、功能或设计内容。

数据集位于用户工作区 `architecture-mapping-zh-runtime/`，不嵌入 Skill 安装包。

## 自动选择

`style_cluster=auto` 时，先用主类、子型、投影与媒介匹配适用场景，再比较候选簇的正向词和反向词。输出 `selection_mode=auto`、最终簇、强度档位和选择理由。没有明确匹配时使用 `minimal_grey_competition`，不得按簇样本数量决定风格。

## 专家路由

依次经过 `09-knowledge-retrieval`、`05-style-layout`、`10-programmatic-validator`、`06-model-production` 和 `07-quality-critic`。运行时索引缺失时设置 `sample_level_rag=false`，只使用内置统计档案，不虚构 Pin 来源。