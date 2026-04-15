# assistant-2api

将 [assistant-ui.com](https://www.assistant-ui.com) 的免费聊天端点转换为 OpenAI 兼容的 `/v1/chat/completions` 格式。

## 功能

- 流式 & 非流式聊天补全
- 2 个活跃模型（GPT-5.4 Nano/Mini），6 个暂停模型自动回退到默认
- 工具/函数调用（多步，最多 10 轮）
- 图片识别（Vision）
- System Prompt 透传
- API Key 认证
- Docker 部署

## 快速开始

```bash
# 克隆
git clone https://github.com/XXXxx7258/assistant-2api.git
cd assistant-2api

# 配置
cp .env.example .env

# 启动（uv）
uv sync && uv run main.py

# 或 Docker
docker compose up -d
```

服务启动在 `http://localhost:8080`。

## 使用

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="sk-assistant-2api-free"
)

response = client.chat.completions.create(
    model="gpt-5.4-nano",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True
)
for chunk in response:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

### 可用模型

| 名称 | model 参数 | 状态 |
|------|-----------|------|
| GPT-5.4 Nano | `gpt-5.4-nano` | 可用 |
| GPT-5.4 Mini | `gpt-5.4-mini` | 可用 |
| Claude Haiku 4.5 | `claude-haiku-4.5` | 暂停 |
| Gemini 3 Flash | `gemini-3-flash` | 暂停 |
| Grok 4.1 Fast | `grok-4.1-fast` | 暂停 |
| Grok 3 Mini Fast | `grok-3-mini-fast` | 暂停 |
| Llama 3.3 70B | `llama-3.3-70b` | 暂停 |
| Qwen3 32B | `qwen3-32b` | 暂停 |

> 暂停模型由上游 assistant-ui 禁用，请求时会自动回退到 `gpt-5.4-nano`。

### 图片识别

```python
response = client.chat.completions.create(
    model="gpt-5.4-nano",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "这张图片是什么？"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
        ]
    }]
)
```

### 工具调用

```python
response = client.chat.completions.create(
    model="gpt-5.4-nano",
    messages=[{"role": "user", "content": "London 天气如何？"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取天气",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"]
            }
        }
    }]
)
```

## API 端点

| 端点 | 说明 |
|------|------|
| `POST /v1/chat/completions` | 聊天补全（兼容 OpenAI） |
| `GET /v1/models` | 活跃模型列表 |
| `GET /v1/models/all` | 全部模型（含状态和上下文窗口） |
| `GET /health` | 健康检查 |

## 限制

- 上游限流：每 IP 30 秒 5 次请求
- `maxOutputTokens` 硬编码 4096，不可调
- System Prompt 最长 4000 字符
- `temperature`、`top_p` 等生成参数不可控
- 工具调用最多 10 轮

## 技术原理

assistant-ui.com 是一个开源 React 聊天 UI 组件库的文档站，部署在 Vercel 上。其 `/api/chat` 端点通过 Vercel AI Gateway 路由到各 LLM 提供商，本项目将其 AI SDK v6 Data Stream 格式转换为 OpenAI 兼容格式。
