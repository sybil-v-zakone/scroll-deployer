import random

from config import (
    ACTION_DELAY_RANGE,
    CUSTOM_BYTECODE,
    OKX_API_KEY,
    OKX_API_PASSWORD,
    OKX_API_SECRET,
    OKX_WITHDRAW_AMOUNT_RANGE,
    ORBITER_BRIDGE_AMOUNT_RANGE,
    USE_CUSTOM_CONTRACT,
    USE_MOBILE_PROXY,
)
from constants import DEPLOYER_ABI_FILE_PATH
from core.chain import ARBITRUM, SCROLL
from core.client import Client
from core.okx import Okx
from core.orbiter import Orbiter
from logger import logger
from utils import read_from_json, sleep

from .database import Database


class Deployer:
    @staticmethod
    async def deploy_mode() -> None:
        db = Database.read_from_json()
        while not db.is_empty():
            wallet, index = db.get_random_wallet()
            scroll_client = Client(private_key=wallet.private_key, proxy=wallet.proxy)
            arbitrum_client = Client(
                private_key=wallet.private_key, proxy=wallet.proxy, chain=ARBITRUM
            )
            if USE_MOBILE_PROXY:
                await scroll_client.change_ip()
            logger.info(f"Working with wallet {scroll_client}")
            if not wallet.withdrawn_from_okx:
                okx = Okx(
                    client=arbitrum_client,
                    api_key=OKX_API_KEY,
                    api_secret=OKX_API_SECRET,
                    password=OKX_API_PASSWORD,
                )
                amount = round(random.uniform(*OKX_WITHDRAW_AMOUNT_RANGE), 7)
                withdrawn_from_okx = await okx.withdraw(amount=amount)
                db.update_wallet(
                    item_index=index, withdrawn_from_okx=withdrawn_from_okx
                )
                await sleep(delay_range=ACTION_DELAY_RANGE, send_message=False)
                continue
            elif not wallet.bridged_to_scroll:
                orbiter = Orbiter(
                    src_chain_client=arbitrum_client, dst_chain_client=scroll_client
                )
                amount = round(random.uniform(*ORBITER_BRIDGE_AMOUNT_RANGE), 8)
                bridged_to_scroll = await orbiter.bridge(
                    amount=amount, dst_chain=SCROLL
                )
                db.update_wallet(item_index=index, bridged_to_scroll=bridged_to_scroll)
                await sleep(delay_range=ACTION_DELAY_RANGE, send_message=False)
                continue
            elif not wallet.contract_deployed:
                abi, byte_code = None, None
                if USE_CUSTOM_CONTRACT:
                    abi = read_from_json(file_path=DEPLOYER_ABI_FILE_PATH)
                    byte_code = CUSTOM_BYTECODE
                contract_deployed = await scroll_client.deploy_contract(
                    abi=abi, bytecode=byte_code
                )
                if contract_deployed:
                    db.delete_wallet(wallet_index=index)
                await sleep(delay_range=ACTION_DELAY_RANGE, send_message=False)
                continue
        logger.success("No more wallets left")
