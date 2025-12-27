#!/usr/bin/env python3
"""
环境信息收集脚本 - 用于DPO训练环境配置
运行: python check_env.py
"""

import sys
import platform
import subprocess

def run_cmd(cmd):
    """执行命令并返回输出"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except:
        return "N/A"

def check_python():
    """检查Python版本"""
    print("=" * 60)
    print("Python环境")
    print("=" * 60)
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    print()

def check_system():
    """检查系统信息"""
    print("=" * 60)
    print("系统信息")
    print("=" * 60)
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"架构: {platform.machine()}")
    print(f"处理器: {platform.processor()}")
    print()

def check_cuda():
    """检查CUDA信息"""
    print("=" * 60)
    print("CUDA信息")
    print("=" * 60)
    nvidia_smi = run_cmd("nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader")
    if nvidia_smi != "N/A":
        print("GPU信息:")
        print(nvidia_smi)
    else:
        print("未检测到NVIDIA GPU或nvidia-smi不可用")
    
    cuda_version = run_cmd("nvcc --version 2>/dev/null | grep 'release' || echo 'N/A'")
    print(f"CUDA编译器版本: {cuda_version}")
    print()

def check_packages():
    """检查关键包版本"""
    print("=" * 60)
    print("已安装的关键包")
    print("=" * 60)
    
    packages = [
        "torch",
        "torchdata",
        "transformers",
        "flash-attn",
        "liger-kernel",
        "datasets",
        "huggingface_hub",
        "safetensors",
        "omegaconf",
        "numpy",
        "tiktoken",
        "sentencepiece",
        "grouped_gemm",
    ]
    
    for pkg in packages:
        try:
            if pkg == "flash-attn":
                import flash_attn
                version = getattr(flash_attn, "__version__", "unknown")
            elif pkg == "liger-kernel":
                try:
                    import liger_kernel
                    version = getattr(liger_kernel, "__version__", "unknown")
                except:
                    version = "未安装"
            elif pkg == "grouped_gemm":
                try:
                    import grouped_gemm
                    version = getattr(grouped_gemm, "__version__", "unknown")
                except:
                    version = "未安装"
            else:
                mod = __import__(pkg.replace("-", "_"))
                version = getattr(mod, "__version__", "unknown")
            print(f"{pkg:20s}: {version}")
        except ImportError:
            print(f"{pkg:20s}: 未安装")
        except Exception as e:
            print(f"{pkg:20s}: 检查失败 ({str(e)})")
    print()

def check_torch_details():
    """检查PyTorch详细信息"""
    print("=" * 60)
    print("PyTorch详细信息")
    print("=" * 60)
    try:
        import torch
        print(f"PyTorch版本: {torch.__version__}")
        print(f"CUDA可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"CUDA版本: {torch.version.cuda}")
            print(f"cuDNN版本: {torch.backends.cudnn.version()}")
            print(f"GPU数量: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
        print(f"编译选项: {torch.__config__.show()}")
    except ImportError:
        print("PyTorch未安装")
    except Exception as e:
        print(f"检查失败: {str(e)}")
    print()

def main():
    print("\n" + "=" * 60)
    print("DPO训练环境检查")
    print("=" * 60 + "\n")
    
    check_python()
    check_system()
    check_cuda()
    check_packages()
    check_torch_details()
    
    print("=" * 60)
    print("检查完成！请将以上信息复制给我。")
    print("=" * 60)

if __name__ == "__main__":
    main()

