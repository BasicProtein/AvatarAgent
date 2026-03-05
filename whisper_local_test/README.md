# Whisper 本地 GPU 测试工具

> 此目录为**独立测试目录**，可随时整体删除，不影响项目其他文件。

## 你的显卡

- RTX 3050（Ampere 架构，支持 CUDA 12.1）✅

---

## 使用步骤

### 第一次使用（安装环境）

1. 双击运行 `1_setup_cuda.bat`
   - 自动在项目 `.venv` 中安装 **PyTorch CUDA 12.1 版本**
   - 自动安装 **openai-whisper**
   - ⏱ 首次安装约需下载 2~3 GB，请耐心等待

### 验证安装（可选但推荐）

2. 双击运行 `2_test_device.bat`
   - 检测 CUDA 是否可用
   - 加载 Whisper turbo 模型（首次约 809MB）
   - 用短音频做一次真实转录测试
   - 成功后会显示绿色 ✅ 和检测到的 GPU 名称

---

## 预期输出（成功时）

```
[设备检测]
  PyTorch 版本: 2.x.x+cu121
  CUDA 可用:    是 ✅
  GPU 型号:     NVIDIA GeForce RTX 3050
  显存:         4096 MB

[模型加载]
  正在加载 Whisper turbo 模型到 cuda...
  模型加载完毕 ✅

[转录测试]
  使用 fp16 (GPU 模式)
  转录结果: ...
  耗时: x.xx 秒 ✅
```

---

## 目录说明

| 文件 | 说明 |
|------|------|
| `1_setup_cuda.bat` | CUDA 版 PyTorch + Whisper 安装脚本 |
| `2_test_device.bat` | 设备检测 + 模型测试脚本 |
| `test_asr.py` | 测试脚本主体（Python） |
| `README.md` | 本文件 |

---

## 删除方法

直接删除整个 `whisper_local_test/` 目录即可，不影响任何其他功能。
