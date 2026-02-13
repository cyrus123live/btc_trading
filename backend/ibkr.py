import asyncio
import logging
from datetime import datetime
from typing import Optional

from ib_insync import IB, Contract, MarketOrder, util
from models import Candle, Position, AccountSummary

logger = logging.getLogger(__name__)


class IBKRClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 4002, client_id: int = 1):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()
        self._contract: Optional[Contract] = None

    @property
    def connected(self) -> bool:
        return self.ib.isConnected()

    async def connect(self):
        if self.connected:
            return
        try:
            await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
            logger.info(f"Connected to IBKR at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            raise

    async def disconnect(self):
        if self.connected:
            self.ib.disconnect()
            logger.info("Disconnected from IBKR")

    async def ensure_connected(self):
        if not self.connected:
            await self.connect()

    def get_contract(self) -> Contract:
        if self._contract is None:
            contract = Contract()
            contract.symbol = "MBT"
            contract.secType = "FUT"
            contract.exchange = "CME"
            contract.currency = "USD"
            # Use the front-month contract
            contract.lastTradeDateOrContractMonth = ""
            self._contract = contract
        return self._contract

    async def qualify_contract(self) -> Contract:
        """Qualify the contract to get the front-month expiry."""
        await self.ensure_connected()
        contract = self.get_contract()
        if not contract.lastTradeDateOrContractMonth:
            contracts = await self.ib.qualifyContractsAsync(contract)
            if contracts:
                self._contract = contracts[0]
                logger.info(f"Qualified contract: {self._contract}")
            else:
                # Fallback: request contract details and pick the nearest expiry
                contract_for_details = Contract()
                contract_for_details.symbol = "MBT"
                contract_for_details.secType = "FUT"
                contract_for_details.exchange = "CME"
                contract_for_details.currency = "USD"
                details = await self.ib.reqContractDetailsAsync(contract_for_details)
                if details:
                    # Sort by expiry and pick the nearest
                    details.sort(key=lambda d: d.contract.lastTradeDateOrContractMonth)
                    self._contract = details[0].contract
                    await self.ib.qualifyContractsAsync(self._contract)
                    logger.info(f"Qualified contract via details: {self._contract}")
                else:
                    raise RuntimeError("Could not find MBT futures contract")
        return self._contract

    async def get_historical_candles(
        self, duration: str = "1 D", bar_size: str = "1 min"
    ) -> list[Candle]:
        await self.ensure_connected()
        contract = await self.qualify_contract()
        bars = await self.ib.reqHistoricalDataAsync(
            contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=False,
            formatDate=2,  # UTC timestamps
        )
        candles = []
        for bar in bars:
            ts = int(bar.date.timestamp()) if isinstance(bar.date, datetime) else int(bar.date)
            candles.append(
                Candle(
                    time=ts,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                )
            )
        return candles

    async def subscribe_realtime_bars(self, callback):
        """Subscribe to 5-second realtime bars and call callback with each bar."""
        await self.ensure_connected()
        contract = await self.qualify_contract()
        bars = self.ib.reqRealTimeBars(
            contract, barSize=5, whatToShow="TRADES", useRTH=False
        )
        bars.updateEvent += callback
        return bars

    async def place_order(self, side: str, quantity: int = 1) -> dict:
        await self.ensure_connected()
        contract = await self.qualify_contract()
        action = "BUY" if side.upper() == "BUY" else "SELL"
        order = MarketOrder(action, quantity)
        trade = self.ib.placeOrder(contract, order)

        # Wait briefly for fill
        for _ in range(50):
            await asyncio.sleep(0.1)
            if trade.isDone():
                break

        return {
            "order_id": trade.order.orderId,
            "side": action,
            "quantity": quantity,
            "status": trade.orderStatus.status,
            "avg_fill_price": trade.orderStatus.avgFillPrice or None,
        }

    async def get_positions(self) -> list[Position]:
        await self.ensure_connected()
        positions = self.ib.positions()
        result = []
        for pos in positions:
            if pos.contract.symbol == "MBT":
                result.append(
                    Position(
                        symbol="MBT",
                        size=pos.position,
                        avg_cost=pos.avgCost,
                        unrealized_pnl=pos.unrealizedPNL if hasattr(pos, "unrealizedPNL") else 0,
                        market_value=pos.marketValue if hasattr(pos, "marketValue") else 0,
                    )
                )
        # If no MBT positions, also check portfolio items for P/L
        if not result:
            portfolio = self.ib.portfolio()
            for item in portfolio:
                if item.contract.symbol == "MBT":
                    result.append(
                        Position(
                            symbol="MBT",
                            size=item.position,
                            avg_cost=item.averageCost,
                            unrealized_pnl=item.unrealizedPNL,
                            market_value=item.marketValue,
                        )
                    )
        return result

    async def get_account_summary(self) -> AccountSummary:
        await self.ensure_connected()
        summary = self.ib.accountSummary()
        values = {item.tag: float(item.value) for item in summary if item.value.replace(".", "").replace("-", "").isdigit()}
        return AccountSummary(
            net_liquidation=values.get("NetLiquidation", 0),
            available_funds=values.get("AvailableFunds", 0),
            buying_power=values.get("BuyingPower", 0),
            margin_used=values.get("MaintMarginReq", 0),
        )
