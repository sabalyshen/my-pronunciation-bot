#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
发音评分模块
功能：评估英文发音，给出评分和改进建议
"""

import os
import subprocess
import logging

# 尝试导入 faster-whisper，失败则使用原版 whisper
try:
    from faster_whisper import WhisperModel
    USE_FASTER_WHISPER = True
    print("✅ 使用 Faster-Whisper 引擎")
except ImportError:
    import whisper
    USE_FASTER_WHISPER = False
    print("✅ 使用原版 Whisper 引擎")

logger = logging.getLogger(__name__)

# 全局加载模型（只加载一次）
print("正在加载 Whisper 模型用于发音评分...")

if USE_FASTER_WHISPER:
    pronunciation_model = WhisperModel("small", device="cpu", compute_type="int8")
else:
    pronunciation_model = whisper.load_model("base")

print("✅ Whisper 模型加载完成")


async def evaluate_pronunciation(ogg_path: str, deepseek_api_func, scoring_prompt_template: str = None) -> dict:
    """
    评估英文发音
    
    Args:
        ogg_path: 语音文件路径
        deepseek_api_func: DeepSeek API 调用函数
        scoring_prompt_template: 评分提示词模板（可选）
    
    Returns:
        dict: {
            "success": bool,
            "text": str,           # 转写的文字
            "feedback": str,       # 评分反馈
            "error": str
        }
    """
    wav_path = None
    try:
        # 1. 格式转换
        wav_path = ogg_path.replace('.ogg', '.wav')
        ffmpeg_path = _find_ffmpeg()
        
        cmd = [ffmpeg_path, "-i", ogg_path, "-acodec", "pcm_s16le", 
               "-ar", "16000", "-ac", "1", wav_path, "-y"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {"success": False, "error": "音频格式转换失败", "text": "", "feedback": ""}
        
        # 检查文件是否生成
        if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
            return {"success": False, "error": "转换后的文件无效", "text": "", "feedback": ""}
        
        # 2. Whisper 转写
        if pronunciation_model is None:
            return {"success": False, "error": "模型未加载", "text": "", "feedback": ""}
        
        user_text = _transcribe_audio(wav_path)
        
        if not user_text:
            return {"success": False, "error": "没有识别到任何内容", "text": "", "feedback": ""}
        
        # 3. 构造评分 Prompt
        if scoring_prompt_template is None:
            scoring_prompt = _get_default_scoring_prompt(user_text)
        else:
            scoring_prompt = scoring_prompt_template.format(user_text=user_text)
        
        # 4. 调用 DeepSeek API
        feedback = await deepseek_api_func(scoring_prompt)
        
        return {
            "success": True,
            "text": user_text,
            "feedback": feedback,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"发音评分失败: {e}")
        return {"success": False, "error": str(e), "text": "", "feedback": ""}
    
    finally:
        # 清理临时文件
        _cleanup_files([wav_path, ogg_path] if wav_path else [ogg_path])


def _transcribe_audio(wav_path: str) -> str:
    """执行音频转写"""
    if USE_FASTER_WHISPER:
        # faster-whisper 接口
        segments, info = pronunciation_model.transcribe(wav_path, beam_size=1)
        text = " ".join([seg.text for seg in segments]).strip()
        print(f"📊 检测语言: {info.language} (置信度: {info.language_probability:.2f})")
        return text
    else:
        # 原版 whisper 接口
        result = pronunciation_model.transcribe(wav_path, fp16=False)
        text = result["text"].strip()
        print(f"📊 检测语言: {result.get('language', 'unknown')}")
        return text


def _find_ffmpeg() -> str:
    """查找 ffmpeg 可执行文件路径"""
    import shutil
    common_paths = ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "ffmpeg"]
    for path in common_paths:
        found = shutil.which(path)
        if found:
            return found
    return "ffmpeg"


def _cleanup_files(paths: list):
    """清理临时文件"""
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


def _get_default_scoring_prompt(user_text: str) -> str:
    """默认的评分提示词模板"""
    return f"""你是一位专业的英语发音教练。请对以下这段英文录音的转写文本进行发音评估。

用户说的内容："{user_text}"

请按照以下格式给出评估：

【发音准确度】（0-10分）
指出具体的音素问题

【重音与节奏】（0-10分）
评估单词重音、句子语调

【流利度】（0-10分）
分析停顿和语速问题

【综合评分】（1-10分）

【改进建议】
给出2-3条具体建议

最后用一句鼓励的话结尾。"""


# 模块说明
MODULE_INFO = {
    "name": "发音评分",
    "description": "评估英文发音，给出评分和改进建议",
    "commands": ["/pronounce", "/评分", "/p"],
    "help_text": """
🎙️ **发音评分模式**（默认）
发送英文语音消息后，机器人会：
1. 转写你说的话
2. 从准确度、节奏、流利度三个维度评分
3. 给出改进建议

使用方式：
- 直接发送英文语音即可（默认模式）
- 或发送 `/pronounce` 明确切换到评分模式
"""
}
