from typing import Optional, Tuple
from ..schemas.models import Tick


class LeeReadyTickClassifier:
    """
    Trade-side classification using Exchange Aggressor Flags with documented fallback
    to the Lee-Ready algorithm / tick rule.
    """

    def __init__(self):
        self.last_price: Optional[float] = None
        self.last_side: Optional[str] = "BUY"  # Default initial side if tie on start

    def classify_trade(
        self,
        price: float,
        is_buyer_maker: Optional[bool] = None,
        best_bid: Optional[float] = None,
        best_ask: Optional[float] = None,
    ) -> Tuple[str, str]:
        """
        Classifies trade as 'BUY' or 'SELL'.
        Returns (side, classification_method).
        """
        # 1. Exchange Aggressor Flag (Binance: is_buyer_maker=True -> Sell Taker, is_buyer_maker=False -> Buy Taker)
        if is_buyer_maker is not None:
            side = "SELL" if is_buyer_maker else "BUY"
            self.last_price = price
            self.last_side = side
            return side, "EXCHANGE_FLAG"

        # 2. Quote Rule (if bid/ask provided)
        if best_bid is not None and best_ask is not None and best_bid < best_ask:
            mid_price = (best_bid + best_ask) / 2.0
            if price > mid_price:
                self.last_price = price
                self.last_side = "BUY"
                return "BUY", "LEE_READY_TICK_RULE"
            elif price < mid_price:
                self.last_price = price
                self.last_side = "SELL"
                return "SELL", "LEE_READY_TICK_RULE"

        # 3. Tick Rule (Lee-Ready)
        if self.last_price is None:
            side = "BUY"
        elif price > self.last_price:
            side = "BUY"
        elif price < self.last_price:
            side = "SELL"
        else:
            # Zero tick: repeat previous direction
            side = self.last_side or "BUY"

        self.last_price = price
        self.last_side = side
        return side, "LEE_READY_TICK_RULE"
