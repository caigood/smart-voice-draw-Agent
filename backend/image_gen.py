import httpx
from config import IMAGE_API_KEY, IMAGE_BASE_URL, IMAGE_MODEL
from openai import AsyncOpenAI


class ImageGenerator:
    def __init__(self):
        self.model = IMAGE_MODEL
        self.use_dashscope = "dashscope" in IMAGE_BASE_URL.lower()
        if not self.use_dashscope:
            self.client = AsyncOpenAI(api_key=IMAGE_API_KEY, base_url=IMAGE_BASE_URL)
        else:
            # 用 IMAGE_BASE_URL 拼接 DashScope 图片端点；如果误填 compatible-mode/v1，则自动修正为 api/v1
            base = IMAGE_BASE_URL.rstrip("/")
            if base.endswith("/compatible-mode/v1"):
                base = base.replace("/compatible-mode/v1", "/api/v1")
            self.multimodal_url = f"{base}/services/aigc/multimodal-generation/generation"
            self.image_gen_url = f"{base}/services/aigc/image-generation/generation"

    async def generate(self, prompt: str, negative_prompt: str = "") -> str:
        """生成图片并返回 URL"""
        print(f"[ImageGen] use_dashscope={self.use_dashscope}, prompt={prompt[:50]}...")

        if self.use_dashscope:
            return await self._generate_dashscope(prompt, negative_prompt)
        return await self._generate_openai(prompt)

    async def edit(self, image_url: str, prompt: str, negative_prompt: str = "") -> str:
        """基于已有图片进行编辑并返回新图片 URL"""
        print(f"[ImageEdit] use_dashscope={self.use_dashscope}, image={image_url[:50]}..., prompt={prompt[:50]}...")

        if not self.use_dashscope:
            raise Exception("当前非 DashScope 图片模型暂不支持图片编辑")

        return await self._edit_dashscope(image_url, prompt, negative_prompt)

    async def _edit_dashscope(self, image_url: str, prompt: str, negative_prompt: str = "") -> str:
        """通过 DashScope qwen-image 系列编辑图片"""
        model_lower = self.model.lower()
        if "qwen-image" not in model_lower:
            raise Exception("当前模型不支持图片编辑，请使用 qwen-image 系列模型")

        body = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": image_url},
                            {"text": prompt}
                        ]
                    }
                ]
            },
            "parameters": {
                "size": "1024*1024",
                "n": 1,
                "prompt_extend": True,
                "watermark": False
            }
        }
        if negative_prompt:
            body["parameters"]["negative_prompt"] = negative_prompt

        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                self.multimodal_url,
                json=body,
                headers={
                    "Authorization": f"Bearer {IMAGE_API_KEY}",
                    "Content-Type": "application/json"
                }
            )
            data = resp.json()
            if resp.status_code != 200:
                raise Exception(f"DashScope 图片编辑失败: {data.get('message', str(data))}")

            choices = data.get("output", {}).get("choices", [])
            if not choices:
                raise Exception("DashScope 返回无图片编辑结果")
            content_list = choices[0].get("message", {}).get("content", [])
            for item in content_list:
                if "image" in item:
                    return item["image"]
            raise Exception("DashScope 返回无图片 URL")

    async def _generate_dashscope(self, prompt: str, negative_prompt: str = "") -> str:
        """通过 DashScope API 生成图片 (qwen-image 系列用 multimodal-generation 端点)"""
        model_lower = self.model.lower()

        # qwen-image 系列用 multimodal-generation 端点
        if "qwen-image" in model_lower:
            body = {
                "model": self.model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"text": prompt}]
                        }
                    ]
                },
                "parameters": {
                    "size": "1024*1024",
                    "n": 1,
                    "prompt_extend": True,
                    "watermark": False
                }
            }
            if negative_prompt:
                body["parameters"]["negative_prompt"] = negative_prompt

            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    self.multimodal_url,
                    json=body,
                    headers={
                        "Authorization": f"Bearer {IMAGE_API_KEY}",
                        "Content-Type": "application/json"
                    }
                )
                data = resp.json()
                if resp.status_code != 200:
                    raise Exception(f"DashScope 生图失败: {data.get('message', str(data))}")

                choices = data.get("output", {}).get("choices", [])
                if not choices:
                    raise Exception("DashScope 返回无图片结果")
                content_list = choices[0].get("message", {}).get("content", [])
                for item in content_list:
                    if "image" in item:
                        return item["image"]
                raise Exception("DashScope 返回无图片 URL")

        # wan 系列用 image-generation 端点
        else:
            body = {
                "model": self.model,
                "input": {
                    "prompt": prompt
                },
                "parameters": {
                    "size": "1024*1024",
                    "n": 1
                }
            }
            if negative_prompt:
                body["parameters"]["negative_prompt"] = negative_prompt

            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    self.image_gen_url,
                    json=body,
                    headers={
                        "Authorization": f"Bearer {IMAGE_API_KEY}",
                        "Content-Type": "application/json"
                    }
                )
                data = resp.json()
                if resp.status_code != 200:
                    raise Exception(f"DashScope 生图失败: {data.get('message', str(data))}")

                results = data.get("output", {}).get("results", [])
                if not results:
                    raise Exception("DashScope 返回无图片结果")
                return results[0].get("url", "")

    async def _generate_openai(self, prompt: str) -> str:
        """通过 OpenAI DALL-E API 生成图片"""
        response = await self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url
