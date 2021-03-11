import itertools
import random

from brownie.convert.datatypes import Wei
from brownie.test import strategy
from tests.constants import CASH_GROUP_PARAMETERS, MARKETS, RATE_PRECISION, SECONDS_IN_DAY

timeToMaturityStrategy = strategy("uint", min_value=90, max_value=7200)
impliedRateStrategy = strategy(
    "uint", min_value=0.01 * RATE_PRECISION, max_value=0.40 * RATE_PRECISION
)


def get_cash_group_with_max_markets(maxMarketIndex):
    cg = list(CASH_GROUP_PARAMETERS)
    cg[0] = maxMarketIndex
    cg[7] = cg[7][0:maxMarketIndex]
    cg[8] = cg[8][0:maxMarketIndex]

    return cg


def get_tref(blockTime):
    return blockTime - blockTime % (90 * SECONDS_IN_DAY)


def get_market_state(maturity, **kwargs):
    totalfCash = 1e18 if "totalfCash" not in kwargs else kwargs["totalfCash"]
    totalCurrentCash = 1e18 if "totalCurrentCash" not in kwargs else kwargs["totalCurrentCash"]
    totalLiquidity = 1e18 if "totalLiquidity" not in kwargs else kwargs["totalLiquidity"]
    lastImpliedRate = 0.1e9 if "lastImpliedRate" not in kwargs else kwargs["lastImpliedRate"]
    oracleRate = 0.1e9 if "oracleRate" not in kwargs else kwargs["oracleRate"]
    previousTradeTime = 0 if "previousTradeTime" not in kwargs else kwargs["previousTradeTime"]
    storageState = "0x00"

    return (
        "0x0",  # storage slot
        maturity,
        Wei(totalfCash),
        Wei(totalCurrentCash),
        Wei(totalLiquidity),
        lastImpliedRate,
        oracleRate,
        previousTradeTime,
        storageState,
    )


def get_liquidity_token(marketIndex, **kwargs):
    currencyId = 1 if "currencyId" not in kwargs else kwargs["currencyId"]
    maturity = MARKETS[marketIndex - 1] if "maturity" not in kwargs else kwargs["maturity"]
    assetType = marketIndex + 1
    notional = 1e18 if "notional" not in kwargs else kwargs["notional"]
    storageState = 0 if "storageState" not in kwargs else kwargs["storageState"]

    return (currencyId, maturity, assetType, Wei(notional), storageState)


def get_fcash_token(marketIndex, **kwargs):
    currencyId = 1 if "currencyId" not in kwargs else kwargs["currencyId"]
    maturity = MARKETS[marketIndex - 1] if "maturity" not in kwargs else kwargs["maturity"]
    assetType = 1
    notional = 1e18 if "notional" not in kwargs else kwargs["notional"]
    storageState = 0 if "storageState" not in kwargs else kwargs["storageState"]

    return (currencyId, maturity, assetType, Wei(notional), storageState)


def get_portfolio_array(length, cashGroups, **kwargs):
    portfolio = []
    while len(portfolio) < length:
        isLiquidity = random.randint(0, 1)
        cashGroup = random.choice(cashGroups)
        marketIndex = random.randint(1, cashGroup[1])

        if isLiquidity:
            asset = get_liquidity_token(marketIndex, currencyId=cashGroup[0])
        else:
            asset = get_fcash_token(marketIndex, currencyId=cashGroup[0])

        # Don't allow keys to be repeated
        if (
            len(
                list(
                    filter(
                        lambda x: (x[0], x[1], x[2]) == (asset[0], asset[1], asset[2]), portfolio
                    )
                )
            )
            == 0
        ):
            portfolio.append(asset)

    if kwargs["sorted"]:
        return sorted(portfolio, key=lambda x: (x[0], x[1], x[2]))

    return portfolio


def generate_asset_array(numAssets, numCurrencies):
    assets = []
    nextMaturingAsset = 2 ** 40
    assetsChoice = random.sample(
        list(itertools.product(range(1, numCurrencies), MARKETS)), numAssets
    )

    for a in assetsChoice:
        notional = random.randint(-1e18, 1e18)
        # isfCash = random.randint(0, 1)
        isfCash = 0
        if isfCash:
            assets.append((a[0], a[1], 1, notional))
        else:
            index = MARKETS.index(a[1])
            assets.append((a[0], a[1], index + 2, abs(notional)))
            # Offsetting fCash asset
            assets.append((a[0], a[1], 1, -abs(notional)))

        nextMaturingAsset = min(a[1], nextMaturingAsset)

    random.shuffle(assets)
    return (assets, nextMaturingAsset)


def get_bitstring_from_bitmap(bitmap):
    if bitmap.hex() == "":
        return []

    num_bits = str(len(bitmap) * 8)
    bitstring = ("{:0>" + num_bits + "b}").format(int(bitmap.hex(), 16))

    return bitstring


def random_asset_bitmap(numAssets, maxBit=254):
    # Choose K bits to set
    bitmapList = ["0"] * 256
    setBits = random.choices(range(0, maxBit), k=numAssets)
    for b in setBits:
        bitmapList[b] = "1"
    bitmap = "0x{:0{}x}".format(int("".join(bitmapList), 2), 64)

    return (bitmap, bitmapList)
