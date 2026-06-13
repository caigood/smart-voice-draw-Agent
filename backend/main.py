from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from orchestrator import VoiceDrawOrchestrator
from image_gen import ImageGenerator
import uuid
import traceback

app = FastAPI(title="VoiceDraw Agent")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 服务实例
orchestrator = VoiceDrawOrchestrator()
image_generator = ImageGenerator()


class SessionState(BaseModel):
    currentPrompt: Optional[str] = ""
    pendingQuestion: Optional[str] = None
    history: List[dict] = []


class ParseRequest(BaseModel):
    text: str
    sessionState: SessionState


class ParseResponse(BaseModel):
    intent: str
    needClarification: bool
    clarificationQuestion: Optional[str] = ""
    agentReply: str
    prompt: Optional[str] = ""
    negativePrompt: Optional[str] = ""
    operations: List[str] = []


class ConfirmRequest(BaseModel):
    text: str
    pendingPrompt: str
    sessionState: SessionState


class ConfirmResponse(BaseModel):
    confirmIntent: str  # confirm/revise/reject
    shouldGenerate: bool
    newPrompt: Optional[str] = ""
    agentReply: str


class GenerateRequest(BaseModel):
    prompt: str
    negativePrompt: Optional[str] = ""


class EditRequest(BaseModel):
    imageUrl: str
    prompt: str
    negativePrompt: Optional[str] = ""


class GenerateResponse(BaseModel):
    imageUrl: str
    versionId: str


@app.get("/")
async def root():
    return {"message": "VoiceDraw Agent API", "status": "running"}


@app.post("/api/agent/parse", response_model=ParseResponse)
async def parse_command(request: ParseRequest):
    """解析用户语音指令"""
    try:
        result = await orchestrator.parse(
            text=request.text,
            current_prompt=request.sessionState.currentPrompt,
            pending_question=request.sessionState.pendingQuestion,
            history=request.sessionState.history
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/confirm", response_model=ConfirmResponse)
async def confirm_command(request: ConfirmRequest):
    """处理用户对提示词的确认反馈"""
    try:
        context = f"历史操作：{request.sessionState.history}"
        result = await orchestrator.confirm(
            text=request.text,
            pending_prompt=request.pendingPrompt,
            context=context
        )
        return ConfirmResponse(
            confirmIntent=result.get("confirm_intent", "confirm"),
            shouldGenerate=result.get("should_generate", True),
            newPrompt=result.get("new_prompt", ""),
            agentReply=result.get("agent_reply", "")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/image/generate", response_model=GenerateResponse)
async def generate_image(request: GenerateRequest):
    """生成图片"""
    try:
        image_url = await image_generator.generate(request.prompt, request.negativePrompt)
        version_id = f"v{uuid.uuid4().hex[:8]}"
        return GenerateResponse(imageUrl=image_url, versionId=version_id)
    except Exception as e:
        print("=== Image Generate Error ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/image/edit", response_model=GenerateResponse)
async def edit_image(request: EditRequest):
    """基于当前图片进行编辑"""
    try:
        image_url = await image_generator.edit(
            request.imageUrl,
            request.prompt,
            request.negativePrompt
        )
        version_id = f"v{uuid.uuid4().hex[:8]}"
        return GenerateResponse(imageUrl=image_url, versionId=version_id)
    except Exception as e:
        print("=== Image Edit Error ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
