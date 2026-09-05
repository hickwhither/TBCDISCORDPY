import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from features.connhen import repository

DAILY_REWARD = 5
DAILY_COOLDOWN = timedelta(hours=24)
CONNHEN_EMOJI = "<:connhen:1545576341804687370>"


def format_amount(amount: int) -> str:
    s = f"{amount:,}".replace(",", "'")
    return f"{s} {CONNHEN_EMOJI}"


@dataclass
class DailyResult:
    claimed: bool
    amount: int = 0
    cooldown_remaining: timedelta | None = None


@dataclass
class GambleResult:
    win: bool
    stake: int
    new_balance: int


class PayError(Enum):
    OK = "ok"
    SELF = "self"
    INSUFFICIENT = "insufficient"
    INVALID = "invalid"


async def daily(user_id: int) -> DailyResult:
    row = await repository.get_or_create(user_id)
    now = datetime.now(timezone.utc)

    if row.last_daily:
        last = row.last_daily
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        remaining = DAILY_COOLDOWN - (now - last)
        if remaining > timedelta(0):
            return DailyResult(claimed=False, cooldown_remaining=remaining)

    await repository.add_connhen(user_id, DAILY_REWARD)
    await repository.set_last_daily(user_id, now)
    return DailyResult(claimed=True, amount=DAILY_REWARD)


async def balance(user_id: int) -> int:
    row = await repository.get_or_create(user_id)
    return row.connhen


async def pay(sender_id: int, recipient_id: int, amount: int) -> PayError:
    if amount <= 0:
        return PayError.INVALID
    if sender_id == recipient_id:
        return PayError.SELF

    if not await repository.sub_connhen(sender_id, amount):
        return PayError.INSUFFICIENT

    await repository.add_connhen(recipient_id, amount)
    return PayError.OK


async def gamble(user_id: int, stake: int) -> GambleResult:
    if stake <= 0:
        return GambleResult(win=False, stake=0, new_balance=await balance(user_id))

    win = random.random() < 0.5
    if win:
        new_balance = await repository.add_connhen(user_id, stake)
    else:
        await repository.sub_connhen(user_id, stake)
        new_balance = await balance(user_id)
    return GambleResult(win=win, stake=stake, new_balance=new_balance)