import os
import torch
import warnings
import timesfm

# 环境变量设置
os.environ['XLA_PYTHON_CLIENT_PREALLOCATE'] = 'false'
os.environ['JAX_PMAP_USE_TENSORSTORE'] = 'false'

# 忽略警告
warnings.filterwarnings("ignore")
current_device_type = "gpu" if torch.backends.cuda.is_built() else "cpu"
if current_device_type == "cpu":
    if torch.backends.mps.is_available():
        current_device_type = "mps"
print(f"当前设备类型: {current_device_type}")
# 模型路径设置
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
runtime_api = os.environ.get("RUNTIME_API", "local")
model_dir = os.path.join(root_dir, "models", "timesfm-2.0-500m-pytorch")
if runtime_api == "docker":
    model_dir = os.path.join("/app", "timesfm-2.0-500m-pytorch")
# timesfm_dir = "/root/models/ai_tools/timesfm/senrajat_google_com/google_finetune"
original_model = os.path.join(model_dir, "torch_model.ckpt")


tfm = {}
def init_timesfm(horizon_len: int, context_len: int) -> timesfm.TimesFm:
    """
    初始化TimesFM模型
    
    Args:
        horizon_len: 预测 horizon_len 天
        context_len: 上下文长度
        
    Returns:
        timesfm.TimesFm: 初始化后的TimesFM模型实例
    """
    global tfm
    if context_len > 2048:
        context_len = 2048
    if f"{horizon_len}_{context_len}" not in tfm:
        print("初始化TimesFM模型...")
        tfm[f"{horizon_len}_{context_len}"] = timesfm.TimesFm(
            hparams=timesfm.TimesFmHparams(
                backend=current_device_type,
                per_core_batch_size=32,  # 降低批次大小以支持并发
                horizon_len=horizon_len,
                num_layers=50,
                use_positional_embedding=False,
                context_len=context_len,
            ),
            checkpoint=timesfm.TimesFmCheckpoint(
                path=original_model),
        )
        print(f"TimesFM模型 {horizon_len}_{context_len} 初始化完成")
    return tfm[f"{horizon_len}_{context_len}"]
