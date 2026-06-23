# 程序化校验专家

在模型生产前与交付前各运行一次：

```powershell
python ../../scripts/programmatic_validator.py --input <constraint-dsl.json> --output <validation.json>
```

## 检查范围

- DSL Schema 与枚举；
- 生产任务是否完成 3–7 轮问询；
- ontology、grammar pattern 和 style token 是否存在；
- 结论是否具有证据；
- 锁定几何与可编辑几何是否冲突；
- RAG 来源 ID 是否有效；
- 中文长文本是否进入 SVG/PPTX 后期。

## 输出与路由

输出 `valid`、`schema_errors`、`semantic_checks` 和 `repair_targets`。任何硬检查失败都阻止出图或交付，并把任务返回最早责任专家；不得用高审美分覆盖程序错误。
