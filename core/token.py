from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Token:
    symbol: str
    decimals: int
    is_stable: bool
    is_native: bool
    api_id: str
    contract_address: Optional[str] = None
    abi: Optional[Dict] = None

    def to_wei(self, value: int) -> int:
        return int(value * pow(10, self.decimals))

    def from_wei(self, value: int) -> float:
        return value / pow(10, self.decimals)


ETH = Token(
    symbol="ETH",
    decimals=18,
    is_stable=False,
    is_native=True,
    api_id="80",
)
