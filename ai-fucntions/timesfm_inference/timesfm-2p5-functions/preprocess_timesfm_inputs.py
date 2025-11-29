import numpy as np
import pandas as pd
from typing import List, Optional, Sequence, Union

def df_to_timesfm_inputs(
    df: pd.DataFrame,
    value_col: Union[str, int],
    group_by: Optional[Sequence[str]] = None,
    sort_by: Optional[Sequence[str]] = None,
    ascending: Union[bool, Sequence[bool]] = True,
    max_context: Optional[int] = None,
    dtype: str = "float32",
) -> List[np.ndarray]:
    if sort_by:
        df = df.sort_values(by=list(sort_by), ascending=ascending)
    if group_by:
        inputs: List[np.ndarray] = []
        for _, g in df.groupby(list(group_by)):
            arr = np.asarray(g[value_col], dtype=dtype)
            if max_context is not None and arr.size > max_context:
                arr = arr[-max_context:]
            inputs.append(arr)
        return inputs
    arr = np.asarray(df[value_col], dtype=dtype)
    if max_context is not None and arr.size > max_context:
        arr = arr[-max_context:]
    return [arr]

def wide_df_to_timesfm_inputs(
    df: pd.DataFrame,
    columns: Optional[Sequence[Union[str, int]]] = None,
    sort_by: Optional[Sequence[str]] = None,
    ascending: Union[bool, Sequence[bool]] = True,
    max_context: Optional[int] = None,
    dtype: str = "float64",
) -> List[np.ndarray]:
    if sort_by:
        df = df.sort_values(by=list(sort_by), ascending=ascending)
    cols = list(columns) if columns is not None else list(df.columns)
    inputs: List[np.ndarray] = []
    for c in cols:
        arr = np.asarray(df[c], dtype=dtype)
        if max_context is not None and arr.size > max_context:
            arr = arr[-max_context:]
        inputs.append(arr)
    return inputs