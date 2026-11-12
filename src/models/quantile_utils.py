import numpy as np
import pandas as pd
from src.common import constants


def sort_quantiles(df: pd.DataFrame) -> pd.DataFrame:
    q_cols = constants.QUANTILE_COLS
    vals = np.sort(df[q_cols].to_numpy(copy=True), axis=1)
    df[q_cols] = vals
    return df
