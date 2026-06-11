# DeepSeek 语音助手 - 英文发音教练

<div align="center">

*基于 DeepSeek AI 的 Telegram 语音助手，专为英文发音评分设计*

[![Python Version](https://img.shields.io/badge/python-3.14%2B-blue)](https://www.python.org/)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue)](https://core.telegram.org/bots)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

## 📖 项目简介

DeepSeek 语音助手是一个 Telegram 机器人，它可以：

- 接收用户发送的英文语音消息
- 使用 Whisper AI 将语音转写成文字
- 调用 DeepSeek API 对发音进行专业评分
- 从**发音准确度、重音与节奏、流利度**三个维度给出反馈
- 返回详细的评分报告和改进建议
- 录音转文字：支持长音频（>10分钟）自动分段转写，目前中文轉錄辨識度低
- 中断控制*：可随时停止长音频处理
- 練習發音時可以先輸入句子，增加句子辨識準確度


## 🛠️ 技术栈

### 核心技术
| 技术 | 用途 |
|------|------|
| Python 3.14+ | 主要编程语言 |
| python-telegram-bot | Telegram Bot API 封装 |
| OpenAI Whisper | 免费开源语音识别模型 |
| DeepSeek API | 大语言模型，用于发音评分 |
| FFmpeg | 音频格式转换（.oga → .wav） |

### 辅助库
- `python-dotenv` - 环境变量管理
- `requests` - HTTP 请求
- `logging` - 日志记录

## 🚀 安装与配置

### 系统要求

```bash
# 确保已安装以下工具
python --version   # 需要 3.10 或更高版本
git --version      # 需要 2.20 或更高版本
ffmpeg -version    # 需要 6.0 或更高版本
安装步骤
bash
# 1. 克隆项目到本地
git clone https://github.com/sabalyshen/my-pronunciation-bot.git
cd my-pronunciation-bot

# 2. 创建 Python 虚拟环境
python3 -m venv venv

# 3. 激活虚拟环境
# Linux / macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 创建配置文件
cp .env.example .env

# 6. 编辑 .env 文件，填入你的 API 密钥
nano .env
🔑 获取 API 密钥
1. Telegram Bot Token
在 Telegram 中搜索 @BotFather

发送 /newbot 命令

按照提示设置机器人名称和用户名

复制获得的 Token（格式类似：1234567890:ABCdefGHIjklMNOpqrsTUVwxyz）

2. DeepSeek API Key
访问 DeepSeek 开放平台 注册账号

进入 API Keys 页面

点击 Create new API key

复制生成的密钥（格式类似：sk-xxxxxxxxxxxxxxxx）

📁 项目结构
text
my-pronunciation-bot/
├── deepseek_bot.py          # 机器人主程序
├── requirements.txt         # Python 依赖列表
├── .env                     # 配置文件（需自行创建）
├── .env.example             # 配置文件模板
├── .gitignore               # Git 忽略文件
└── README.md                # 项目说明
🔄 工作流程
text
用户发送英文语音
       ↓
Telegram 服务器
       ↓
机器人下载语音文件 (.oga)
       ↓
FFmpeg 转换为 .wav
       ↓
Whisper 转写为文字
       ↓
DeepSeek API 评分
       ↓
返回评分报告给用户
📝 使用示例
用户发送语音后，机器人会回复类似：

text
📝 你说的是：
Hello, my name is Ted. Nice to meet you.

🎙️ 评分报告：
【发音准确度】8/10
“name”中的 /eɪ/ 元音可以更饱满

【重音与节奏】7/10
“Nice to meet you”语调可以更自然

【流利度】9/10
整体流畅，无明显停顿

【综合评分】8/10

【改进建议】
1. 练习 /eɪ/ 和 /æ/ 的区分
2. 注意句尾语调上扬

继续加油！💪
❓ 常见问题
1. ModuleNotFoundError: No module named 'whisper'
bash
# 重新安装依赖
pip install openai-whisper
2. FFmpeg 找不到
bash
# Linux (Debian/Ubuntu)
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# 下载并添加到 PATH
3. 语音转写失败
确保麦克风录制清晰

尽量使用较短的语音（建议 < 30 秒）

检查网络连接

4. DeepSeek API 认证失败
检查 .env 中的 API Key 是否正确

确认账户有足够余额

检查 API Key 状态是否为“启用”

📄 许可证
本项目基于 MIT 许可证开源。

🙏 致谢与引用
本项目基于以下开源项目构建：

NailGusmanov/Deepseek_voice_assistant - 原始项目，提供了基础的 Telegram + Whisper + DeepSeek 集成框架

OpenAI Whisper - 语音识别模型

python-telegram-bot - Telegram Bot 框架

DeepSeek API - 大语言模型服务# DeepSeek Voice Assistant

<div align="center">

*Голосовой ассистент для Telegram на основе DeepSeek AI*

[![Python Version](https://img.shields.io/badge/python-3.14%2B-blue)](https://www.python.org/)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue)](https://core.telegram.org/bots)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

## Что это за проект?

DeepSeek Voice Assistant - это Telegram бот, который:
- Принимает голосовые сообщения от пользователей
- Преобразует речь в текст с помощью Whisper AI
- Обрабатывает запросы через DeepSeek API
- Отвечает текстовыми сообщениями

## Технологии которые используются

### Основные технологии:
- Python 3.14 - основной язык программирования (протестировано на Python 3.14)
- python_telegram_bot - библиотека для работы с Telegram API
- OpenAI Whisper - бесплатная модель для распознавания речи
- DeepSeek API - искусственный интеллект для обработки запросов
- FFmpeg - инструмент для обработки аудиофайлов

### Вспомогательные библиотеки:
- python-dotenv - для управления настройками
- requests - для отправки HTTP запросов
- logging - для ведения логов работы бота

## Установка и настройка

### Предварительные требования

   ```bash
python - 3.14 version
git - 2.51.1 version
ffmpeg - 8.0 version

# Копируем проект на ваш компьютер
git clone https://github.com/NailGusmanov/deepseek_voice_assistant.git
cd deepseek_voice_assistant

# Создаем изолированное окружение для Python
python -m venv venv

# Активируем окружение
# Для Windows:
venv\Scripts\activate

# Устанавливаем все нужные библиотеки
pip install -r requirements.txt

# Копируем шаблон настроек
cp .env.example .env

# Редактируем файл .env текстовым редактором
# Добавляйте ваши реальные API ключи

Получение API ключей

1. Telegram Bot Token

1. Найти в Telegram @BotFather
2. Отправить команду /newbot
3. Выбрать имя и username для бота
4. Скопировать выданный токен

2. DeepSeek API Key

1. Зарегистрироваться на platform.deepseek.com
2. Перейти в раздел API Keys
3. Создать новый API ключ
4. Скопировать ключ

# Убедитесь что виртуальное окружение активировано
venv\Scripts\activate    # для Windows

# Запускаем бота
python_deepseek_bot.py

# Структура проекта
deepseek_voice_assistant/
├── deepseek_bot.py          # Основной код бота
├── requirements.txt         # Список зависимостей
├── .env.example            # Шаблон настроек
├── .gitignore              # Игнорируемые файлы
└── README.md               # Эта инструкция

# Как работает бот
Пользователь → Голосовое сообщение → Telegram → Наш сервер →

Распознавание речи → Текст запроса → DeepSeek API → Текстовый ответ

# Частые проблемы
1. "ModuleNotFoundError"
  
   # Решение: переустановить зависимости
   pip install -r requirements.txt

2. Проблемы с API ключами
   · Проверить что файл .env создан
   · Убедиться что ключи вписаны без кавычек
   · Проверить что файл находится в той же папке что и бот

Если у вас возникли вопросы:

1. Проверьте этот README еще раз 😂
