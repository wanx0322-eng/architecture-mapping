# architecture-mapping-zh

中文建筑/景观/城市设计竞赛分析图 Skill 与 Pinterest mapping 研究管线。

## 当前能力

- Pinterest 页面可见 Pin 的断点采集与 JSONL 导入
- 缩略图下载、SHA-256 与 64 位感知哈希
- 精确与近似重复检测
- 九类主分类及多标签 JSON Schema
- 全面反推/仅风格反推两套严格 JSON
- 类内视觉特征聚类与代表图选择
- Nano Banana/Gemini、GPT Image、Midjourney 提示词编译
- 数据集完整性检查与 HTML/Markdown 报告

## 安全边界

采集器只读取已登录页面中用户可见的公开内容。不读取 Cookie、密码、Local
Storage，不绕过 CAPTCHA、限流或访问控制。仅保存缩略图和来源链接。

## Pilot

正式扩展到 2100 个唯一有效 Pin 前，先完成 100 个样本并满足：

- 相关率 >= 90%
- 重复漏检率 <= 5%
- JSON Schema 通过率 = 100%

浏览器不可用时，可以把页面提取结果保存为 JSONL 后运行离线管线。

