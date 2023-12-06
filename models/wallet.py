from typing import Optional

from core.client import Client


class Wallet:
    def __init__(
        self,
        account: Client,
        withdrawn_from_okx: Optional[bool] = False,
        bridged_to_scroll: Optional[bool] = False,
        contract_deployed: Optional[bool] = False,
    ) -> None:
        self.private_key: str = account.private_key
        self.address: str = account.address
        self.proxy: str = account.proxy
        self.withdrawn_from_okx: bool = withdrawn_from_okx
        self.bridged_to_scroll: bool = bridged_to_scroll
        self.contract_deployed: bool = contract_deployed

    def _to_dict(self):
        return self.__dict__
