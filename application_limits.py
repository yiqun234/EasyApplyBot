"""Shared daily-limit signal for the bot and scheduler."""


DAILY_LIMIT_EXIT_CODE = 75


class DailyApplyLimitReached(RuntimeError):
    def __init__(self):
        super().__init__("Daily Easy Apply limit reached")
