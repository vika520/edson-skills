---
name: edson-skills
description: Edson Shop 生图能力接入包：AI 抠图、图片编辑（图生图）、文生图与电商套图编排，通过 REST API 或 MCP 调用，按积分计费、失败自动退还。
metadata:
  version: "0.1.0"
---

# Edson Shop Skills

把 [Edson Shop](https://www.edsonshop.com) 的电商生图能力接进你的 agent 工作流。

## 前置（一次性）

1. 到 <https://www.edsonshop.com/api-access> 注册/登录并创建 API 密钥（`edson_sk_...`，仅显示一次）。
2. 设置环境变量：

```bash
export EDSON_API_KEY="edson_sk_..."
export EDSON_API_BASE="https://www.edsonshop.com"   # 自部署实例改成自己的地址
```

3. 充值积分（与网页端同账户同余额；余额不足调用会返回 HTTP 402 `billing.insufficient_funds`）。

## 两种接入方式

| 方式 | 适合 | 说明 |
|---|---|---|
| **REST 直调** | Claude Code / Cursor / 脚本 / n8n | `scripts/edson_api.py` 是零依赖客户端；或直接 curl，端点见 `api/commands.json` |
| **MCP** | Claude Desktop 等工具型客户端 | 服务地址与配置见 `examples/`，鉴权同样用 `edson_sk_` 密钥 |

## 子技能路由

按用户诉求选择子技能，进入对应目录读全文后执行：

- **抠图 / 去背景 / 透明底** → `skills/ai-cutout/SKILL.md`
- **改风格 / 改文案 / 重绘 / 电商图复刻 / 白底主图** → `skills/ecommerce-edit/SKILL.md`
- **商品套图 / 多图一组 / listing 图集** → `skills/ecommerce-kit/SKILL.md`
- 纯文字生图（无参考图）→ 直接调 `/agent/v1/images/generations`，无需子技能

## 通用铁律

1. 所有调用带 `Authorization: Bearer $EDSON_API_KEY`；密钥泄露立即到 /api-access 更换（旧密钥即刻失效）。
2. 结果 `url` 是**限时签名直连（约 1 小时）**；需要长期保存请立即下载到本地，不要把过期 URL 当永久链接。
3. 生成结果同时保存在账户文件空间（网页「文件」页可查可下载）。
4. 余额不足（402）→ 提示用户充值，不要重试；其它错误可指数退避重试 2 次。
5. 单次任务最多 4 张输出、16 张输入图；更大批量自行分批。
