# VoiceDraw Agent

VoiceDraw Agent 是一款面向“纯语音控制绘图工具”课题的 AI 绘图 Demo。用户通过语音描述绘图需求，系统会进行指令理解、提示词优化、用户确认、图像生成，并支持基于已有图片的语音修改、历史版本管理和图片下载。

## 项目特点

- **语音驱动创作流程**：使用浏览器 Web Speech API 进行中文语音识别，用户通过语音完成绘图描述、确认、修改、回退和清空等操作。
- **CrewAI 多智能体架构**：后端使用 CrewAI 构建三个核心智能体：
  - `IntentAgent`：负责识别用户语音指令意图，例如新图生成、图片修改、重新生成、回退和清空。
  - `PromptAgent`：负责将用户自然语言绘图需求优化为高质量绘图提示词。
  - `ConfirmAgent`：负责理解用户对提示词的确认、补充、修改或拒绝意图。
- **FastAPI 后端服务**：提供语音指令解析、提示词确认、图片生成、图片编辑等接口。
- **React 前端界面**：提供科技风格的语音交互界面、图片展示区、对话区、历史版本区和下载功能。
- **图像生成与编辑**：支持 OpenAI-compatible 图像生成接口，当前适配 DashScope `qwen-image` 系列的文生图和图像编辑能力。
- **多轮确认机制**：系统会在生成前展示优化后的提示词，用户可以继续语音补充修改，确认后才生成图片。
- **历史版本管理**：生成和编辑后的图片会进入历史版本区，支持点击放大、下载和语音回退。

## 技术栈

### 前端

- React 18
- Vite
- Axios
- Browser Web Speech API
- CSS Glassmorphism / Tech UI

### 后端

- Python 3
- FastAPI
- Uvicorn
- CrewAI
- LiteLLM
- OpenAI Python SDK
- HTTPX
- Pydantic
- python-dotenv

### 模型服务

- 文本大模型：OpenAI-compatible Chat API
- 图像模型：OpenAI-compatible Image API 或 DashScope `qwen-image` 系列

## 目录结构

```text
VoiceDraw-Agent/
├── backend/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── intent_agent.py      # CrewAI 意图识别智能体
│   │   ├── prompt_agent.py      # CrewAI 提示词优化智能体
│   │   └── confirm_agent.py     # CrewAI 用户反馈理解智能体
│   ├── .env.example             # 环境变量示例
│   ├── orchestrator.py          # VoiceDrawOrchestrator，负责流程编排与智能体调度
│   ├── config.py                # 配置加载与 CrewAI 本地存储路径配置
│   ├── image_gen.py             # 图像生成与图像编辑服务
│   ├── main.py                  # FastAPI 应用入口
│   └── requirements.txt         # 后端依赖
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # 前端主逻辑
│   │   ├── App.css              # 前端样式
│   │   └── main.jsx             # React 入口
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── .gitignore
├── DESIGN.md                    # 初始设计文档
├── COMPETITION_DESIGN.md        # 参赛提交设计文档
└── README.md
```

## 核心流程

```text
用户语音输入
  ↓
浏览器语音识别
  ↓
FastAPI /api/agent/parse
  ↓
VoiceDrawOrchestrator 调用 CrewAI 智能体
  ├── IntentAgent：识别用户语音意图
  ├── PromptAgent：创建图片时优化提示词
  └── ConfirmAgent：确认阶段理解用户反馈
  ↓
前端展示优化提示词并请求用户确认
  ↓
用户语音确认 / 补充 / 拒绝
  ↓
FastAPI /api/agent/confirm
  ↓
ConfirmAgent 理解反馈
  ├── confirm → 生成图片
  ├── revise → 更新提示词并再次确认
  └── reject → 等待用户重新描述
```

## 支持的语音能力

- 创建新图片：如“画一只穿宇航服的猫”
- 确认生成：如“可以生成”“就用这个”
- 补充修改提示词：如“可以，但是加一个月球背景”
- 基于当前图修改：如“把背景改成夜晚”“给它加一顶蓝色帽子”
- 重新生成：如“重新生成一张”
- 回退版本：如“回到上一个版本”
- 清空画面：如“清空画面”

## 本地运行

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd VoiceDraw-Agent
```

### 2. 配置后端环境

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

编辑 `backend/.env`：

```env
LLM_API_KEY=your_llm_api_key
LLM_BASE_URL=https://your-llm-compatible-endpoint/v1
LLM_MODEL=your-chat-model

IMAGE_API_KEY=your_image_api_key
IMAGE_BASE_URL=https://dashscope.aliyuncs.com/api/v1
IMAGE_MODEL=qwen-image
```

启动后端：

```bash
python main.py
```

默认地址：`http://localhost:8000`

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认地址：`http://localhost:5173`

## 环境变量说明

| 变量 | 说明 |
| --- | --- |
| `LLM_API_KEY` | 文本大模型 API Key |
| `LLM_BASE_URL` | 文本大模型 OpenAI-compatible Base URL |
| `LLM_MODEL` | 文本大模型名称 |
| `IMAGE_API_KEY` | 生图模型 API Key |
| `IMAGE_BASE_URL` | 生图模型 Base URL |
| `IMAGE_MODEL` | 生图模型名称 |

## 设计取舍

- 为避免持续监听导致误触发和隐私问题，系统采用“主动语音输入”方式。用户通过麦克风按钮启动单轮语音输入，绘图创作内容本身均通过语音完成。
- 为提升生成结果准确性，系统引入提示词确认机制。用户可以在生成前继续补充或修改提示词。
- 图像二次编辑依赖图像模型能力，当前可通过提示词强调“保持主体不变，仅修改指定部分”，但模型仍可能对未指定区域产生变化。
- 使用 CrewAI 保持后端智能体架构清晰，便于后续扩展更多 Agent，例如安全审查 Agent、成本控制 Agent、风格推荐 Agent 等。

## 注意事项

- 不要提交 `.env`、`.crewai`、`node_modules`、`dist` 等本地生成文件。
- 浏览器首次使用语音识别时需要麦克风权限授权。
- 图像编辑能力依赖具体图像模型，若使用非 DashScope `qwen-image` 系列模型，可能不支持图片编辑。