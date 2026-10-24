#!/usr/bin/env bash
# Edson Shop 对外 API curl 速查（把 edson_sk_... 换成你的密钥）
set -euo pipefail

BASE="${EDSON_API_BASE:-https://www.edsonshop.com}"
AUTH="Authorization: Bearer ${EDSON_API_KEY:?请先 export EDSON_API_KEY=edson_sk_...}"
AGENT="$BASE/api/v1/agent/v1"

echo "== 模型与单价 =="
curl -s -H "$AUTH" "$AGENT/models" | head -c 400; echo

echo "== 上传商品图 =="
curl -s -X POST -H "$AUTH" -F "file=@product.jpg" "$AGENT/files"; echo

echo "== 智能抠图（同步，透明底 PNG）=="
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"file_ids":["file_xxx"]}' "$AGENT/images/cutout"; echo

echo "== 图片编辑（异步 + 轮询）=="
TASK=$(curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"prompt":"生成1张1:1比例的电商主图，纯白背景","model":"gpt-image-2","image_urls":["https://example.com/product.jpg"],"mode":"async"}' \
  "$AGENT/images/edits")
echo "$TASK"
# TASK_ID=$(echo "$TASK" | sed -n 's/.*"task_id":\"\([^\"]*\)\".*/\1/p')
# curl -s -H "$AUTH" "$AGENT/tasks/$TASK_ID"

echo "== 余额 =="
curl -s -H "$AUTH" "$AGENT/account"; echo
