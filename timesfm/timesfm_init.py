import os
import sys
import warnings


# 环境变量设置
os.environ['XLA_PYTHON_CLIENT_PREALLOCATE'] = 'false'
os.environ['JAX_PMAP_USE_TENSORSTORE'] = 'false'

# 忽略警告
warnings.filterwarnings("ignore")

# 添加akshare工具路径
finance_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
akshare_dir = os.path.join(finance_dir, 'akshare-tools')
sys.path.append(akshare_dir)
from get_finanial_data import ak_stock_data, get_stock_list, get_index_data, talib_tools

# 模型路径设置
current_dir = os.path.abspath("..")
timesfm_dir = "/root/models/ai_tools/timesfm/senrajat_google_com/google_finetune"
original_model = "/root/workers/finance/timesfm/timesfm-2.0-500m-pytorch/torch_model.ckpt"

# 导入TimesFM
import timesfm
tfm = None
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
    if tfm is None:
        print("初始化TimesFM模型...")
        tfm = timesfm.TimesFm(
            hparams=timesfm.TimesFmHparams(
                backend="gpu",
                per_core_batch_size=32,  # 降低批次大小以支持并发
                horizon_len=horizon_len,
                num_layers=50,
                use_positional_embedding=False,
                context_len=context_len,
            ),
            checkpoint=timesfm.TimesFmCheckpoint(
                path=original_model),
        )
        print("TimesFM模型初始化完成")
    return tfm