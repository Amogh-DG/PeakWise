import pandas as pd
from src.common import constants, seasons


SEGMENTS = [
    "all",
    "winter",
    "summer",
    "monsoon",
    "post_monsoon",
    "peak_hours",
    "off_peak",
]


def get_segment_mask(df: pd.DataFrame, segment: str) -> pd.Series:
    if segment == "all":
        return pd.Series(True, index=df.index)

    target_ts = df["target_ts"]
    month = target_ts.dt.month
    hour = target_ts.dt.hour

    if segment in seasons.SEASONS:
        season_series = month.apply(seasons.season_of)
        return season_series == segment

    if segment == "peak_hours":
        return hour.isin(constants.PEAK_HOURS)

    if segment == "off_peak":
        return ~hour.isin(constants.PEAK_HOURS)

    raise ValueError(f"Unknown segment: {segment}")
