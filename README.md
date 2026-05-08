# AI Capability Service

「模型能力统一调用」最小独立后端：对外暴露单一 HTTP 接口，按 `capability` 分发到不同实现（当前含 `text_summary` 模拟逻辑，以及加分项 `text_echo`）。

## 环境要求

- Python 3.10+

## 安装依赖

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

（Linux / macOS：`source .venv/bin/activate`）

## 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

默认文档：<http://127.0.0.1:8080/docs>  
健康检查：<http://127.0.0.1:8080/healthz>

## 接口说明

- **POST** `/v1/capabilities/run`

请求体：

| 字段 | 类型 | 说明 |
|------|------|------|
| `capability` | string | 能力名，如 `text_summary` |
| `input` | object | 能力入参 |
| `request_id` | string，可选 | 链路追踪 ID；不传则服务端生成 |

成功 / 失败 JSON 结构见题目说明；失败时 HTTP 状态码：`INVALID_INPUT` / `UNKNOWN_CAPABILITY` 为 **400**，校验失败为 **422**（`VALIDATION_ERROR`），未预期异常为 **500**（`INTERNAL_ERROR`）。

### `text_summary`

`input` 字段：

- `text`（string，必填）
- `max_length`（int，可选，默认 120，≥ 1）

实现为**本地模拟**（按句号/问号等优先截取完整句，否则截断并加 `...`），可通过环境变量控制模拟耗时：

- `AI_CAPABILITY_SIMULATED_LATENCY_MS`：默认 `3`，设为 `0` 可关闭 `sleep`（测试脚本已关闭）。

### `text_echo`（加分）

原样返回 `input.text`，便于联调。

## 示例 curl

```bash
curl -s -X POST "http://127.0.0.1:8080/v1/capabilities/run" ^
  -H "Content-Type: application/json" ^
  -d "{\"capability\":\"text_summary\",\"input\":{\"text\":\"第一段。第二段更长一些用于测试截断与摘要边界。\",\"max_length\":40},\"request_id\":\"demo-001\"}"
```

（Linux / macOS 将 `^` 换为 `\` 并写成一行或多行均可。）

## 运行测试

```bash
pytest -q
```

## 生产化说明（简要）

- 统一响应结构与错误码；业务错误在路由内计时并写入 `meta.elapsed_ms`。
- 结构化日志（含 `request_id` / `capability` / `elapsed_ms`）；支持请求头 `x-request-id` 与响应头回传。
- 能力注册表扩展第二个能力时仅需实现函数并登记到 `app/capabilities/registry.py`。
