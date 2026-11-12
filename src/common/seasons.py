SEASONS = ["winter", "summer", "monsoon", "post_monsoon"]


def season_of(month: int) -> str:
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5, 6):
        return "summer"
    if month in (7, 8, 9):
        return "monsoon"
    if month in (10, 11):
        return "post_monsoon"
    raise ValueError(f"Invalid month: {month}")
