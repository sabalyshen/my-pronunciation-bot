#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
录音转文字模块
功能：
1. 将用户发送的语音消息转写成中文文字
2. 支持长音频自动分段处理（>10分钟自动启用）
3. 支持中断控制
4. 分段输出结果
"""

import os
import re
import json
import time
import asyncio
import subprocess
import logging
from typing import Dict, Any, Optional, Callable, List

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

# ============================================================
# 全局配置
# ============================================================

# 长音频阈值（秒）：超过此值自动启用分段模式
LONG_AUDIO_THRESHOLD = 600  # 10分钟 = 600秒

# 分段时长（秒）：长音频模式下每个片段的长度
SEGMENT_DURATION = 60  # 1分钟 = 60秒

# 全局任务状态管理（用于中断控制）
active_tasks: Dict[str, Dict[str, Any]] = {}


# ============================================================
# 模型加载
# ============================================================

print("正在加载 Whisper 模型用于中文转写...")

if USE_FASTER_WHISPER:
    transcribe_model = WhisperModel("small", device="cpu", compute_type="int8")
else:
    transcribe_model = whisper.load_model("tiny")

print("✅ Whisper 模型加载完成")

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    "zh": "中文",
    "en": "英文",
    "auto": "自动检测"
}


# ============================================================
# 辅助函数
# ============================================================

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
                print(f"🗑️ 已删除临时文件: {path}")
            except Exception as e:
                print(f"⚠️ 删除文件失败 {path}: {e}")


def _get_audio_duration(file_path: str) -> float:
    """使用 ffprobe 获取音频时长（秒）"""
    ffprobe_path = _find_ffmpeg().replace('ffmpeg', 'ffprobe')
    if not os.path.exists(ffprobe_path):
        ffprobe_path = "ffprobe"
    
    cmd = [
        ffprobe_path,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except:
        # 备用方法：使用 ffmpeg 获取时长
        cmd = [_find_ffmpeg(), "-i", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        import re
        match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})', result.stderr)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = float(match.group(3))
            return hours * 3600 + minutes * 60 + seconds
        return 0


def _transcribe_audio(wav_path: str, language: str = None) -> tuple:
    """执行音频转写，返回 (text, detected_language)"""
    if USE_FASTER_WHISPER:
        # faster-whisper 接口
        segments, info = transcribe_model.transcribe(
            wav_path, 
            language=language,
            beam_size=1
        )
        text = " ".join([seg.text for seg in segments]).strip()
        return text, info.language
    else:
        # 原版 whisper 接口
        result = transcribe_model.transcribe(
            wav_path,
            language=language if language else None,
            fp16=False
        )
        text = result["text"].strip()
        detected_lang = result.get("language", "unknown")
        return text, detected_lang


def _merge_segment_texts(segments: List[dict]) -> str:
    """合并多个片段的文字，去除重复和边界问题"""
    if not segments:
        return ""
    
    texts = [seg["text"] for seg in segments if seg.get("text") and seg.get("text") != "[识别失败]"]
    
    if not texts:
        return ""
    
    # 简单合并
    merged = " ".join(texts)
    
    # 清理多余空格和标点
    merged = re.sub(r'\s+', ' ', merged)
    merged = merged.strip()
    
    return merged


# ============================================================
# 核心转写函数（单文件版本）
# ============================================================

async def transcribe_voice(audio_path: str, language: str = "zh") -> dict:
    """
    将语音文件转写成文字（单文件版本，用于短音频）
    支持 m4a, mp3, wav, ogg 等格式
    """
    wav_path = None
    try:
        # 获取不带扩展名的文件名
        base_name = os.path.splitext(audio_path)[0]
        wav_path = f"{base_name}.wav"
        
        # 如果输入已经是 .wav，不需要转换
        if audio_path.lower().endswith('.wav'):
            wav_path = audio_path
        else:
            ffmpeg_path = _find_ffmpeg()
            
            cmd = [
                ffmpeg_path, "-i", audio_path, 
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                "-f", "wav",
                wav_path, "-y"
            ]
            print(f"🔧 执行转换命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ FFmpeg 错误: {result.stderr}")
                return {"success": False, "error": "音频格式转换失败", "text": ""}
        
        # 检查文件是否生成
        if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
            return {"success": False, "error": "转换后的文件无效或为空", "text": ""}
        
        print(f"✅ 转换成功，文件大小: {os.path.getsize(wav_path)} 字节")
        
        # Whisper 转写
        detected_lang = None if language == "auto" else language
        text, detected_language = _transcribe_audio(wav_path, detected_lang)
        
        if not text:
            return {"success": False, "error": "没有识别到任何内容", "text": ""}
        
        return {
            "success": True,
            "text": text,
            "language": detected_language,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"转写失败: {e}")
        return {"success": False, "error": str(e), "text": ""}
    
    finally:
        # 清理临时文件（但保留输入文件？由调用者决定）
        if wav_path and wav_path != audio_path and os.path.exists(wav_path):
            _cleanup_files([wav_path])


# ============================================================
# 长音频转写函数
# ============================================================

async def transcribe_long_audio(
    audio_path: str,
    user_id: int,
    language: str = "zh",
    progress_callback: Optional[Callable] = None,
    segment_duration: int = SEGMENT_DURATION
) -> dict:
    """
    处理长音频：自动分段转写，支持中断
    
    Args:
        audio_path: 原始音频路径（支持 m4a, mp3, ogg 等）
        user_id: 用户ID（用于任务管理）
        language: 语言代码
        progress_callback: 进度回调函数 async def callback(current, total, text)
        segment_duration: 分段时长（秒）
    
    Returns:
        dict: {
            "success": bool,
            "text": str,
            "segments": list,
            "interrupted": bool,
            "segments_done": int,
            "error": str
        }
    """
    wav_path = None
    segment_files = []
    results = []
    
    # 注册任务
    active_tasks[str(user_id)] = {
        "active": True,
        "start_time": time.time(),
        "segments_done": 0,
        "total_segments": 0
    }
    
    try:
        # 1. 转换整个文件为 WAV（便于分割）
        base_name = os.path.splitext(audio_path)[0]
        wav_path = f"{base_name}.wav"
        ffmpeg_path = _find_ffmpeg()
        
        cmd_convert = [
            ffmpeg_path, "-i", audio_path,
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-f", "wav",
            wav_path, "-y"
        ]
        print(f"🔧 执行转换命令: {' '.join(cmd_convert)}")
        
        result = subprocess.run(cmd_convert, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ 转换错误: {result.stderr}")
            return {"success": False, "error": "音频格式转换失败", "text": "", 
                    "segments": [], "interrupted": False, "segments_done": 0}
        
        if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
            return {"success": False, "error": "转换后的文件无效", "text": "", 
                    "segments": [], "interrupted": False, "segments_done": 0}
        
        print(f"✅ 转换成功: {wav_path} ({os.path.getsize(wav_path)} 字节)")
        
        # 2. 获取音频总时长
        total_duration = _get_audio_duration(wav_path)
        total_segments = max(1, int((total_duration + segment_duration - 1) / segment_duration))
        
        # 更新任务信息
        if str(user_id) in active_tasks:
            active_tasks[str(user_id)]["total_segments"] = total_segments
        
        print(f"📊 音频总时长: {total_duration:.1f}秒")
        print(f"📊 将分割为 {total_segments} 个片段 (每段 {segment_duration}秒)")
        
        # 3. 分割并逐段转写
        for idx in range(total_segments):
            # 检查是否被中断
            if str(user_id) in active_tasks and not active_tasks[str(user_id)]["active"]:
                print(f"⚠️ 用户 {user_id} 中断了转写任务")
                return {
                    "success": False,
                    "text": _merge_segment_texts(results),
                    "segments": results,
                    "interrupted": True,
                    "segments_done": idx,
                    "error": "用户中断"
                }
            
            # 生成当前片段的起止时间
            start_time = idx * segment_duration
            end_time = min((idx + 1) * segment_duration, total_duration)
            
            # 提取并转写片段
            segment_path = wav_path.replace('.wav', f'_seg_{idx:04d}.wav')
            segment_files.append(segment_path)
            
            # 使用 ffmpeg 提取片段
            cmd_extract = [
                ffmpeg_path, "-i", wav_path,
                "-ss", str(start_time),
                "-to", str(end_time),
                "-c", "copy",
                segment_path, "-y"
            ]
            subprocess.run(cmd_extract, capture_output=True)
            
            # 转写当前片段
            print(f"🔄 处理片段 {idx + 1}/{total_segments} ({start_time:.0f}s - {end_time:.0f}s)")
            
            text, detected_lang = _transcribe_audio(segment_path, None if language == "auto" else language)
            
            if text:
                results.append({
                    "segment": idx + 1,
                    "start_time": start_time,
                    "end_time": end_time,
                    "text": text
                })
                print(f"📝 片段 {idx + 1}: {text[:50]}...")
            else:
                results.append({
                    "segment": idx + 1,
                    "start_time": start_time,
                    "end_time": end_time,
                    "text": "[识别失败]",
                    "error": True
                })
            
            # 更新进度
            if progress_callback:
                await progress_callback(idx + 1, total_segments, text if text else "")
            
            # 更新任务进度
            if str(user_id) in active_tasks:
                active_tasks[str(user_id)]["segments_done"] = idx + 1
            
            # 清理片段文件
            _cleanup_files([segment_path])
            
            # 避免 CPU 过载，短暂休息
            await asyncio.sleep(0.2)
        
        # 4. 合并所有结果
        full_text = _merge_segment_texts(results)
        
        return {
            "success": True,
            "text": full_text,
            "segments": results,
            "interrupted": False,
            "segments_done": total_segments,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"长音频转写失败: {e}")
        return {
            "success": False, 
            "error": str(e), 
            "text": _merge_segment_texts(results),
            "segments": results,
            "interrupted": False,
            "segments_done": len(results)
        }
    
    finally:
        # 清理临时文件
        _cleanup_files([wav_path] if wav_path else [])
        _cleanup_files(segment_files)
        # 注意：不删除原始 audio_path，由调用者决定


# ============================================================
# 中断控制函数
# ============================================================

def interrupt_transcription(user_id: int) -> bool:
    """中断用户的转写任务"""
    key = str(user_id)
    if key in active_tasks and active_tasks[key]["active"]:
        active_tasks[key]["active"] = False
        print(f"🛑 已发送中断信号给用户 {user_id}")
        return True
    return False


def get_task_status(user_id: int) -> Optional[Dict]:
    """获取用户当前转写任务的状态"""
    key = str(user_id)
    if key in active_tasks:
        return active_tasks[key].copy()
    return None


def is_task_active(user_id: int) -> bool:
    """检查用户是否有正在进行的转写任务"""
    key = str(user_id)
    return key in active_tasks and active_tasks[key]["active"]


def get_audio_duration_for_display(file_path: str) -> str:
    """获取音频时长（可读格式 MM:SS 或 HH:MM:SS）"""
    seconds = _get_audio_duration(file_path)
    if seconds >= 3600:
        return f"{int(seconds // 3600)}:{int((seconds % 3600) // 60):02d}:{int(seconds % 60):02d}"
    else:
        return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def get_language_list() -> dict:
    """获取支持的语言列表"""
    return SUPPORTED_LANGUAGES


def get_module_info() -> dict:
    """获取模块信息"""
    return {
        "name": "录音转文字",
        "description": "将语音消息转写成中文文字，支持长音频分段处理",
        "features": [
            "短音频直接转写",
            "长音频自动分段 (>10分钟)",
            "支持中断控制",
            "分段进度反馈",
            "临时文件自动清理"
        ],
        "commands": ["/transcribe", "/转录", "/t", "/stop"],
        "help_text": """
📝 **录音转文字模式**

发送语音消息后，机器人会将语音转写成中文文字。

**自动分段**：
- 音频 ≤10分钟：直接转写
- 音频 >10分钟：自动分为1分钟片段，逐段转写

**控制命令**：
- `/transcribe` 或 `/t` - 进入转写模式
- `/stop` - 中断正在进行的转写任务
"""
    }


# ============================================================
# 主程序测试入口
# ============================================================

if __name__ == "__main__":
    async def test():
        print("=" * 50)
        print("测试模块功能")
        print("=" * 50)
        
        print(f"支持的语言: {get_language_list()}")
        print(f"模块信息: {get_module_info()['name']}")
        print(f"长音频阈值: {LONG_AUDIO_THRESHOLD // 60}分钟")
        print(f"分段时长: {SEGMENT_DURATION}秒")
        
    asyncio.run(test())
