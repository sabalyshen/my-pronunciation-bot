#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DeepSeek 语音助手 - 主程序
支持两种模式：
1. 发音评分模式（默认）：评估英文发音
2. 录音转文字模式：将中文语音转写成文字
"""

import os
import sys
import time
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 导入功能模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules import pronunciation, transcription

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 环境变量
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

if not TOKEN or not DEEPSEEK_API_KEY:
    raise ValueError("请检查 .env 文件中的 TELEGRAM_BOT_TOKEN 和 DEEPSEEK_API_KEY")

# ============================================================
# 用户数据管理
# ============================================================
user_mode = {}           # 用户当前模式: pronunciation / transcription
user_pending_file = {}   # 用户待处理的文件路径

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = ['.m4a', '.mp3', '.wav', '.ogg', '.opus', '.flac', '.aac', '.mp4', '.mpeg']


# ============================================================
# DeepSeek API 函数
# ============================================================
async def get_deepseek_response(message: str) -> str:
    """调用 DeepSeek API 获取回复"""
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": message}],
            "stream": False
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"⚠️ API 返回错误: {response.status_code}"
            
    except Exception as e:
        logger.error(f"DeepSeek API 调用失败: {e}")
        return "⚠️ AI 服务暂时不可用，请稍后再试。"


# ============================================================
# 命令处理器
# ============================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    user_id = update.effective_user.id
    user_mode[user_id] = "pronunciation"
    user_pending_file[user_id] = None
    
    await update.message.reply_text(
        "🤖 **DeepSeek 语音助手**\n\n"
        "你好！我是你的语音助手。\n\n"
        "📌 **使用流程**：\n"
        "1. 发送 `/transcribe` 切换到转写模式\n"
        "2. **直接上传**录音文件（点击附件📎 → 选择文件）\n"
        "3. 发送 `/process` 开始处理\n\n"
        "📌 **命令列表**：\n"
        "• `/pronounce` - 切换到发音评分模式\n"
        "• `/transcribe` - 切换到录音转文字模式\n"
        "• `/process` - 处理已上传的文件\n"
        "• `/stop` - 中断正在进行的转写\n"
        "• `/mode` - 查看当前模式\n"
        "• `/help` - 查看帮助\n\n"
        "⚠️ **注意**：请直接上传文件，不要转发！",
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /help 命令"""
    help_text = """
ℹ️ **帮助**

**使用流程**：
1. 先用 `/pronounce` 或 `/transcribe` 切换模式
2. **直接上传**录音文件（点击📎附件 → 选择文件）
3. 发送 `/process` 开始处理

**命令列表**：
• `/start` - 启动机器人
• `/mode` - 查看当前模式
• `/pronounce` (或 `/p`) - 切换到发音评分模式
• `/transcribe` (或 `/t`) - 切换到录音转文字模式
• `/process` - 开始处理已上传的文件
• `/stop` - 中断正在进行的转写任务
• `/help` - 显示本帮助

**支持的格式**：
m4a, mp3, wav, ogg, opus, flac, aac, mp4, mpeg

**发音评分模式**：
评估英文发音，从准确度、节奏、流利度三个维度评分

**录音转文字模式**：
将中文录音转写成文字，支持 >10分钟长音频自动分段
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看当前模式"""
    user_id = update.effective_user.id
    current = user_mode.get(user_id, "pronunciation")
    mode_name = "🎙️ 发音评分模式" if current == "pronunciation" else "📝 录音转文字模式"
    
    pending = user_pending_file.get(user_id)
    pending_status = f"\n📁 有待处理文件: {'是' if pending and os.path.exists(pending) else '否'}"
    
    await update.message.reply_text(f"{mode_name}{pending_status}")


async def pronounce_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """切换到发音评分模式"""
    user_id = update.effective_user.id
    user_mode[user_id] = "pronunciation"
    await update.message.reply_text(
        "🎙️ 已切换到**发音评分模式**\n\n"
        "请**直接上传**英文录音文件（点击📎 → 文件），然后发送 `/process` 开始评分。",
        parse_mode='Markdown'
    )


async def transcribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """切换到录音转文字模式"""
    user_id = update.effective_user.id
    user_mode[user_id] = "transcription"
    await update.message.reply_text(
        "📝 已切换到**录音转文字模式**\n\n"
        "请**直接上传**中文录音文件（点击📎 → 文件），然后发送 `/process` 开始转写。",
        parse_mode='Markdown'
    )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """中断正在进行的转写任务"""
    user_id = update.effective_user.id
    
    if transcription.is_task_active(user_id):
        transcription.interrupt_transcription(user_id)
        await update.message.reply_text("🛑 已发送中断信号，当前片段完成后将输出已有结果并停止。")
    else:
        await update.message.reply_text("ℹ️ 当前没有正在进行的转写任务。")


async def process_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始处理用户上传的文件"""
    user_id = update.effective_user.id
    file_path = user_pending_file.get(user_id)
    
    # 检查是否有待处理文件
    if not file_path or not os.path.exists(file_path):
        await update.message.reply_text(
            "❌ 没有找到待处理的文件。\n\n"
            "请先**直接上传**录音文件（点击📎附件 → 选择文件），然后发送 /process 开始处理。\n\n"
            "⚠️ 注意：请直接上传，不要转发文件！"
        )
        return
    
    current_mode = user_mode.get(user_id, "pronunciation")
    mode_name = "发音评分" if current_mode == "pronunciation" else "转写文字"
    
    # 发送开始处理提示
    await update.message.reply_text(
        f"🎧 开始处理...\n"
        f"📁 文件: {os.path.basename(file_path)}\n"
        f"🎯 模式: {mode_name}\n\n"
        f"⏳ 请稍候，这可能需要一些时间..."
    )
    
    try:
        if current_mode == "pronunciation":
            # 发音评分模式
            result = await pronunciation.evaluate_pronunciation(
                file_path,
                get_deepseek_response
            )
            
            if result["success"]:
                # 如果反馈太长，分段发送
                feedback = result['feedback']
                if len(feedback) > 4000:
                    await update.message.reply_text(f"📝 你说的是：\n{result['text']}")
                    for i in range(0, len(feedback), 4000):
                        await update.message.reply_text(feedback[i:i+4000])
                else:
                    await update.message.reply_text(
                        f"📝 你说的是：\n{result['text']}\n\n🎙️ 评分报告：\n{feedback}"
                    )
            else:
                await update.message.reply_text(f"❌ {result['error']}")
        
        else:  # transcription 模式
            # 获取音频时长
            duration_seconds = transcription._get_audio_duration(file_path)
            duration_min = int(duration_seconds // 60)
            
            if duration_seconds > transcription.LONG_AUDIO_THRESHOLD:
                # 长音频模式
                await update.message.reply_text(
                    f"📢 检测到长音频 ({duration_min} 分钟)，启用分段模式\n"
                    f"⏱️ 每 {transcription.SEGMENT_DURATION // 60} 分钟输出一段结果\n"
                    f"💡 发送 /stop 可中断转写"
                )
                
                # 进度回调
                async def progress_callback(current, total, text):
                    if text:
                        await update.message.reply_text(
                            f"📝 **片段 {current}/{total}：**\n{text[:500]}{'...' if len(text) > 500 else ''}"
                        )
                
                result = await transcription.transcribe_long_audio(
                    file_path,
                    user_id,
                    language="zh",
                    progress_callback=progress_callback
                )
                
                if result["interrupted"]:
                    await update.message.reply_text(
                        f"🛑 **转写已中断**\n\n"
                        f"已完成 {result['segments_done']} 个片段\n\n"
                        f"**已转写内容：**\n{result['text']}"
                    )
                elif result["success"]:
                    # 分段发送长文本
                    full_text = result['text']
                    if len(full_text) > 4000:
                        for i in range(0, len(full_text), 4000):
                            await update.message.reply_text(full_text[i:i+4000])
                    else:
                        await update.message.reply_text(f"✅ **转写完成！**\n\n{full_text}")
                else:
                    await update.message.reply_text(f"❌ 转写失败: {result['error']}")
            
            else:
                # 短音频模式
                result = await transcription.transcribe_voice(file_path, language="zh")
                
                if result["success"]:
                    await update.message.reply_text(
                        f"📝 **转写结果**：\n{result['text']}\n\n🔍 检测语言：{result['language']}"
                    )
                else:
                    await update.message.reply_text(f"❌ {result['error']}")
        
        # 清理文件
        if os.path.exists(file_path):
            os.remove(file_path)
        user_pending_file[user_id] = None
        
    except Exception as e:
        logger.error(f"处理文件时出错: {e}")
        await update.message.reply_text(f"❌ 处理时出错: {str(e)}")


# ============================================================
# 文件上传处理器（统一处理所有类型的文件）
# ============================================================
async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理所有类型的文件上传（document, audio, voice）"""
    user_id = update.effective_user.id
    message = update.message
    
    # 获取文件对象和文件名
    file_obj = None
    file_name = None
    file_size = 0
    
    if message.document:
        file_obj = message.document
        file_name = message.document.file_name
        file_size = message.document.file_size
        print(f"📄 收到文档: {file_name}")
    elif message.audio:
        file_obj = message.audio
        file_name = message.audio.file_name
        file_size = message.audio.file_size
        print(f"🎵 收到音频: {file_name}")
    elif message.voice:
        file_obj = message.voice
        file_name = f"voice_{user_id}_{int(time.time())}.ogg"
        file_size = message.voice.file_size
        print(f"🎤 收到语音: {file_name}")
    else:
        # 不是文件消息，忽略
        return
    
    # 检查文件扩展名
    ext = os.path.splitext(file_name)[1].lower() if file_name else ''
    
    # 对于 voice 消息，.ogg 是支持的
    if message.voice:
        ext = '.ogg'
    
    if ext and ext not in SUPPORTED_EXTENSIONS and not message.voice:
        await update.message.reply_text(
            f"❌ 不支持的文件格式: {ext}\n\n"
            f"支持的格式: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
        return
    
    # 检查文件大小（限制 100MB）
    if file_size > 100 * 1024 * 1024:
        await update.message.reply_text("❌ 文件太大，请上传小于 100MB 的文件。")
        return
    
    # 发送下载提示
    status_msg = await update.message.reply_text(f"📥 正在下载文件: {file_name}...")
    
    try:
        # 下载文件
        file = await file_obj.get_file()
        
        # 生成保存路径
        if message.voice:
            save_path = f"user_{user_id}_{int(time.time())}.ogg"
        else:
            save_path = f"user_{user_id}_{int(time.time())}{ext}"
        
        await file.download_to_drive(save_path)
        
        # 验证文件是否下载成功
        if not os.path.exists(save_path) or os.path.getsize(save_path) == 0:
            await status_msg.edit_text("❌ 文件下载失败，请重试。")
            return
        
        # 保存文件路径
        user_pending_file[user_id] = save_path
        
        current_mode = user_mode.get(user_id, "pronunciation")
        mode_name = "发音评分" if current_mode == "pronunciation" else "转写文字"
        
        await status_msg.edit_text(
            f"✅ 文件已保存\n"
            f"📁 名称: {file_name}\n"
            f"📊 大小: {file_size / 1024:.1f} KB\n"
            f"🎯 当前模式: {mode_name}\n\n"
            f"📌 发送 `/process` 开始处理"
        )
        
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        await status_msg.edit_text(f"❌ 下载文件失败: {str(e)}")


# ============================================================
# 主程序
# ============================================================
def main():
    """启动机器人"""
    print("=" * 50)
    print("🤖 DeepSeek 语音助手正在启动...")
    print("=" * 50)
    
    # 创建应用
    application = Application.builder().token(TOKEN).build()
    
    # 注册命令处理器
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("mode", mode_command))
    application.add_handler(CommandHandler("pronounce", pronounce_command))
    application.add_handler(CommandHandler("p", pronounce_command))
    application.add_handler(CommandHandler("transcribe", transcribe_command))
    application.add_handler(CommandHandler("t", transcribe_command))
    application.add_handler(CommandHandler("process", process_command))
    application.add_handler(CommandHandler("stop", stop_command))
    
    # 注册文件处理器（重要：使用 filters.ALL 捕获所有文件类型）
    application.add_handler(MessageHandler(
        filters.Document.ALL | filters.AUDIO | filters.VOICE, 
        handle_file_upload
    ))
    
    # 处理普通文本消息
    async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "请使用命令操作。\n\n"
            "📌 发送 /help 查看使用说明。\n\n"
            "⚠️ 要上传文件，请点击输入框旁边的 📎 附件按钮。"
        )
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("✅ 所有处理器配置完成！")
    print("📌 功能模块：")
    print("   - 发音评分模块")
    print("   - 录音转文字模块")
    print("   - 手动触发处理 (/process)")
    print("=" * 50)
    print("🚀 机器人已启动，正在监听消息...")
    print("   按 Ctrl+C 停止运行")
    print("=" * 50)
    
    application.run_polling()


if __name__ == "__main__":
    main()
