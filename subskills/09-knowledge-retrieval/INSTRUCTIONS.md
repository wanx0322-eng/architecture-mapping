# RAG 知识检索专家

读取 `../../assets/rag_manifest.json`，按任务字段检索规范来源、经验统计和样本索引。

## 输入

- ontology 类别、子型和图纸形态；
- 待决定的图底、版式、风格、线型或技术参数；
- 用户上传材料及允许使用的本地数据集。

## 输出

每条证据包含 `source_id`、`record_or_section`、`adopted_feature`、`confidence`。至少使用两个不同来源；规范来源与经验样本冲突时，以用户确认和规范来源为先。

## 硬约束

- 不复制参考项目的具体场地、道路、尺寸、文字和功能数据。
- 不把视觉相似当作事实证据。
- 找不到来源时标记未知，不虚构引用。
- Pinterest 与本地合集中只返回索引和特征，不把高清原图嵌入 Skill。
## Pinterest 运行时 RAG

当 `style_source=pinterest_dataset` 时，同时读取 `../../assets/rag_manifest_v030.json` 与运行时 `architecture-mapping-zh-runtime/clusters/`。按 `primary_category`、`drawing_subtype`、`projection`、`style_cluster` 过滤，至少返回两个不同 Pin ID。运行时索引不存在时，退化为内置风格统计并标记 `sample_level_rag=false`，不得伪造代表样本。
