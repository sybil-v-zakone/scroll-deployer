from decimal import Decimal
from typing import Optional, Union

from config import GAS_DELAY_RANGE, GAS_THRESHOLD
from constants import (
    ARBITRUM_ORBITER_CONTRACT_ADDRESS,
    ORBITER_ARB_SCROLL_TRADING_FEE,
    ORBITER_MIN_SENT_VALUE,
    WAIT_FOR_DEPOSIT_DELAY_RANGE,
)
from logger import logger
from utils import gas_delay

from .chain import Chain
from .client import Client
from .token import ETH, Token


class Orbiter:
    def __init__(self, src_chain_client: Client, dst_chain_client: Client) -> None:
        self.src_chain_client = src_chain_client
        self.dst_chain_client = dst_chain_client

    @gas_delay(gas_threshold=GAS_THRESHOLD, delay_range=GAS_DELAY_RANGE)
    async def bridge(
        self,
        amount: Union[int, float],
        dst_chain: Chain,
        token: Optional[Token] = ETH,
        wait_for_funds: Optional[bool] = True,
    ) -> bool:
        value = Orbiter._adjust_amount(
            amount=amount,
            chain_code=dst_chain.orbiter_id,
        )
        if amount < ORBITER_MIN_SENT_VALUE:
            logger.error(
                f"[Orbiter] Specified value `{amount}` is lower than minimum sent value `{ORBITER_MIN_SENT_VALUE}`"
            )
            return False
        logger.info(
            f"[Orbiter] Bridging {value} {token.symbol} from {self.src_chain_client.chain.name} to {self.dst_chain_client.chain.name}"
        )

        try:
            initial_dst_chain_balance = await self.dst_chain_client.get_native_balance()
            tx_hash = await self.src_chain_client.send_transaction(
                value=token.to_wei(value=value), to=ARBITRUM_ORBITER_CONTRACT_ADDRESS
            )
            if tx_hash:
                tx_verified = await self.src_chain_client.verify_tx(tx_hash=tx_hash)
                if wait_for_funds and tx_verified:
                    return await self.dst_chain_client.wait_for_deposit(
                        initial_balance=initial_dst_chain_balance,
                        checkup_sleep_time_range=WAIT_FOR_DEPOSIT_DELAY_RANGE,
                    )
                return tx_verified
            return False
        except Exception as e:
            logger.info(f"[ORBITER] Couldn't execute bridge transaction: {e}")
            return False

    @staticmethod
    def _adjust_amount(
        amount: float,
        chain_code: str,
        trading_fee: Optional[float] = ORBITER_ARB_SCROLL_TRADING_FEE,
    ) -> float:
        return Decimal("{:.14f}{}".format(amount + trading_fee, chain_code))
