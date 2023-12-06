from typing import Any, Dict, Optional, Union

from ccxt.async_support import okx

from constants import (
    OKX_WAIT_FOR_WITHDRAWAL_FINAL_STATUS_ATTEMPTS,
    OKX_WAIT_FOR_WITHDRAWAL_FINAL_STATUS_DELAY_RANGE,
    OKX_WITHDRAW_DELAY_RANGE,
    OKX_WITHDRAW_TRIES,
    WAIT_FOR_DEPOSIT_DELAY_RANGE,
)
from core.chain import ARBITRUM, Chain
from core.token import ETH, Token
from logger import logger
from utils import sleep

from .client import Client
from .exceptions import WithdrawalCancelledError


class Okx:
    def __init__(
        self, client: Client, api_key: str, api_secret: str, password: str
    ) -> None:
        self.client = client
        self.api_key = api_key
        self.api_secret = api_secret
        self.password = password
        self.exchange = okx(config=self._get_config())

    def _get_config(self) -> Dict[str, Any]:
        return {
            "apiKey": self.api_key,
            "secret": self.api_secret,
            "password": self.password,
            "enableRateLimit": True,
        }

    async def withdraw(
        self,
        amount: Union[int, float],
        token: Optional[Token] = ETH,
        retry_count: Optional[int] = 0,
        chain: Optional[Chain] = ARBITRUM,
        wait_for_funds: Optional[bool] = True,
    ) -> bool:
        logger.info(
            f"[OKX] Trying to withdraw {amount} {token.symbol} to {self.client}"
        )
        async with self.exchange as exchange:
            try:
                initial_balance = await self.client.get_native_balance(chain=chain)

                withdrawal_data = await exchange.withdraw(
                    code=token.symbol,
                    amount=amount,
                    address=self.client.address,
                    params={
                        "toAddress": self.client.address,
                        "chainName": f"{token.symbol}-{chain.okx_chain_name}",
                        "dest": 4,
                        "fee": chain.okx_withdrawal_fee,
                        "pwd": "-",
                        "amt": amount,
                        "network": chain.okx_chain_name,
                    },
                )

                withdrawal_id = withdrawal_data["info"]["wdId"]
            except Exception as e:
                error_message = str(e)
                if (
                    "Withdrawal address is not allowlisted for verification exemption"
                    in error_message
                ):
                    logger.error(f"[OKX] Address {self.client} is not allowlisted")
                elif "Insufficient balance" in error_message:
                    logger.error(f"[OKX] Insufficient funds for withdrawal")
                else:
                    logger.error(
                        f"[OKX] Error while withdrawing {amount} {token.symbol} to {self.client}: {error_message}"
                    )

                if retry_count < OKX_WITHDRAW_TRIES:
                    logger.info(
                        f"[OKX] Withdrawal unsuccessful, waiting for the next try"
                    )
                    await sleep(
                        delay_range=OKX_WITHDRAW_DELAY_RANGE, send_message=False
                    )
                    return await self.withdraw(
                        retry_count=retry_count + 1, amount=amount
                    )
                else:
                    logger.error(
                        f"[OKX] Withdrawal failed, attempt limit exceeded: {e}"
                    )
                    return False
            if wait_for_funds:
                tokens_delivered = await self._watch_for_delivery(
                    withdrawal_id=withdrawal_id, initial_balance=initial_balance
                )
                if tokens_delivered:
                    logger.success(
                        f"[OKX] Successfully withdrew {amount} {token.symbol}"
                    )
                    return True
                return False
            return True

    async def _watch_for_delivery(
        self, withdrawal_id: str, initial_balance: Union[int, float]
    ) -> bool:
        withdrawal_finalized = await self._wait_for_withdrawal_final_status(
            withdrawal_id=withdrawal_id
        )
        withdrawal_recieved = await self.client.wait_for_deposit(
            initial_balance=initial_balance,
            checkup_sleep_time_range=WAIT_FOR_DEPOSIT_DELAY_RANGE,
        )
        return withdrawal_finalized and withdrawal_recieved

    async def _wait_for_withdrawal_final_status(self, withdrawal_id: str) -> bool:
        attempt_count = 1
        logger.info(f"[OKX] Waiting for withdrawal final status")
        while attempt_count < OKX_WAIT_FOR_WITHDRAWAL_FINAL_STATUS_ATTEMPTS:
            async with self.exchange as exchange:
                try:
                    status = await exchange.private_get_asset_deposit_withdraw_status(
                        params={"wdId": withdrawal_id}
                    )

                    if "Cancelation complete" in status["data"][0]["state"]:
                        raise WithdrawalCancelledError
                    if "Withdrawal complete" not in status["data"][0]["state"]:
                        attempt_count += 1
                        await sleep(
                            delay_range=OKX_WAIT_FOR_WITHDRAWAL_FINAL_STATUS_DELAY_RANGE,
                            send_message=False,
                            pr_bar=False,
                        )
                    else:
                        logger.info("[OKX] Withdrawal sent from OKX")
                        return True
                except Exception as e:
                    logger.error(f"[OKX] {e}")
                    return False
        logger.error(f"[OKX] Max attempts reached. Withdrawal status not finalized")
        return False
