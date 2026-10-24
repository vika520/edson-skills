# edson-skills

把 [Edson Shop](https://www.edsonshop.com) 的电商生图能力接进你的 agent 与自动化：**AI 抠图、图片编辑（图生图）、文生图、商品套图编排**，通过 REST 直调或 MCP 两种方式，按积分计费、失败自动退还。

## 安装

```bash
# 方式一：skills CLI
npx -y skills add https://github.com/vika520/edson-skills

# 方式二：直接克隆
git clone https://github.com/vika520/edson-skills.git
```

## 配置

1. 注册/登录 [Edson Shop](https://www.edsonshop.com)，到 [API 接入页](https://www.edsonshop.com/api-access) 创建密钥（`edson_sk_...`，仅显示一次，可随时更换）。
2. 充值积分（API 与网页端同账户同余额）。
3. 环境变量：

```bash
export EDSON_API_KEY="edson_sk_..."
export EDSON_API_BASE="https://www.edsonshop.com"   # 自部署实例改这里
```

## 快速开始（REST 直调）

```bash
export EDSON_API_KEY=edson_sk_...
python scripts/edson_api.py models                                   # 可用模型与单价
python scripts/edson_api.py upload product.jpg                       # 上传 → file_id
python scripts/edson_api.py cutout file_abc123                       # 抠图 → out/*.png
```

或 curl（完整示例见 `examples/curl-quickstart.sh`）：

```bash
curl -X POST https://www.edsonshop.com/api/v1/agent/v1/images/cutout \
  -H "Authorization: Bearer $EDSON_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"file_ids":["file_abc123"]}'
```

## 快速开始（MCP）

Claude Desktop / Cursor 等：把 `examples/claude-desktop.json` 的配置并入客户端配置，密钥放 `Authorization` 头。MCP 端点为 `https://mcp.edsonshop.com/mcp`，鉴权与 REST 同一把密钥。

## 技能清单

| 技能 | 入口 | 能力 |
|---|---|---|
| AI 抠图 | `skills/ai-cutout/SKILL.md` | 透明底 PNG，人像/商品，发丝级边缘 |
| 电商图片编辑 | `skills/ecommerce-edit/SKILL.md` | 改风格/改文案/白底主图/参考图复刻 |
| 商品套图 | `skills/ecommerce-kit/SKILL.md` | 6 张式 listing 图集编排（主图/卖点/场景/细节/尺寸/包装） |

API 端点契约：`api/commands.json`；错误码与限额：根 `SKILL.md`。

## 限额与计费

- 单任务输出 ≤4 张、输入图 ≤16 张；MCP 批量单批 ≤16 项。
- 图片按次计费（`/agent/v1/models` 返回单价；gpt-image-2 ≈ 36 积分/张，1 积分 ≈ ¥0.01）。
- 余额不足返回 `402 billing.insufficient_funds`；生成失败自动退还。
- 结果 URL 为限时签名直连（约 1 小时），需长期保存请立即下载。

## License

MIT（见 `LICENSE`）。上游归属见 `NOTICE`。
