import streamlit as st
import os
import sys
import time
import json
import re
import openai
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import threading
import queue
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import tempfile
import logging
import traceback
import subprocess
import hashlib
import shutil
import re
from typing import Optional, Dict, Any, List, Tuple
import warnings
from streamlit_mic_recorder import mic_recorder

# 忽略警告以保持输出清洁
warnings.filterwarnings("ignore")

# 配置中文友好的日志系统
class ChineseFormatter(logging.Formatter):
    """中文友好的日志格式化器"""
    def format(self, record):
        # 确保所有日志消息都以中文输出
        if hasattr(record, 'msg') and record.msg:
            # 将英文错误信息转换为中文
            error_translations = {
                'Connection error': '连接错误',
                'Timeout error': '超时错误',
                'File not found': '文件未找到',
                'Permission denied': '权限被拒绝',
                'Invalid format': '格式无效',
                'Processing failed': '处理失败',
                'API error': 'API错误',
                'Network error': '网络错误'
            }
            
            msg = str(record.msg)
            for en, zh in error_translations.items():
                msg = msg.replace(en, zh)
            record.msg = msg
        
        return super().format(record)

# 配置日志系统 - 直接输出到命令行
def setup_logging():
    """设置中文友好的日志系统"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # 清除现有处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 设置中文友好的格式
    formatter = ChineseFormatter(
        '%(asctime)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    return logger

logger = setup_logging()

# Add FFmpeg to PATH for pydub
ffmpeg_path = r'd:\zhuanlu\ffmpeg_portable'
if ffmpeg_path not in os.environ['PATH']:
    os.environ['PATH'] += os.pathsep + ffmpeg_path

sys.path.insert(0, r'd:\zhuanlu\Dolphin-main')
from dolphin.transcribe import load_model, transcribe, transcribe_long
from dolphin.constants import SPEECH_LENGTH
from dolphin.audio import load_audio
import pydub
from pydub import AudioSegment
from pydub.effects import normalize, high_pass_filter

# 加载OpenAI API密钥
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# 页面配置 - 中文优化
st.set_page_config(
    page_title="智能语音转录助手 - 中文专业版",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 中文友好的自定义CSS样式
st.markdown("""
<style>
    /* 全局中文字体优化 */
    .main {
        font-family: "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", "WenQuanYi Micro Hei", sans-serif;
    }
    
    /* 标题样式优化 */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        font-weight: 700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header p {
        font-size: 1.2rem;
        opacity: 0.9;
        margin: 0;
    }
    
    /* 文件上传区域样式 */
    .upload-area {
        border: 3px dashed #667eea;
        border-radius: 15px;
        padding: 3rem;
        text-align: center;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        margin: 2rem 0;
        transition: all 0.3s ease;
    }
    
    .upload-area:hover {
        border-color: #764ba2;
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    
    /* 进度条样式 */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    /* 成功消息样式 */
    .success-message {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        font-weight: 500;
    }
    
    /* 错误消息样式 */
    .error-message {
        background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        font-weight: 500;
    }
    
    /* 信息卡片样式 */
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 5px solid #667eea;
    }
    
    /* 文本区域样式 */
    .stTextArea textarea {
        font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
        font-size: 16px;
        line-height: 1.6;
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        transition: border-color 0.3s ease;
    }
    
    .stTextArea textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 10px rgba(102, 126, 234, 0.3);
    }
    
    /* 按钮样式优化 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
    }
    
    /* 侧边栏样式 */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* 文件信息显示 */
    .file-info {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #28a745;
    }
    
    .progress-container {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
    }
    .export-button {
        background: #28a745;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        border: none;
        cursor: pointer;
        margin: 0.25rem;
    }
    .selectable-text {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        font-family: 'Courier New', monospace;
        line-height: 1.6;
        user-select: text;
        -webkit-user-select: text;
        -moz-user-select: text;
        -ms-user-select: text;
    }
    .api-section {
        background: #e3f2fd;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    /* 统计信息样式 */
    .stats-container {
        display: flex;
        justify-content: space-around;
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    .stat-item {
        text-align: center;
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
    }
    
    .stat-label {
        color: #666;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# 大文件预处理功能
class FilePreprocessor:
    """大文件预处理器 - 专为中文音频优化"""
    
    def __init__(self):
        self.temp_dir = Path("temp")
        self.temp_dir.mkdir(exist_ok=True)
        self.max_chunk_size = 25 * 1024 * 1024  # 25MB per chunk
        self.supported_formats = ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma']
        
    def get_file_hash(self, file_path: str) -> str:
        """获取文件哈希值用于缓存"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def check_file_format(self, file_path: str) -> bool:
        """检查文件格式是否支持"""
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.supported_formats
    
    def get_audio_info(self, file_path: str) -> Dict[str, Any]:
        """获取音频文件信息"""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(file_path)
            
            info = {
                'duration': len(audio) / 1000,  # 秒
                'channels': audio.channels,
                'sample_rate': audio.frame_rate,
                'format': Path(file_path).suffix.lower(),
                'size': os.path.getsize(file_path),
                'bitrate': audio.frame_rate * audio.sample_width * 8 * audio.channels
            }
            
            logger.info(f"音频文件信息: 时长 {info['duration']:.1f}秒, 采样率 {info['sample_rate']}Hz, 声道数 {info['channels']}")
            return info
            
        except Exception as e:
            logger.error(f"获取音频信息失败: {str(e)}")
            return {}
    
    def optimize_audio_for_chinese(self, file_path: str) -> str:
        """为中文语音识别优化音频"""
        try:
            from pydub import AudioSegment
            from pydub.effects import normalize
            
            logger.info("开始优化音频以提高中文识别准确率...")
            
            # 加载音频
            audio = AudioSegment.from_file(file_path)
            
            # 中文语音优化处理
            # 1. 转换为单声道（中文语音识别通常在单声道下效果更好）
            if audio.channels > 1:
                audio = audio.set_channels(1)
                logger.info("已转换为单声道")
            
            # 2. 设置最适合中文的采样率 (16kHz)
            if audio.frame_rate != 16000:
                audio = audio.set_frame_rate(16000)
                logger.info("已设置采样率为16kHz（中文语音识别最佳）")
            
            # 3. 音量标准化
            audio = normalize(audio)
            logger.info("已进行音量标准化")
            
            # 4. 降噪处理（简单的高通滤波）
            # 移除低频噪音，保留中文语音的主要频率范围
            audio = audio.high_pass_filter(80)
            logger.info("已应用高通滤波器去除低频噪音")
            
            # 保存优化后的文件
            optimized_path = str(self.temp_dir / f"optimized_{Path(file_path).name}")
            audio.export(optimized_path, format="wav")
            
            logger.info(f"音频优化完成，保存至: {optimized_path}")
            return optimized_path
            
        except Exception as e:
            logger.error(f"音频优化失败: {str(e)}")
            return file_path
    
    def split_large_file(self, file_path: str, chunk_duration: int = 300) -> List[str]:
        """分割大文件为小块（默认5分钟一块）"""
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(file_path)
            duration_ms = len(audio)
            chunk_duration_ms = chunk_duration * 1000
            
            if duration_ms <= chunk_duration_ms:
                return [file_path]
            
            logger.info(f"文件较大（{duration_ms/1000:.1f}秒），开始分割为{chunk_duration}秒的片段...")
            
            chunks = []
            chunk_count = 0
            
            for start_ms in range(0, duration_ms, chunk_duration_ms):
                end_ms = min(start_ms + chunk_duration_ms, duration_ms)
                chunk = audio[start_ms:end_ms]
                
                chunk_filename = f"chunk_{chunk_count:03d}_{Path(file_path).stem}.wav"
                chunk_path = str(self.temp_dir / chunk_filename)
                
                chunk.export(chunk_path, format="wav")
                chunks.append(chunk_path)
                chunk_count += 1
                
                logger.info(f"已创建片段 {chunk_count}: {start_ms/1000:.1f}s - {end_ms/1000:.1f}s")
            
            logger.info(f"文件分割完成，共创建 {len(chunks)} 个片段")
            return chunks
            
        except Exception as e:
            logger.error(f"文件分割失败: {str(e)}")
            return [file_path]
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            for file_path in self.temp_dir.glob("*"):
                if file_path.is_file():
                    file_path.unlink()
            logger.info("临时文件清理完成")
        except Exception as e:
            logger.error(f"清理临时文件失败: {str(e)}")

# 初始化文件预处理器
preprocessor = FilePreprocessor()

# 主标题 - 中文专业版
st.markdown("""
<div class="main-header">
    <h1>🎙️ 智能语音转录助手</h1>
    <p>专业中文语音识别 | 支持大文件处理 | AI智能优化</p>
</div>
""", unsafe_allow_html=True)

# 侧边栏配置 - 中文优化
with st.sidebar:
    st.markdown("### 🔧 转录配置")
    # 添加新优化选项
    enable_ai_enhance = st.checkbox("启用AI增强转录", value=True, help="使用AI优化转录结果")
    
    # Whisper模型选择
    model_name = st.selectbox(
        "选择Whisper模型",
        options=["small", "base", "medium", "large"],
        index=1,
        help="更大的模型准确率更高，但处理速度较慢"
    )
    
    # 设备选择
    device = st.selectbox(
        "计算设备",
        options=["cpu", "cuda"],
        index=0,
        help="如果有NVIDIA GPU，选择cuda可以显著提升速度"
    )
    
    # 语言设置 - 默认中文
    language = st.selectbox(
        "识别语言",
        options=["zh", "auto", "en"],
        index=0,  # 默认中文
        format_func=lambda x: {
            "zh": "中文（推荐）",
            "auto": "自动检测",
            "en": "英文"
        }[x],
        help="建议选择中文以获得最佳识别效果"
    )
    
    st.markdown("---")
    
    # 大文件处理选项
    st.markdown("### 📁 大文件处理")
    
    enable_preprocessing = st.checkbox(
        "启用音频预处理",
        value=True,
        help="为中文语音识别优化音频质量"
    )
    
    auto_split = st.checkbox(
        "自动分割大文件",
        value=True,
        help="将长音频分割为小段以提高处理效率"
    )
    
    chunk_duration = st.slider(
        "分割时长（分钟）",
        min_value=1,
        max_value=10,
        value=5,
        help="每个音频片段的时长"
    )
    
    st.markdown("---")
    
    # AI优化配置
    st.markdown("### 🤖 AI文本优化")
    enable_ai_optimization = st.checkbox("启用AI文本优化", value=False)
    
    if enable_ai_optimization:
        api_provider = st.selectbox(
            "选择AI服务商",
            ["硅基流动", "火山大模型", "OpenAI", "Claude", "本地模型"],
            index=0,
            help="选择用于文本优化的AI服务"
        )
        
        # 根据选择的提供商显示相应的配置
        if api_provider == "OpenAI":
            api_key = st.text_input("OpenAI API Key", type="password")
            api_model = st.selectbox("模型", ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"])
            api_base_url = st.text_input("Base URL (可选)", value="https://api.openai.com/v1")
            
        elif api_provider == "Claude":
            api_key = st.text_input("Claude API Key", type="password")
            api_model = st.selectbox("模型", ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"])
            api_base_url = st.text_input("Base URL (可选)", value="https://api.anthropic.com")
            
        elif api_provider == "硅基流动":
            api_key = st.text_input("硅基流动 API Key", type="password")
            api_model = st.selectbox("模型", [
                "Qwen/Qwen2.5-7B-Instruct",
                "Qwen/Qwen2.5-14B-Instruct", 
                "Qwen/Qwen2.5-32B-Instruct",
                "THUDM/glm-4-9b-chat",
                "01-ai/Yi-1.5-9B-Chat-16K"
            ])
            api_base_url = st.text_input("Base URL", value="https://api.siliconflow.cn/v1")
            
        elif api_provider == "火山大模型":
            api_key = st.text_input("火山引擎 API Key", type="password")
            api_model = st.selectbox("模型", [
                "doubao-lite-4k",
                "doubao-pro-4k", 
                "doubao-pro-32k",
                "doubao-pro-128k"
            ])
            api_base_url = st.text_input("Base URL", value="https://ark.cn-beijing.volces.com/api/v3")
            
        elif api_provider == "本地模型":
            api_key = ""
            api_model = st.text_input("模型名称", value="qwen2.5:7b")
            api_base_url = st.text_input("本地模型URL", value="http://localhost:11434/v1")
    
    st.markdown("---")
    
    # 系统信息
    st.markdown("### ℹ️ 系统信息")
    
    if st.button("清理临时文件"):
        preprocessor.cleanup_temp_files()
        st.success("临时文件已清理")
    
    # 显示支持的格式
    with st.expander("支持的音频格式"):
        st.write("• MP3 - 最常用格式")
        st.write("• WAV - 无损格式")
        st.write("• M4A - Apple设备录音")
        st.write("• FLAC - 无损压缩")
        st.write("• AAC - 高质量压缩")
        st.write("• OGG - 开源格式")
        st.write("• WMA - Windows格式")

# 初始化session state
if 'transcription_result' not in st.session_state:
    st.session_state.transcription_result = ""
    st.session_state.enhanced_result = ""
    st.session_state.transcription_result = ""
if 'progress' not in st.session_state:
    st.session_state.progress = 0
if 'is_transcribing' not in st.session_state:
    st.session_state.is_transcribing = False
if 'real_time_text' not in st.session_state:
    st.session_state.real_time_text = ""
if 'optimized_text' not in st.session_state:
    st.session_state.optimized_text = None

# 初始化文件预处理器
preprocessor = FilePreprocessor()

# AI优化功能
async def optimize_text_with_ai(text, provider, optimization_type, custom_prompt="", api_config=None):
    """使用AI优化文本，带重试机制和中文语言约束"""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # 构建优化提示，强制使用中文输出
            base_constraint = "请用中文回复，保持文本的中文特色和表达习惯。"
            
            if optimization_type == "语法纠错":
                prompt = f"{base_constraint}请纠正以下中文文本中的语法错误，保持原意不变，确保符合中文语法规范：\n\n{text}"
            elif optimization_type == "标点符号优化":
                prompt = f"{base_constraint}请为以下中文文本添加正确的中文标点符号（如句号、逗号、问号等）：\n\n{text}"
            elif optimization_type == "文本润色":
                prompt = f"{base_constraint}请润色以下中文文本，使其更加流畅自然，符合中文表达习惯：\n\n{text}"
            elif optimization_type == "格式整理":
                prompt = f"{base_constraint}请整理以下中文文本的格式，使其更加规范，保持中文排版特点：\n\n{text}"
            elif optimization_type == "自定义提示":
                prompt = f"{base_constraint}{custom_prompt}\n\n{text}"
            else:
                prompt = f"{base_constraint}请优化以下中文文本，使其更加准确和流畅：\n\n{text}"
            
            # 设置更长的超时时间
            timeout = aiohttp.ClientTimeout(total=120)  # 增加到120秒
            
            # 根据不同提供商构建请求
            if provider == "OpenAI":
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_config['api_key']}"
                }
                data = {
                    "model": api_config['model'],
                    "messages": [
                        {"role": "system", "content": "你是一个专业的中文文本优化助手，请始终用中文回复。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 3000
                }
                endpoint = f"{api_config['base_url']}/chat/completions"
                
            elif provider == "硅基流动":
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_config['api_key']}"
                }
                data = {
                    "model": api_config['model'],
                    "messages": [
                        {"role": "system", "content": "你是一个专业的中文文本优化助手，请始终用中文回复。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 3000
                }
                endpoint = f"{api_config['base_url']}/chat/completions"
                
            elif provider == "火山大模型":
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_config['api_key']}"
                }
                data = {
                    "model": api_config['model'],
                    "messages": [
                        {"role": "system", "content": "你是一个专业的中文文本优化助手，请始终用中文回复。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 3000
                }
                endpoint = f"{api_config['base_url']}/chat/completions"
                
            elif provider == "Claude":
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": api_config['api_key'],
                    "anthropic-version": "2023-06-01"
                }
                data = {
                    "model": api_config['model'],
                    "max_tokens": 3000,
                    "system": "你是一个专业的中文文本优化助手，请始终用中文回复。",
                    "messages": [{"role": "user", "content": prompt}]
                }
                endpoint = f"{api_config['base_url']}/v1/messages"
            
            # 发送异步请求
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(endpoint, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if provider == "Claude":
                            return result["content"][0]["text"]
                        else:
                            return result["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        raise Exception(f"API请求失败 ({response.status}): {error_text}")
                        
        except asyncio.TimeoutError:
            retry_count += 1
            if retry_count >= max_retries:
                raise Exception(f"AI优化请求超时，已重试{max_retries}次，请检查网络连接或稍后重试")
            await asyncio.sleep(2)  # 等待2秒后重试
            continue
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise Exception(f"AI优化失败: {str(e)}")
            await asyncio.sleep(1)  # 等待1秒后重试
            continue
    
    raise Exception("AI优化失败: 超过最大重试次数")

# 实时转录功能
def real_time_transcribe_callback(text_chunk):
    """实时转录回调函数"""
    if 'real_time_text' not in st.session_state:
        st.session_state.real_time_text = ""
    st.session_state.real_time_text += text_chunk + " "

# 优化的转录函数
@st.cache_data(ttl=3600)  # 缓存1小时
def get_audio_info(audio_path):
    """获取音频信息（带缓存）"""
    audio = pydub.AudioSegment.from_file(audio_path)
    return {
        'duration': audio.duration_seconds,
        'channels': audio.channels,
        'frame_rate': audio.frame_rate,
        'sample_width': audio.sample_width
    }

def filter_chinese_content(text):
    """过滤并保留中文内容，移除非中文字符和词汇"""
    if not text:
        return ""
    
    import re
    
    # 定义中文字符范围（包括中文标点符号）
    chinese_pattern = r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3000-\u303f\uff00-\uffef]'
    
    # 常见的非中文词汇模式（日语、韩语等）
    non_chinese_patterns = [
        r'[\u3040-\u309f]',  # 日语平假名
        r'[\u30a0-\u30ff]',  # 日语片假名
        r'[\uac00-\ud7af]',  # 韩语
        r'[\u0e00-\u0e7f]',  # 泰语
        r'[\u0900-\u097f]',  # 梵语/印地语
    ]
    
    # 移除明显的非中文字符
    for pattern in non_chinese_patterns:
        text = re.sub(pattern, '', text)
    
    # 分割文本为词汇/短语
    words = re.findall(r'[^\s\n]+', text)
    filtered_words = []
    
    for word in words:
        # 检查词汇是否包含中文字符
        if re.search(chinese_pattern, word):
            # 进一步过滤：如果词汇主要是中文字符，则保留
            chinese_chars = len(re.findall(chinese_pattern, word))
            total_chars = len(word)
            
            # 如果中文字符占比超过50%，则认为是中文内容
            if total_chars > 0 and chinese_chars / total_chars >= 0.5:
                filtered_words.append(word)
    
    # 重新组合文本
    filtered_text = ''.join(filtered_words)
    
    # 最终检查：如果过滤后的文本太短或没有中文，返回空字符串
    if len(filtered_text) < 2 or not re.search(chinese_pattern, filtered_text):
        return ""
    
    return filtered_text


def optimized_transcribe(model, audio_path, callback=None, progress_callback=None, enable_preprocessing=True, auto_split=True, chunk_duration=5):
    """优化的转录函数，支持实时回调、进度更新和大文件处理"""
    try:
        # 获取音频信息
        audio_info = get_audio_info(audio_path)
        audio_duration = audio_info['duration']
        
        logger.info(f"开始处理音频文件，时长: {audio_duration:.1f}秒")
        
        if progress_callback:
            progress_callback(10, f"音频时长: {audio_duration:.1f}秒")
        
        # 音频预处理
        processed_audio_path = audio_path
        if enable_preprocessing:
            if progress_callback:
                progress_callback(15, "正在优化音频质量...")
            
            try:
                processed_audio_path = preprocessor.optimize_audio_for_chinese(audio_path)
                logger.info("音频预处理完成")
            except Exception as e:
                logger.warning(f"音频预处理失败，使用原始文件: {str(e)}")
                processed_audio_path = audio_path
        
        # 根据音频长度选择合适的转录方法
        if audio_duration > SPEECH_LENGTH:
            if progress_callback:
                progress_callback(30, "开始长音频处理...")
            
            # 长音频处理 - 使用transcribe_long进行VAD分割
            segments = transcribe_long(
                model=model, 
                audio=processed_audio_path,
                lang_sym="zh",  # 强制指定中文
                region_sym="CN"  # 指定中国大陆
            )
            
            # 合并所有分段的转录结果
            transcription_text = ""
            for segment in segments:
                segment_text = segment.text if hasattr(segment, 'text') else str(segment)
                if segment_text:
                    transcription_text += segment_text + " "
            
            # 中文文本优化和过滤
            if transcription_text:
                transcription_text = filter_chinese_content(transcription_text)
                transcription_text = re.sub(r'\s+', '', transcription_text.strip())
            
            if callback:
                callback(transcription_text)
            
            if progress_callback:
                progress_callback(80, "转录完成")
            
            return transcription_text
        else:
            if progress_callback:
                progress_callback(40, "开始短音频处理...")
            
            # 短音频直接处理 - 使用transcribe
            result = transcribe(
                model=model, 
                audio=processed_audio_path,
                lang_sym="zh",  # 强制指定中文
                region_sym="CN"  # 指定中国大陆
            )
            transcription_text = result.text if hasattr(result, 'text') else str(result)
            
            # 中文文本优化和过滤
            if transcription_text:
                transcription_text = filter_chinese_content(transcription_text)
                transcription_text = re.sub(r'\s+', '', transcription_text.strip())
            
            if callback:
                callback(transcription_text)
            
            if progress_callback:
                progress_callback(80, "转录完成")
            
            return transcription_text
            
    except Exception as e:
        error_msg = f"转录失败: {str(e)}"
        logger.error(error_msg)
        if progress_callback:
            progress_callback(0, error_msg)
        raise Exception(error_msg)
    
    finally:
        # 清理预处理的临时文件
        if enable_preprocessing and processed_audio_path != audio_path:
            try:
                os.unlink(processed_audio_path)
            except:
                pass

# 一键导出功能
def create_export_package(transcription_text, model_name, language):
    """创建导出包"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 统计信息
    char_count = len(transcription_text)
    word_count = len(transcription_text.split())
    line_count = transcription_text.count('\n') + 1
    
    # 创建不同格式的内容
    export_data = {
        'txt': transcription_text,
        'json': {
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "language": language,
            "transcription": transcription_text,
            "statistics": {
                "characters": char_count,
                "words": word_count,
                "lines": line_count
            }
        },
        'markdown': f"""# 语音转录结果

**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**模型**: {model_name}
**语言**: {language}

## 转录内容

{transcription_text}

## 统计信息

- 字符数: {char_count}
- 词数: {word_count}
- 行数: {line_count}
""",
        'statistics': {
            'characters': char_count,
            'words': word_count,
            'lines': line_count
        }
    }
    
    return export_data, timestamp

# 加载模型
@st.cache_resource
def load_transcription_model(model_name, device):
    model_dir = Path.home() / '.cache' / 'dolphin' / 'models'
    return load_model(model_name, model_dir=model_dir, device=device)

# 文件上传区域
st.markdown('<div class="feature-card">', unsafe_allow_html=True)
st.subheader("📁 音频文件上传")

uploaded_file = st.file_uploader(
    '选择音频文件', 
    type=['mp3', 'wav', 'ogg', 'm4a', 'flac'],
    help="支持多种音频格式，建议使用WAV或MP3格式以获得最佳效果"
)

if uploaded_file is not None:
    # 显示文件信息
    file_details = {
        "文件名": uploaded_file.name,
        "文件大小": f"{uploaded_file.size / 1024 / 1024:.2f} MB",
        "文件类型": uploaded_file.type
    }
    
    col1, col2 = st.columns(2)
    with col1:
        st.json(file_details)
    
    with col2:
        # 音频预览
        st.audio(uploaded_file, format=uploaded_file.type)

# 实时麦克风录制
st.subheader("🎤 实时麦克风录制")
audio = mic_recorder(
    start_prompt="开始录制",
    stop_prompt="停止录制",
    just_once=False,
    use_container_width=True
)

if audio:
    # 保存录制的音频到临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
        tmp_file.write(audio['bytes'])
        uploaded_file = type('UploadedFile', (), {'name': 'recorded_audio.wav', 'getvalue': lambda: audio['bytes'], 'type': 'audio/wav', 'size': len(audio['bytes'])})()
    st.audio(audio['bytes'], format='audio/wav')

st.markdown('</div>', unsafe_allow_html=True)

# 转录功能
if uploaded_file is not None:
    st.markdown('<div class="feature-card">', unsafe_allow_html=True)
    st.subheader("🎯 语音转录")
    st.subheader("🌐 翻译功能")
    if st.button("翻译为英文"):
        if st.session_state.transcription_result:
            # 假设我们有音频路径或文本，这里简单翻译文本
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": f"Translate to English: {st.session_state.transcription_result}"}]
            )
            translated_text = response.choices[0].message.content
            st.write("翻译结果:", translated_text)
        else:
            st.warning("请先进行转录")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        transcribe_button = st.button(
            "🚀 开始转录", 
            type="primary",
            disabled=st.session_state.is_transcribing,
            use_container_width=True
        )
    
    with col2:
        if st.session_state.is_transcribing:
            st.button("⏹️ 停止转录", key="stop_transcribe", use_container_width=True)
    
    with col3:
        clear_button = st.button("🗑️ 清除结果", use_container_width=True)
        if clear_button:
            st.session_state.transcription_result = ""
            st.session_state.progress = 0
            st.session_state.real_time_text = ""
    
    # 实时进度条和状态显示
    if st.session_state.is_transcribing or st.session_state.progress > 0:
        st.markdown('<div class="progress-container">', unsafe_allow_html=True)
        st.subheader("📊 转录进度")
        
        progress_bar = st.progress(st.session_state.progress / 100)
        progress_text = st.empty()
        progress_text.text(f"进度: {st.session_state.progress}%")
        
        if st.session_state.is_transcribing:
            status_text = st.empty()
            status_text.info("🔄 正在处理音频文件...")
        
        # 实时转录文本显示
        if st.session_state.real_time_text:
            st.markdown("**实时转录内容：**")
            st.markdown(
                f'<div class="selectable-text">{st.session_state.real_time_text}</div>',
                unsafe_allow_html=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 转录处理
    if transcribe_button and not st.session_state.is_transcribing:
        st.session_state.is_transcribing = True
        st.session_state.progress = 0
        st.session_state.real_time_text = ""
        
        # 使用临时文件优化性能
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            audio_path = tmp_file.name
        
        # 创建实时显示容器
        real_time_container = st.empty()
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        try:
            # 加载模型（使用缓存优化）
            status_placeholder.info('🤖 正在加载模型...')
            model = load_transcription_model(model_name, device)
            st.session_state.progress = 20
            progress_placeholder.progress(0.2)
            
            # 分析音频（异步优化）
            status_placeholder.info('🎵 正在分析音频文件...')
            audio_duration = pydub.AudioSegment.from_file(audio_path).duration_seconds
            st.session_state.progress = 40
            progress_placeholder.progress(0.4)
            
            # 执行转录（实时显示）
            status_placeholder.info('🗣️ 正在执行语音转录...')
            
            def update_real_time_display(text_chunk):
                st.session_state.real_time_text += text_chunk + " "
                real_time_container.markdown(
                    f'<div class="selectable-text">实时转录: {st.session_state.real_time_text}</div>',
                    unsafe_allow_html=True
                )
            
            def update_progress_display(progress, message):
                st.session_state.progress = min(progress, 95)
                progress_placeholder.progress(st.session_state.progress / 100)
                status_placeholder.info(f'🔄 {message}')
            
            transcription = optimized_transcribe(
                model=model, 
                audio_path=audio_path,
                callback=update_real_time_display,
                progress_callback=update_progress_display,
                enable_preprocessing=enable_preprocessing,
                auto_split=auto_split,
                chunk_duration=chunk_duration
            )
            
            # 处理结果
            status_placeholder.info('📝 正在处理转录结果...')
            st.session_state.transcription_result = transcription
            st.session_state.progress = 100
            progress_placeholder.progress(1.0)
            status_placeholder.success("✅ 转录完成！")
            
            # 清理临时文件
            os.unlink(audio_path)
            
            # 自动显示一键导出按钮
            export_data, timestamp = create_export_package(transcription, model_name, language)
            
            st.markdown("### 📤 快速导出")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button(
                    label="📄 导出TXT",
                    data=export_data['txt'],
                    file_name=f"transcription_{timestamp}.txt",
                    mime="text/plain",
                    type="primary",
                    use_container_width=True
                )
                # 添加更多导出选项，如CSV
            with col2:
                st.download_button(
                    label="📋 导出JSON",
                    data=json.dumps(export_data['json'], ensure_ascii=False, indent=2),
                    file_name=f"transcription_{timestamp}.json",
                    mime="application/json",
                    type="primary",
                    use_container_width=True
                )
            with col3:
                st.download_button(
                    label="📝 导出MD",
                    data=export_data['markdown'],
                    file_name=f"transcription_{timestamp}.md",
                    mime="text/markdown",
                    type="primary",
                    use_container_width=True
                )
            
            # 自动刷新页面显示结果
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ 转录失败: {str(e)}")
            status_placeholder.error(f"❌ 转录失败: {str(e)}")
            # 清理临时文件
            if 'audio_path' in locals():
                try:
                    os.unlink(audio_path)
                except:
                    pass
        finally:
            st.session_state.is_transcribing = False
    
    st.markdown('</div>', unsafe_allow_html=True)

# 结果显示和操作
if st.session_state.transcription_result:
    st.markdown('<div class="feature-card">', unsafe_allow_html=True)
    st.subheader("📄 转录结果")
    
    # 可选择的文本显示
    st.markdown(
        f'<div class="selectable-text">{st.session_state.transcription_result}</div>',
        unsafe_allow_html=True
    )
    
    # 文本统计
    word_count = len(st.session_state.transcription_result.split())
    char_count = len(st.session_state.transcription_result)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("字符数", char_count)
    with col2:
        st.metric("词数", word_count)
    with col3:
        st.metric("行数", st.session_state.transcription_result.count('\n') + 1)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 导出功能
    st.markdown('<div class="feature-card">', unsafe_allow_html=True)
    st.subheader("💾 导出选项")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # 导出为TXT
        txt_data = st.session_state.transcription_result
        st.download_button(
            label="📄 导出TXT",
            data=txt_data,
            file_name=f"transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )
    
    with col2:
        # 导出为JSON
        json_data = {
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "language": language,
            "transcription": st.session_state.transcription_result,
            "statistics": {
                "characters": char_count,
                "words": word_count,
                "lines": st.session_state.transcription_result.count('\n') + 1
            }
        }
        st.download_button(
            label="📋 导出JSON",
            data=json.dumps(json_data, ensure_ascii=False, indent=2),
            file_name=f"transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with col3:
        # 导出为Markdown
        newline_count = st.session_state.transcription_result.count('\n') + 1
        md_data = f"""# 语音转录结果

**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**模型**: {model_name}
**语言**: {language}

## 转录内容

{st.session_state.transcription_result}

## 统计信息

- 字符数: {char_count}
- 词数: {word_count}
- 行数: {newline_count}
"""
        st.download_button(
            label="📝 导出Markdown",
            data=md_data,
            file_name=f"transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
    
    with col4:
        # 复制到剪贴板
        if st.button("📋 复制文本"):
            st.code(st.session_state.transcription_result)
            st.success("文本已显示，请手动复制")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # AI文本优化
    if st.session_state.get('transcription_result'):
        st.header("🤖 AI文本优化")
        
        # AI服务商选择
        ai_provider = st.selectbox(
            "选择AI服务商",
            ["OpenAI", "硅基流动", "火山大模型", "Claude"],
            key="ai_provider_select"
        )
        
        # 根据选择的服务商显示配置
        if ai_provider == "OpenAI":
            openai_api_key = st.text_input("OpenAI API Key", type="password", key="openai_key_input")
            openai_base_url = st.text_input("Base URL (可选)", value="https://api.openai.com/v1", key="openai_base_url")
            openai_model = st.selectbox("选择模型", ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"], key="openai_model_select")
            
        elif ai_provider == "硅基流动":
            siliconflow_api_key = st.text_input("硅基流动 API Key", type="password", key="siliconflow_key_input")
            siliconflow_base_url = st.text_input("Base URL", value="https://api.siliconflow.cn/v1", key="siliconflow_base_url")
            siliconflow_model = st.selectbox(
                "选择模型", 
                ["Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V2.5", "meta-llama/Meta-Llama-3.1-70B-Instruct"],
                key="siliconflow_model_select"
            )
            
        elif ai_provider == "火山大模型":
            volcano_api_key = st.text_input("火山大模型 API Key", type="password", key="volcano_key_input")
            volcano_base_url = st.text_input("Base URL", value="https://ark.cn-beijing.volces.com/api/v3", key="volcano_base_url")
            volcano_model = st.selectbox(
                "选择模型", 
                ["doubao-pro-4k", "doubao-lite-4k", "doubao-pro-32k"],
                key="volcano_model_select"
            )
            
        elif ai_provider == "Claude":
            claude_api_key = st.text_input("Claude API Key", type="password", key="claude_key_input")
            claude_base_url = st.text_input("Base URL", value="https://api.anthropic.com", key="claude_base_url")
            claude_model = st.selectbox(
                "选择模型", 
                ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"],
                key="claude_model_select"
            )
        
        # 优化类型选择
        optimization_type = st.selectbox(
            "选择优化类型",
            ["语法纠错", "标点符号优化", "文本润色", "格式整理", "自定义提示"],
            key="optimization_type_select"
        )
        
        # 自定义提示
        custom_prompt = ""
        if optimization_type == "自定义提示":
            custom_prompt = st.text_area(
                "输入自定义优化提示",
                placeholder="请输入您希望AI如何优化文本的具体要求...",
                key="custom_prompt_input"
            )
        
        # 优化控制按钮
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 开始优化", type="primary", use_container_width=True):
                # 检查API密钥
                api_key_valid = False
                if ai_provider == "OpenAI" and openai_api_key:
                    api_key_valid = True
                elif ai_provider == "硅基流动" and siliconflow_api_key:
                    api_key_valid = True
                elif ai_provider == "火山大模型" and volcano_api_key:
                    api_key_valid = True
                elif ai_provider == "Claude" and claude_api_key:
                    api_key_valid = True
                
                if not api_key_valid:
                    st.error(f"请输入{ai_provider}的API Key")
                elif optimization_type == "自定义提示" and not custom_prompt.strip():
                    st.error("请输入自定义优化提示")
                else:
                    # 执行AI优化
                    with st.spinner(f"正在使用{ai_provider}优化文本..."):
                        try:
                            # 准备API参数
                            if ai_provider == "OpenAI":
                                api_config = {
                                    "api_key": openai_api_key,
                                    "base_url": openai_base_url,
                                    "model": openai_model
                                }
                            elif ai_provider == "硅基流动":
                                api_config = {
                                    "api_key": siliconflow_api_key,
                                    "base_url": siliconflow_base_url,
                                    "model": siliconflow_model
                                }
                            elif ai_provider == "火山大模型":
                                api_config = {
                                    "api_key": volcano_api_key,
                                    "base_url": volcano_base_url,
                                    "model": volcano_model
                                }
                            elif ai_provider == "Claude":
                                api_config = {
                                    "api_key": claude_api_key,
                                    "base_url": claude_base_url,
                                    "model": claude_model
                                }
                            
                            # 异步执行优化
                            optimized_result = asyncio.run(
                                optimize_text_with_ai(
                                    text=st.session_state.transcription_result,
                                    provider=ai_provider,
                                    optimization_type=optimization_type,
                                    custom_prompt=custom_prompt,
                                    api_config=api_config
                                )
                            )
                            
                            st.session_state.optimized_text = optimized_result
                            st.success(f"✅ 使用{ai_provider}优化完成！")
                            
                        except Exception as e:
                            st.error(f"❌ 优化失败: {str(e)}")
        
        with col2:
            if st.button("🔄 重置优化", use_container_width=True):
                st.session_state.optimized_text = None
                st.rerun()
        
        # 显示优化结果
        if st.session_state.get('optimized_text'):
            st.subheader("📊 优化结果对比")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**原始文本**")
                st.text_area(
                    "原始转录结果",
                    value=st.session_state.transcription_result,
                    height=300,
                    key="original_text_display"
                )
                
                # 原始文本统计
                original_chars = len(st.session_state.transcription_result)
                original_words = len(st.session_state.transcription_result.split())
                st.caption(f"字符数: {original_chars} | 词数: {original_words}")
            
            with col2:
                st.markdown("**优化后文本**")
                st.text_area(
                    "AI优化结果",
                    value=st.session_state.optimized_text,
                    height=300,
                    key="optimized_text_display"
                )
                
                # 优化文本统计
                optimized_chars = len(st.session_state.optimized_text)
                optimized_words = len(st.session_state.optimized_text.split())
                st.caption(f"字符数: {optimized_chars} | 词数: {optimized_words}")
            
            # 替换原文选项
            if st.button("🔄 用优化结果替换原文", use_container_width=True):
                st.session_state.transcription_result = st.session_state.optimized_text
                st.session_state.optimized_text = None
                st.success("✅ 已替换原文！")
                st.rerun()
            
            # 优化结果导出
            st.subheader("📤 导出优化结果")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # TXT导出
                st.download_button(
                    label="📄 导出TXT",
                    data=st.session_state.optimized_text,
                    file_name=f"optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with col2:
                # JSON导出
                optimized_json = {
                    "original_text": st.session_state.transcription_result,
                    "optimized_text": st.session_state.optimized_text,
                    "ai_provider": ai_provider,
                    "optimization_type": optimization_type,
                    "timestamp": datetime.now().isoformat(),
                    "statistics": {
                        "original": {
                            "characters": len(st.session_state.transcription_result),
                            "words": len(st.session_state.transcription_result.split())
                        },
                        "optimized": {
                            "characters": len(st.session_state.optimized_text),
                            "words": len(st.session_state.optimized_text.split())
                        }
                    }
                }
                st.download_button(
                    label="📊 导出JSON",
                    data=json.dumps(optimized_json, ensure_ascii=False, indent=2),
                    file_name=f"optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with col3:
                # Markdown导出
                optimized_markdown = f"""# AI文本优化结果

## 优化信息
- **AI服务商**: {ai_provider}
- **优化类型**: {optimization_type}
- **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 原始文本
{st.session_state.transcription_result}

## 优化后文本
{st.session_state.optimized_text}

## 统计对比
- **原始**: {len(st.session_state.transcription_result)}字符, {len(st.session_state.transcription_result.split())}词
- **优化后**: {len(st.session_state.optimized_text)}字符, {len(st.session_state.optimized_text.split())}词
"""
                st.download_button(
                    label="📝 导出MD",
                    data=optimized_markdown,
                    file_name=f"optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with col4:
                # 对比报告导出
                comparison_report = f"""# 文本优化对比报告

## 基本信息
- **优化时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **AI服务商**: {ai_provider}
- **优化类型**: {optimization_type}

## 文本统计对比
| 项目 | 原始文本 | 优化后文本 | 变化 |
|------|----------|------------|------|
| 字符数 | {len(st.session_state.transcription_result)} | {len(st.session_state.optimized_text)} | {len(st.session_state.optimized_text) - len(st.session_state.transcription_result):+d} |
| 词数 | {len(st.session_state.transcription_result.split())} | {len(st.session_state.optimized_text.split())} | {len(st.session_state.optimized_text.split()) - len(st.session_state.transcription_result.split()):+d} |

## 详细内容

### 原始文本
```
{st.session_state.transcription_result}
```

### 优化后文本
```
{st.session_state.optimized_text}
```
"""
                st.download_button(
                    label="📋 对比报告",
                    data=comparison_report,
                    file_name=f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )

# 页脚信息
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>🐬 Dolphin Audio Transcription | 基于深度学习的高精度语音识别</p>
    <p>支持多种音频格式 | 实时进度跟踪 | AI智能优化</p>
</div>
""", unsafe_allow_html=True)