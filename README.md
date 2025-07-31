# Dolphin 语音转录工具 - 用户手册与配置指南

## 1. 简介

本手册旨在为“Dolphin 语音转录工具”的用户提供全面的使用指导和配置说明。Dolphin 语音转录工具是一个基于 OpenAI Whisper 的高效语音转录解决方案，专为中国大陆用户进行了优化，有效解决了模型下载和网络访问的难题。

## 2. 主要特性

- 🎯 **专为中国大陆优化**: 利用HF镜像源，确保用户能够顺畅访问和下载模型，解决网络限制问题。
- 🚀 **简单易用**: 提供一键式安装流程和直观的命令行操作界面，降低使用门槛。
- 📊 **准确性评估**: 内置词错误率（WER）计算功能，帮助用户量化评估转录结果的准确性。
- 🔧 **多模型支持**: 全面支持Whisper系列模型，从轻量级的 `tiny` 到高性能的 `large`，满足不同场景的需求。
- 🌍 **多语言支持**: 除了中文，还支持英文等多种主流语言的语音转录。
- ⚡ **设备灵活**: 兼容CPU和GPU，用户可根据硬件条件选择最佳运行设备，实现加速转录。
- 📁 **大文件处理**: 引入大文件分割处理机制，显著提升处理效率和稳定性，有效避免内存溢出问题。

## 3. 快速开始

### 3.1. 环境准备

在开始使用前，请确保您的系统已安装 Python 3.7 或更高版本。您可以通过以下命令检查 Python 版本：

```bash
python --version
```

### 3.2. 安装依赖

所有必要的 Python 依赖项都已列在 `requirements.txt` 文件中。请使用 `pip` 进行安装：

```bash
pip install -r requirements.txt
```

**FFmpeg 安装**：

FFmpeg 是处理音频文件所必需的工具。对于 Windows 用户，您可以选择以下方式安装：

- **手动下载**: 访问 [FFmpeg 官方网站](https://ffmpeg.org/download.html) 下载适合您系统的版本，并将其 `bin` 目录添加到系统环境变量 `PATH` 中。
- **使用 Chocolatey**: 如果您已安装 Chocolatey 包管理器，可以通过以下命令安装 FFmpeg：
  ```bash
  choco install ffmpeg
  ```

### 3.3. 配置镜像源（强烈推荐）

为了确保模型下载的顺畅，建议配置 Hugging Face (HF) 镜像源。您可以运行提供的环境配置脚本：

```bash
# Windows 系统
setup_env.bat
```

或者，您也可以手动设置环境变量：

```bash
set HF_ENDPOINT=https://hf-mirror.com
```

### 3.4. 基本使用示例

完成环境配置后，您可以通过 `main.py` 脚本进行基本的语音转录操作：

- **基本转录**: 
  ```bash
  python main.py "path/to/your/audio.mp3"
  ```

- **指定模型和语言**: 
  ```bash
  python main.py "audio.mp3" --model base --language zh
  ```

- **使用 GPU 加速（如果可用）**: 
  ```bash
  python main.py "audio.mp3" --device cuda
  ```

- **保存结果到文件**: 
  ```bash
  python main.py "audio.mp3" --output result.txt
  ```

## 4. 详细使用说明

### 4.1. 命令行参数详解

#### `main.py` - 语音转录脚本

用于执行语音到文本的转录任务。

**用法**: 
```bash
python main.py <音频文件> [选项]
```

**参数说明**:
- `audio_path` (必需): 待转录的音频文件路径。
- `--model` (可选): 指定使用的 Whisper 模型大小。可选值包括：
  - `tiny`: 最小的模型，转录速度最快，适用于快速测试或资源受限环境。
  - `base`: 平衡了速度与准确性，推荐日常使用。
  - `small`: 提供更好的转录准确性。
  - `medium`: 具有较高的转录准确性。
  - `large`: 最大的模型，提供最高的转录准确性，但需要更多的计算资源。
  （默认值: `tiny`）
- `--language` (可选): 指定音频的语言代码。例如 `zh` 代表中文，`en` 代表英文。
  （默认值: `zh`）
- `--device` (可选): 指定运行设备。可选值 `cpu` 或 `cuda` (如果您的系统支持GPU加速)。
- `--output` (可选): 指定转录结果的输出文件路径。如果不指定，结果将打印到控制台。

**示例**:
```bash
# 使用 tiny 模型转录中文音频
python main.py "录音.mp3"

# 使用 base 模型转录，并将结果保存到 "转录结果.txt"
python main.py "录音.mp3" --model base --output "转录结果.txt"

# 转录英文音频，使用 small 模型
python main.py "english_audio.wav" --language en --model small
```

#### `evaluate.py` - 准确性评估脚本

用于评估语音转录的准确性，通常通过计算词错误率 (WER) 来实现。

**用法**: 
```bash
python evaluate.py <音频文件> [选项]
```

**参数说明**:
- `audio_path` (必需): 用于评估的测试音频文件路径。
- `--model` (可选): 指定用于转录的 Whisper 模型大小。
- `--language` (可选): 指定音频的语言代码。
- `--device` (可选): 指定运行设备。
- `--truth` (必需): 提供与 `audio_path` 对应的标准（真实）文本，用于与转录结果进行对比。

**示例**:
```bash
# 评估转录准确性，提供标准文本
python evaluate.py "test_audio.mp3" --truth "这是标准的转录文本"

# 使用 base 模型评估，并提供标准文本
python evaluate.py "test_audio.mp3" --model base --truth "标准文本"
```

## 5. 支持的音频格式

Dolphin 语音转录工具支持多种常见的音频格式，包括但不限于：

- MP3
- WAV
- M4A
- FLAC
- OGG
- 以及其他 FFmpeg 支持的音频格式

## 6. 模型选择指南

选择合适的 Whisper 模型对于平衡转录速度和准确性至关重要。下表提供了不同模型的概览和推荐用途：

| 模型   | 大小    | 速度   | 准确性 | 推荐用途                               |
|--------|---------|--------|--------|----------------------------------------|
| `tiny`   | ~39MB   | 最快   | 一般   | 快速测试、低配置设备、对准确性要求不高 |
| `base`   | ~74MB   | 较快   | 良好   | 日常使用推荐，平衡性能与准确性         |
| `small`  | ~244MB  | 中等   | 很好   | 对准确性有较高要求，同时兼顾速度       |
| `medium` | ~769MB  | 较慢   | 优秀   | 高质量转录，适用于对准确性要求严苛的场景 |
| `large`  | ~1550MB | 最慢   | 最佳   | 专业级转录，追求极致准确性，需要充足资源 |

## 7. 故障排除

### 7.1. 网络连接问题

如果在模型下载过程中遇到网络连接问题或下载失败，请尝试以下解决方案：

- **运行环境配置脚本**: 再次运行 `setup_env.bat` 脚本以确保镜像源配置正确。
  ```bash
  setup_env.bat
  ```
- **手动设置镜像源**: 确认环境变量 `HF_ENDPOINT` 已设置为 `https://hf-mirror.com`。
  ```bash
  set HF_ENDPOINT=https://hf-mirror.com
  ```

### 7.2. FFmpeg 未安装或未配置

如果系统提示找不到 FFmpeg 或相关错误，请确保 FFmpeg 已正确安装并将其 `bin` 目录添加到系统 `PATH` 环境变量中。

**Windows 用户**:
1. **下载并解压**: 从 [FFmpeg 官方网站](https://ffmpeg.org/download.html) 下载 FFmpeg，解压到一个您方便的目录（例如 `C:\ffmpeg`）。
2. **添加环境变量**: 将解压目录下的 `bin` 文件夹路径（例如 `C:\ffmpeg\bin`）添加到系统的 `PATH` 环境变量中。

**使用包管理器安装**:
- **Chocolatey**: 
  ```bash
  choco install ffmpeg
  ```
- **Scoop**: 
  ```bash
  scoop install ffmpeg
  ```

### 7.3. 内存不足错误

当处理大型音频文件或使用大型模型时，可能会遇到内存不足（Out of Memory）错误。请尝试以下方法：

- **使用更小的模型**: 优先选择 `tiny` 或 `base` 等内存占用较小的模型进行转录。
- **关闭其他程序**: 确保在运行转录工具时，关闭其他占用大量内存的应用程序。
- **考虑使用 CPU**: 如果您的 GPU 内存不足，可以尝试将 `--device` 参数设置为 `cpu`，虽然速度会变慢，但可以避免内存问题。

### 7.4. CUDA 相关问题

如果在使用 GPU 加速时遇到问题（例如 CUDA 不可用），请进行以下检查：

- **检查 CUDA 可用性**: 运行以下 Python 代码，确认 PyTorch 是否能检测到 CUDA 设备。
  ```bash
  python -c "import torch; print(torch.cuda.is_available())"
  ```
  如果返回 `False`，则表示 CUDA 不可用。在这种情况下，程序将自动回退到 CPU 进行处理。
- **驱动和 CUDA 版本**: 确保您的显卡驱动程序是最新的，并且安装的 CUDA Toolkit 版本与 PyTorch 兼容。

## 8. 高级用法

### 8.1. 批量处理音频文件

对于需要处理大量音频文件的场景，您可以创建批处理脚本来自动化转录过程。以下是一个简单的 Windows 批处理脚本示例：

**`batch_process.bat`**:
```batch
@echo off
for %%f in (*.mp3) do (
    echo Processing %%f
    python main.py "%%f" --output "%%~nf_transcript.txt"
)
```

将此脚本放置在包含您要处理的 `.mp3` 音频文件的目录中，然后运行它。脚本将遍历所有 `.mp3` 文件，并为每个文件生成一个对应的转录文本文件。
