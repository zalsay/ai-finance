import numpy as np
def mean_squared_error(y_pred, y_true):
    """
    计算均方误差
    """
    return np.mean((y_true - y_pred) ** 2)


def mean_absolute_error(y_pred, y_true):
    """
    计算平均绝对误差
    """
    return np.mean(np.abs(y_true - y_pred))