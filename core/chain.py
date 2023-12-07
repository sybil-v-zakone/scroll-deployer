from dataclasses import dataclass

from config import MAINNET_RPC_ENDPOINT, SCROLL_RPC_ENDPOINT
from constants import ARB_NETWORK_FEE, ARB_OKX_CHAIN_NAME


@dataclass
class Chain:
    name: str
    chain_id: int
    coin_symbol: str
    rpc: str
    explorer: str | None = None
    okx_chain_name: str | None = None
    okx_withdrawal_fee: str | None = None
    orbiter_id: str | None = None


SCROLL = Chain(
    name="SCROLL",
    chain_id=534352,
    coin_symbol="ETH",
    explorer="https://scrollscan.com/",
    rpc=SCROLL_RPC_ENDPOINT,
    orbiter_id="9019",
)

ARBITRUM = Chain(
    name="ARBITRUM",
    chain_id=42161,
    coin_symbol="ETH",
    explorer="https://arbiscan.io/",
    rpc="https://rpc.ankr.com/arbitrum",
    okx_chain_name=ARB_OKX_CHAIN_NAME,
    okx_withdrawal_fee=ARB_NETWORK_FEE,
)

MAINNET = Chain(
    name="Ethereum Mainnet", chain_id=1, coin_symbol="ETH", rpc=MAINNET_RPC_ENDPOINT
)
