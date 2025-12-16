"""
视觉分析工具集
用于分析无人机摄像头画面，识别场景内容
支持多种视觉模型：OpenAI GPT-4V, 通义千问VL, Ollama LLaVA
"""
import base64
import httpx
from typing import Dict, Any, List, Optional
from app.plugins.base_tool import BaseAgentTool, ToolParameter, ToolResult
from app.utils import logger
from app.config import settings


class VisionAnalysisTool(BaseAgentTool):
    """视觉场景分析工具"""

    name: str = "analyze_camera_view"
    description: str = (
        "分析无人机摄像头当前画面，识别场景中的物体、环境特征、障碍物等。"
        "使用场景：'看看前面有什么'、'分析当前环境'、'识别画面中的物体'、'检查有没有障碍物'等。"
        "返回场景描述报告。"
    )
    category: str = "vision"
    backend_name: str = "drone"

    parameters: List[ToolParameter] = [
        ToolParameter(
            name="prompt",
            type="string",
            description="分析提示词，如'描述场景'、'识别障碍物'、'寻找特定物体'",
            required=False,
            default="请详细描述这个室内场景，包括：1)可见的物体和家具 2)空间布局 3)潜在的飞行障碍物 4)光线条件"
        ),
        ToolParameter(
            name="detail_level",
            type="string",
            description="分析详细程度: brief(简要), normal(正常), detailed(详细)",
            required=False,
            default="normal",
            enum=["brief", "normal", "detailed"]
        )
    ]

    async def execute(
        self,
        prompt: str = "请详细描述这个室内场景，包括：1)可见的物体和家具 2)空间布局 3)潜在的飞行障碍物 4)光线条件",
        detail_level: str = "normal"
    ) -> Dict[str, Any]:
        """执行视觉分析"""
        logger.info(f"Vision analysis requested, detail_level={detail_level}")

        # 1. 从 broker 获取最新摄像头帧
        frame_result = await self._get_camera_frame()
        if not frame_result["success"]:
            return ToolResult.error_result(frame_result.get("error", "无法获取摄像头画面")).to_dict()

        image_base64 = frame_result["data"]

        # 2. 根据配置选择视觉模型进行分析
        analysis_result = await self._analyze_with_vision_model(image_base64, prompt, detail_level)

        if analysis_result["success"]:
            return ToolResult.success_result(
                "场景分析完成",
                data={
                    "analysis": analysis_result["analysis"],
                    "model_used": analysis_result.get("model", "unknown"),
                    "detail_level": detail_level
                }
            ).to_dict()
        else:
            return ToolResult.error_result(analysis_result.get("error", "视觉分析失败")).to_dict()

    async def _get_camera_frame(self) -> Dict[str, Any]:
        """从 broker 获取最新摄像头帧（Base64 JPEG）"""
        try:
            # 方案1: 直接获取 MJPEG 流的单帧
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 尝试获取单帧图像
                response = await client.get(
                    f"{settings.backend_url}/api/camera/snapshot",
                    timeout=5.0
                )
                if response.status_code == 200:
                    # 如果返回的是图片
                    content_type = response.headers.get("content-type", "")
                    if "image" in content_type:
                        image_base64 = base64.b64encode(response.content).decode("utf-8")
                        return {"success": True, "data": image_base64}
                    # 如果返回的是 JSON（包含 base64）
                    elif "json" in content_type:
                        data = response.json()
                        if data.get("data"):
                            return {"success": True, "data": data["data"]}

                # 方案2: 从 MJPEG 流获取一帧
                # MJPEG 流是 multipart，需要解析
                response = await client.get(
                    f"{settings.backend_url}/api/mjpeg",
                    timeout=5.0
                )
                if response.status_code == 200:
                    # 解析 MJPEG multipart 响应
                    content = response.content
                    # 查找 JPEG 数据（以 FFD8 开头，FFD9 结尾）
                    start = content.find(b'\xff\xd8')
                    end = content.find(b'\xff\xd9')
                    if start != -1 and end != -1:
                        jpeg_data = content[start:end+2]
                        image_base64 = base64.b64encode(jpeg_data).decode("utf-8")
                        return {"success": True, "data": image_base64}

                return {"success": False, "error": "无法从摄像头获取图像"}

        except httpx.TimeoutException:
            return {"success": False, "error": "获取摄像头画面超时"}
        except Exception as e:
            logger.error(f"Get camera frame failed: {e}")
            return {"success": False, "error": f"获取摄像头画面失败: {str(e)}"}

    async def _analyze_with_vision_model(
        self,
        image_base64: str,
        prompt: str,
        detail_level: str
    ) -> Dict[str, Any]:
        """使用视觉模型分析图像"""

        # 根据详细程度调整提示词
        detail_instructions = {
            "brief": "请用2-3句话简要描述。",
            "normal": "请用一段话描述主要内容。",
            "detailed": "请详细描述所有可见元素，包括位置、颜色、大小等细节。"
        }
        full_prompt = f"{prompt}\n\n{detail_instructions.get(detail_level, '')}"

        # 优先尝试使用配置的视觉模型
        # 1. 如果配置了 OpenAI API 且支持 vision
        if settings.openai_api_key:
            result = await self._analyze_with_openai(image_base64, full_prompt)
            if result["success"]:
                return result

        # 2. 尝试使用通义千问 VL（如果配置了）
        qwen_api_key = getattr(settings, 'qwen_api_key', None)
        if qwen_api_key:
            result = await self._analyze_with_qwen_vl(image_base64, full_prompt)
            if result["success"]:
                return result

        # 3. 尝试使用本地 Ollama LLaVA
        result = await self._analyze_with_ollama(image_base64, full_prompt)
        if result["success"]:
            return result

        return {"success": False, "error": "没有可用的视觉分析模型"}

    async def _analyze_with_openai(self, image_base64: str, prompt: str) -> Dict[str, Any]:
        """使用 OpenAI GPT-4V 分析"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # 使用配置的 API base（可能是代理）
                api_base = getattr(settings, 'openai_api_base', 'https://api.openai.com')
                # 对于 DeepSeek，它不支持 vision，跳过
                if 'deepseek' in api_base.lower():
                    return {"success": False, "error": "DeepSeek 不支持视觉分析"}

                response = await client.post(
                    f"{api_base}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4-vision-preview",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{image_base64}",
                                            "detail": "high"
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 1000
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    analysis = data["choices"][0]["message"]["content"]
                    return {"success": True, "analysis": analysis, "model": "gpt-4-vision"}
                else:
                    return {"success": False, "error": f"OpenAI API 错误: {response.status_code}"}

        except Exception as e:
            logger.error(f"OpenAI vision analysis failed: {e}")
            return {"success": False, "error": str(e)}

    async def _analyze_with_qwen_vl(self, image_base64: str, prompt: str) -> Dict[str, Any]:
        """使用通义千问 VL 分析"""
        try:
            qwen_api_key = getattr(settings, 'qwen_api_key', None)
            if not qwen_api_key:
                return {"success": False, "error": "未配置通义千问 API Key"}

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
                    headers={
                        "Authorization": f"Bearer {qwen_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "qwen-vl-plus",
                        "input": {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {"image": f"data:image/jpeg;base64,{image_base64}"},
                                        {"text": prompt}
                                    ]
                                }
                            ]
                        }
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    analysis = data["output"]["choices"][0]["message"]["content"][0]["text"]
                    return {"success": True, "analysis": analysis, "model": "qwen-vl-plus"}
                else:
                    return {"success": False, "error": f"通义千问 API 错误: {response.status_code}"}

        except Exception as e:
            logger.error(f"Qwen VL analysis failed: {e}")
            return {"success": False, "error": str(e)}

    async def _analyze_with_ollama(self, image_base64: str, prompt: str) -> Dict[str, Any]:
        """使用本地 Ollama LLaVA 分析"""
        try:
            ollama_url = getattr(settings, 'ollama_url', 'http://localhost:11434')

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": "llava",  # 或 bakllava
                        "prompt": prompt,
                        "images": [image_base64],
                        "stream": False
                    },
                    timeout=60.0
                )

                if response.status_code == 200:
                    data = response.json()
                    analysis = data.get("response", "")
                    return {"success": True, "analysis": analysis, "model": "ollama-llava"}
                else:
                    return {"success": False, "error": f"Ollama 错误: {response.status_code}"}

        except httpx.ConnectError:
            return {"success": False, "error": "Ollama 服务未运行"}
        except Exception as e:
            logger.error(f"Ollama analysis failed: {e}")
            return {"success": False, "error": str(e)}


class DetectObstaclesTool(BaseAgentTool):
    """障碍物检测工具"""

    name: str = "detect_obstacles"
    description: str = (
        "专门检测摄像头画面中的障碍物和危险区域。"
        "使用场景：飞行前安全检查、路径规划、避障判断。"
        "返回障碍物列表和安全建议。"
    )
    category: str = "vision"
    backend_name: str = "drone"

    parameters: List[ToolParameter] = []

    async def execute(self) -> Dict[str, Any]:
        """检测障碍物"""
        logger.info("Obstacle detection requested")

        # 使用视觉分析工具，但使用专门的障碍物检测提示词
        vision_tool = VisionAnalysisTool()

        obstacle_prompt = """
        请分析这张图片中的飞行障碍物和危险区域：

        1. 列出所有可能阻挡无人机飞行的物体（如家具、灯具、电线、柱子等）
        2. 标注每个障碍物的大致位置（左/中/右，上/中/下）
        3. 评估飞行空间的安全性（安全/需注意/危险）
        4. 给出飞行建议

        请用以下格式回复：
        ## 障碍物列表
        - [物体名称]: [位置], [风险等级]

        ## 安全评估
        [评估结果]

        ## 飞行建议
        [建议内容]
        """

        result = await vision_tool.execute(prompt=obstacle_prompt, detail_level="detailed")

        if result.get("success"):
            return ToolResult.success_result(
                "障碍物检测完成",
                data={
                    "analysis": result["data"]["analysis"],
                    "type": "obstacle_detection"
                }
            ).to_dict()
        else:
            return ToolResult.error_result(result.get("message", "障碍物检测失败")).to_dict()


class FindObjectTool(BaseAgentTool):
    """物体搜索工具"""

    name: str = "find_object"
    description: str = (
        "在摄像头画面中搜索特定物体。"
        "使用场景：'找一下遥控器'、'看看有没有人'、'找到红色的箱子'等。"
        "返回物体是否存在及其位置。"
    )
    category: str = "vision"
    backend_name: str = "drone"

    parameters: List[ToolParameter] = [
        ToolParameter(
            name="target_object",
            type="string",
            description="要搜索的物体名称，如'人'、'椅子'、'红色箱子'",
            required=True
        )
    ]

    async def execute(self, target_object: str) -> Dict[str, Any]:
        """搜索指定物体"""
        logger.info(f"Searching for object: {target_object}")

        vision_tool = VisionAnalysisTool()

        search_prompt = f"""
        请在这张图片中寻找：{target_object}

        请回答：
        1. 是否找到目标物体？（是/否）
        2. 如果找到，它在画面中的位置？（左上/中上/右上/左中/正中/右中/左下/中下/右下）
        3. 物体的状态描述（颜色、大小、状态等）
        4. 置信度（高/中/低）

        如果没找到，请说明可能的原因（不在画面中/被遮挡/光线问题等）
        """

        result = await vision_tool.execute(prompt=search_prompt, detail_level="normal")

        if result.get("success"):
            analysis = result["data"]["analysis"]
            # 简单判断是否找到
            found = "是" in analysis[:50] or "找到" in analysis[:100]

            return ToolResult.success_result(
                f"{'找到' if found else '未找到'} {target_object}",
                data={
                    "target": target_object,
                    "found": found,
                    "analysis": analysis
                }
            ).to_dict()
        else:
            return ToolResult.error_result(result.get("message", "物体搜索失败")).to_dict()
