import binascii
import re
import sys
from typing import Any, Dict, List, Optional, Union

import aiohttp
from aiohttp_proxy import ProxyConnector
from eth_account import Account
from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from loguru import logger
from web3 import AsyncWeb3

from config import GAS_DELAY_RANGE, GAS_THRESHOLD, PROXY_CHANGE_IP_URL
from constants import PROXY_PATTERN, REQUEST_MAX_RETRIES, VERIFY_TX_TIMEOUT
from logger import logger
from utils import gas_delay, retry, sleep

from .chain import SCROLL, Chain
from .exceptions import NoRPCEndpointSpecifiedError


class Client:
    def __init__(
        self, private_key: str, proxy: str = None, chain: Optional[Chain] = SCROLL
    ) -> None:
        self.private_key: str = self._set_private_key(private_key=private_key)
        self.chain: Chain = chain
        self.proxy: str = self._set_proxy(proxy=proxy)
        self.w3: AsyncWeb3 = self._init_w3(chain=chain)
        self.address: ChecksumAddress = self.w3.to_checksum_address(
            value=self.w3.eth.account.from_key(private_key=private_key).address
        )

    def __str__(self):
        return f"{self.address[:6]}...{self.address[-4:]}"

    def _set_proxy(self, proxy: str) -> str:
        if proxy is None:
            return proxy
        pattern = re.compile(pattern=PROXY_PATTERN)
        if pattern.match(proxy):
            return proxy
        logger.error(
            f"Invalid proxy format. The correct format is 'username:password@ip_address:port'."
        )
        sys.exit(1)

    def _get_proxy_connector(self) -> Optional[ProxyConnector]:
        if self.proxy:
            proxy_url = f"http://{self.proxy}"
            return ProxyConnector.from_url(url=proxy_url)
        return None

    def _set_private_key(self, private_key: str) -> str:
        try:
            Account.from_key(private_key=private_key)
            return private_key
        except binascii.Error:
            logger.error(f"Private key `{private_key}` is not a valid hex string.")
            sys.exit(1)
        except ValueError as e:
            logger.error(f"{e} `{private_key}`")
            sys.exit(1)

    def _init_w3(self, chain: Chain):
        if self.proxy:
            request_kwargs = {"proxy": f"http://{self.proxy}"}
        else:
            request_kwargs = {}

        try:
            if not chain.rpc:
                raise NoRPCEndpointSpecifiedError(chain=chain)
            return AsyncWeb3(
                AsyncWeb3.AsyncHTTPProvider(
                    endpoint_uri=chain.rpc, request_kwargs=request_kwargs
                ),
            )
        except Exception as e:
            logger.error(e)
            sys.exit(1)

    @retry(tries=REQUEST_MAX_RETRIES)
    async def get_native_balance(self, chain: Chain = SCROLL) -> Optional[int]:
        w3 = self._init_w3(chain=chain)
        try:
            return await w3.eth.get_balance(self.address)
        except Exception as e:
            logger.error(f"Couldn't get balance of {self}: {e}")
            return None

    async def wait_for_deposit(
        self,
        initial_balance: int,
        checkup_sleep_time_range: List[int],
        attempts: Optional[int] = None,
    ) -> bool:
        if not attempts:
            attempts = True

        logger.info(f"Waiting for funds on {self.chain.name}")

        while attempts:
            final_balance = await self.get_native_balance(chain=self.chain)
            if final_balance > initial_balance:
                logger.info(f"Funds on {self.chain.name} received")
                return True
            if attempts is not True:
                attempts -= 1
            await sleep(
                delay_range=checkup_sleep_time_range,
                send_message=False,
                pr_bar=False,
            )
        logger.error(f"Funds not received on {self.chain.name}")
        return False

    @retry(tries=REQUEST_MAX_RETRIES)
    async def _get_gas_estimate(
        self, tx_params: Dict[str, Union[str, int, None]]
    ) -> Optional[int]:
        try:
            return await self.w3.eth.estimate_gas(tx_params)
        except Exception as e:
            logger.error(f"Transaction estimate failed: {e}")
            return None

    @retry(tries=REQUEST_MAX_RETRIES)
    async def _get_tx_params(
        self,
        to: Optional[str] = None,
        data: Optional[str] = None,
        from_: Optional[str] = None,
        value: Optional[int] = None,
    ) -> Dict[str, Union[str, int]]:
        if not from_:
            from_ = self.address

        tx_params: Dict[str, Union[str, int]] = {
            "chainId": await self.w3.eth.chain_id,
            "nonce": await self.w3.eth.get_transaction_count(self.address),
            "from": self.w3.to_checksum_address(from_),
        }

        if to:
            tx_params["to"] = to
        if data:
            tx_params["data"] = data
        if value is not None:
            tx_params["value"] = value
        tx_params["gasPrice"] = await self.w3.eth.gas_price

        return tx_params

    async def send_transaction(
        self,
        to: Optional[str] = None,
        data: Optional[str] = None,
        from_: Optional[str] = None,
        value: Optional[int] = None,
    ) -> Optional[HexBytes]:
        """
        Sends a transaction on the current client's blockchain.

        Parameters:
        - to (str): The recipient's Ethereum address.
        - data (str, optional): Additional data to include in the transaction.
        - from_ (str, optional): The sender's Ethereum address. If not provided,
          the address associated with the initialized wallet will be used.
        - value (int, optional): The amount of Ether (in wei) to be sent with the transaction.

        Returns:
        - Optional[HexBytes]: The transaction hash if successful, otherwise None.

        Note:
        This method signs and sends an Ethereum transaction using the specified parameters.
        """
        tx_params = await self._get_tx_params(
            to=to, data=data, from_=from_, value=value
        )
        gas = await self._get_gas_estimate(tx_params=tx_params)
        if gas is None:
            return None
        tx_params["gas"] = gas

        signed_tx = self.w3.eth.account.sign_transaction(tx_params, self.private_key)

        try:
            return await self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        except Exception as e:
            logger.error(f"Error while sending transaction: {e}")
            return None

    async def verify_tx(
        self, tx_hash: HexBytes, timeout: int = VERIFY_TX_TIMEOUT
    ) -> bool:
        """
        Verifies the status of a transaction on the current client's blockchain.

        Parameters:
        - tx_hash (HexBytes): The hash of the transaction to be verified.
        - timeout (int, optional): The maximum time (in seconds) to wait for the transaction receipt.
          Defaults to the value specified by VERIFY_TX_TIMEOUT.

        Returns:
        - bool: True if the transaction was successful, False otherwise.

        Note:
        This method checks the status of a transaction using its hash. It waits for the transaction
        receipt and logs the success or failure of the transaction with the corresponding log level.
        """
        try:
            response = await self.w3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=timeout
            )

            if "status" in response and response["status"] == 1:
                logger.success(
                    f"Transaction was successful: {self.chain.explorer}tx/{self.w3.to_hex(tx_hash)}"
                )
                return True
            else:
                logger.error(
                    f"Transaction failed: {self.chain.explorer}tx/{self.w3.to_hex(tx_hash)}"
                )
                return False
        except Exception as e:
            logger.error(f"Unexpected error in verify_tx function: {e}")
            return False

    @gas_delay(gas_threshold=GAS_THRESHOLD, delay_range=GAS_DELAY_RANGE)
    async def deploy_contract(
        self, abi: Optional[Dict[str, Any]] = None, bytecode: Optional[str] = None
    ) -> bool:
        if bytecode is None:
            bytecode = "0x"
        if abi is None:
            abi = []
        logger.info(f"[Deployer] Deploying contract from {self}")
        tx_params = await self._get_tx_params()
        contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        try:
            transaction = await contract.constructor().build_transaction(
                transaction=tx_params
            )
            signed_tx = self.w3.eth.account.sign_transaction(
                transaction_dict=transaction, private_key=self.private_key
            )
            tx_hash = await self.w3.eth.send_raw_transaction(
                transaction=signed_tx.rawTransaction
            )
            if tx_hash:
                return await self.verify_tx(tx_hash=tx_hash)
            return False
        except Exception as e:
            logger.error(f"[Deployer] Couldn't deploy contract from {self}: {e}")
            return False

    @retry(tries=REQUEST_MAX_RETRIES)
    async def change_ip(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(url=PROXY_CHANGE_IP_URL) as response:
                if response.status == 200:
                    logger.debug(f"Successfully changed ip address")
                    return True
                else:
                    logger.warning(f"Couldn't change ip address")
                    return False
