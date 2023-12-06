"""
Настройка сетей
"""
SCROLL_RPC_ENDPOINT = ""
MAINNET_RPC_ENDPOINT = ""

"""
Настройка клиента
"""
# задержка после каждого on-chain действия
ACTION_DELAY_RANGE = [60, 60]
# максимальный гвей
GAS_THRESHOLD = 50
# Диапазон для задержки между проверками газа
GAS_DELAY_RANGE = [10, 10]

"""
Настройка прокси
"""
USE_MOBILE_PROXY = False
# если используете мобильные прокси
# сюда вставьте ссылку на смену айпи
PROXY_CHANGE_IP_URL = ""

"""
Настройка OKX
"""
# api credentials
OKX_API_KEY = ""
OKX_API_SECRET = ""
OKX_API_PASSWORD = ""

# диапазон кол-ва эфира на вывод с OKX
OKX_WITHDRAW_AMOUNT_RANGE = [0.002, 0.002]

"""
Настройка Orbiter Finance
"""
# МИНИМАЛЬНОЕ ЧИСЛО ДЛЯ БРИДЖА - 0.001 ETH, КОМИССИЯ ЗА БРИДЖ 0.0012 ETH
# УЧИТЫВАЙТЕ ЭТО ПРИ УСТАНОВКЕ ЗНАЧЕНИЙ
ORBITER_BRIDGE_AMOUNT_RANGE = [0.001, 0.0011]

"""
Настройка деплоера
"""
USE_CUSTOM_CONTRACT = False
# если хотите деплоить кастом контракт, то сюда надо вписать его байткод
# в файл data/custom_abi.json нужно вставить abi кастом контракта
CUSTOM_BYTECODE = "0x"
