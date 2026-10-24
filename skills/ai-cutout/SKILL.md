---
name: edson-ai-cutout
description: AI 抠图：移除背景输出透明底 PNG，支持人像与商品，发丝级边缘；输入本地图片或图片 URL。
metadata:
  version: "0.1.0"
---

# AI 抠图（透明底）

## 流程

1. **拿 file_id**（二选一）：
   - 本地图片：`client.upload("<本地路径>")` → `file_id`
   - 图片 URL：无需上传，直接传 `image_urls`
2. **抠图**（同步模式，挂起至完成，一般 20~60 秒）：
   ```python
   task = client.cutout(file_ids=["file_xxx"])       # 或 image_urls=["https://..."]
   ```
   - 多张图：一次最多 4 张，每张独立输出一张透明底 PNG。
   - `model` 可省略；显式传 `gpt-image-2` 亦可。
3. **下载**（结果 URL 约 1 小时有效，立即保存）：
   ```python
   client.download(task, out_dir="out")
   ```
   需要白底/纯色底时在本地合成：透明 PNG 上铺一层背景色再压平即可（不要为换底色重复调用）。

## 大批量

> 4 张：循环分批，每批 `cutout` ≤4 张；批间无需等待限流（服务端按账户限流，遇 429 退避重试）。

## 判定与铁律

- 任务 `status=failed` 时读 `error` 原文报告用户，不编造成功；余额不足（402）提示充值后停止。
- 结果同时保存在网页端「文件」页，可作兜底取回。
- 抠图**不修改主体**：形状/颜色/文字/logo 与原图一致，只是背景变透明。
