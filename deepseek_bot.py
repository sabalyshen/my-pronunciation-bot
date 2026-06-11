#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DeepSeek 语音助手 - 英文发音教练
功能：接收 Telegram 语音消息，使用 Whisper 转写，调用 DeepSeek API 进行发音评分
"""

import os
import sys
import logging
import requests
import subprocess
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============================================================
# 第一部分：环境配置
# ============================================================

# 将 ffmpeg 加入 PATH（解决 Whisper 找不到 ffmpeg 的问题）
# 树莓派上 ffmpeg 通常安装在 /usr/bin/ffmpeg，这个路径已经在 PATH 中
# 如果遇到问题，可以取消下面的注释并修改为实际路径
# ffmpeg_dir = r"/usr/bin"
# os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

# 加载环境变量（从 .env 文件）
load_dotenv()

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 全局变量：从环境变量读取 API Keys
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# 检查必要的环境变量是否存在
if not TOKEN or not DEEPSEEK_API_KEY:
    raise ValueError("请检查 .env 文件中的 TELEGRAM_BOT_TOKEN 和 DEEPSEEK_API_KEY")

# 加载 Whisper 模型（全局只加载一次）
import whisper
print("正在加载 Whisper 模型（base）...")
whisper_model = whisper.load_model("small")  # 可选: tiny, base, small, medium, large
print("Whisper 模型加载完成！")

# 创建 Telegram 应用
application = Application.builder().token(TOKEN).build()

# ============================================================
# 第二部分：辅助函数
# ============================================================

def get_fallback_response(message: str) -> str:
    """当 DeepSeek API 不可用时的本地备用回复"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['你好', '您好', 'hello', 'hi', '嗨']):
        return "你好呀！👋 我是语音助手，但目前AI服务暂时不可用。"
    elif any(word in message_lower for word in ['怎么样', '你好吗', 'how are you']):
        return "我一切都好！🚀 正在努力接入AI服务中。"
    elif '?' in message or '？' in message:
        return "🤔 有趣的问题！AI服务正在配置中，请稍后再试。"
    else:
        return "消息已收到！📝 我是语音助手，正在开发中。"


async def get_deepseek_response(message: str) -> str:
    """调用 DeepSeek API 获取回复"""
    try:
        print(f"🔄 调用 DeepSeek API，消息长度: {len(message)}")
        
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
        
        # 超时设置为 30 秒
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"📡 DeepSeek 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            reply = result['choices'][0]['message']['content']
            print(f"✅ DeepSeek 回复成功，长度: {len(reply)}")
            return reply
        else:
            print(f"❌ DeepSeek 返回错误: {response.status_code} - {response.text}")
            return get_fallback_response(message)
            
    except requests.exceptions.Timeout:
        print("❌ DeepSeek API 请求超时")
        return get_fallback_response(message)
    except Exception as e:
        print(f"❌ DeepSeek API 异常: {type(e).__name__}: {e}")
        logger.error(f"AI API 调用出错: {e}")
        return get_fallback_response(message)


# ============================================================
# 第三部分：消息处理器
# ============================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    print(f"🎯 收到 /start 命令，用户: {update.effective_user.id}")
    await update.message.reply_text(
        "🤖 **DeepSeek 语音助手**\n\n"
        "你好！我是你的英文发音教练。\n\n"
        "📌 使用方法：\n"
        "• 发送文字消息 - 我会回复你\n"
        "• 发送英文语音 - 我会评分并给出改进建议\n\n"
        "发送 /help 查看更多帮助。",
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /help 命令"""
    print(f"🎯 收到 /help 命令，用户: {update.effective_user.id}")
    await update.message.reply_text(
        "ℹ️ **帮助**\n\n"
        "• /start - 启动机器人\n"
        "• /help - 显示本帮助\n\n"
        "**语音评分说明**：\n"
        "发送英文语音后，我会从以下维度评分：\n"
        "1. 发音准确度\n"
        "2. 重音与节奏\n"
        "3. 流利度\n"
        "4. 综合得分和改进建议",
        parse_mode='Markdown'
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理文字消息"""
    user_message = update.message.text
    user_id = update.effective_user.id
    print(f"📝 收到来自 {user_id} 的文本: {user_message}")
    
    try:
        response = await get_deepseek_response(user_message)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"处理文本时出错: {e}")
        await update.message.reply_text("❌ 处理消息时出错，请稍后再试。")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理语音消息：Whisper转写 + DeepSeek发音评分"""
    user_id = update.effective_user.id
    print(f"🎤 收到来自 {user_id} 的语音消息")
    
    # 临时文件路径
    ogg_path = None
    wav_path = None
    
    try:
        # 1. 获取并下载语音文件
        voice = update.message.voice
        file = await voice.get_file()
        
        ogg_path = f"voice_{user_id}.ogg"
        await file.download_to_drive(ogg_path)
        print(f"✅ 语音已保存: {ogg_path}")
        
        # 2. 发送“处理中”提示
        await update.message.reply_text("🎧 正在分析你的发音，请稍等...")
        
        # 3. 使用 ffmpeg 将 .ogg 转换为 .wav
        wav_path = ogg_path.replace('.ogg', '.wav')
        
        # 查找 ffmpeg 路径
        ffmpeg_path = "/usr/bin/ffmpeg"
        if not os.path.exists(ffmpeg_path):
            # 尝试从 PATH 中查找
            import shutil
            ffmpeg_path = shutil.which("ffmpeg") or "ffmpeg"
        
        cmd = [ffmpeg_path, "-i", ogg_path, "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav_path, "-y"]
        print(f"🔧 执行命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ FFmpeg 错误: {result.stderr}")
            await update.message.reply_text("❌ 音频格式转换失败，请稍后再试。")
            return
        
        # 检查 wav 文件是否生成成功
        if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
            print(f"❌ 转换后的文件无效: {wav_path}")
            await update.message.reply_text("❌ 音频转换失败，请稍后再试。")
            return
        
        print(f"✅ 转换后的文件大小: {os.path.getsize(wav_path)} 字节")
        
        # 4. 使用 Whisper 转写
        print("🔄 开始 Whisper 转写...")
        result = whisper_model.transcribe(wav_path)
        user_text = result["text"].strip()
        print(f"📝 Whisper 转写: {user_text}")
        
        if not user_text:
            await update.message.reply_text("❌ 没有识别到任何内容，请说得更清晰一些再试。")
            return
        
        # 5. 构造发音评分的 Prompt
        scoring_prompt = f"""你是一位专业的英语发音教练。请对以下这段英文录音的转写文本进行发音评估。

用户说的内容："{user_text}"

请按照以下格式给出评估：

【发音准确度】（0-10分）
指出具体的音素问题（例如元音、辅音、易混淆音）

【重音与节奏】（0-10分）
评估单词重音、句子重读、语调是否自然

【流利度】（0-10分）
分析是否有不自然的停顿、重复或语速问题

【综合评分】（1-10分）

【改进建议】
给出2-3条具体可操作的建议

最后用一句鼓励的话结尾。

注意：你听到的是用户的实际发音，请基于转写文本假设可能存在的发音问题。如果文本中有明显的语法或用词错误，也可以指出。"""
        
        # 6. 调用 DeepSeek API 进行评分
        print("🔄 调用 DeepSeek API 进行评分...")
        feedback = await get_deepseek_response(scoring_prompt)
        
        # 7. 回复用户
        reply_message = f"📝 你说的是：\n{user_text}\n\n🎙️ 评分报告：\n{feedback}"
        
        # 如果消息太长，Telegram 可能会分段，但通常可以一次性发送
        if len(reply_message) > 4000:
            # 如果超过限制，分开发送
            await update.message.reply_text(f"📝 你说的是：\n{user_text}")
            await update.message.reply_text(f"🎙️ 评分报告：\n{feedback}")
        else:
            await update.message.reply_text(reply_message)
        
        print("✅ 语音处理完成")
        
    except Exception as e:
        print(f"❌ 处理语音消息时出错: {type(e).__name__}: {e}")
        logger.error(f"处理语音消息出错: {e}")
        await update.message.reply_text("❌ 处理语音时出现错误，请稍后再试。")
    
    finally:
        # 清理临时文件
        for path in [ogg_path, wav_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"🗑️ 已删除临时文件: {path}")
                except Exception as e:
                    print(f"⚠️ 删除文件失败 {path}: {e}")


# ============================================================
# 第四部分：主程序入口
# ============================================================

def main():
    """主函数：配置并启动机器人"""
    
    print("=" * 50)
    print("🤖 DeepSeek 语音助手正在启动...")
    print("=" * 50)
    
    # 配置消息处理器（注意顺序）
    print("🔧 正在配置消息处理器...")
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    print("✅ 所有处理器配置完成！")
    
    # 测试 Telegram API 连接
    print("🔍 正在进行连接测试...")
    try:
        test_url = f"https://api.telegram.org/bot{TOKEN}/getMe"
        response = requests.get(test_url, timeout=10)
        if response.status_code == 200:
            bot_info = response.json()
            print(f"✅ Telegram API 连接成功")
            print(f"✅ 机器人名称: {bot_info['result']['first_name']} (@{bot_info['result']['username']})")
        else:
            print(f"❌ API 测试失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
    
    print("=" * 50)
    print("🚀 机器人已启动，正在监听消息...")
    print("   按 Ctrl+C 停止运行")
    print("=" * 50)
    
    # 启动机器人（长轮询）
    application.run_polling()


if __name__ == "__main__":
    main()
