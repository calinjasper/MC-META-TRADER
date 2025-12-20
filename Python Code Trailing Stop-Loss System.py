class TrailingStopLoss:
    def __init__(self, entry_price, sl_gap):
        self.entry_price = entry_price
        self.sl_gap = sl_gap
        self.stop_loss = entry_price - sl_gap   # initial SL
        self.highest_price = entry_price        # track highest price

    def update_price(self, current_price):
        # Update highest seen price
        if current_price > self.highest_price:
            self.highest_price = current_price

            # Calculate new SL
            new_sl = self.highest_price - self.sl_gap

            # Trailing SL only moves upward
            if new_sl > self.stop_loss:
                self.stop_loss = new_sl

        return self.stop_loss


# -------------------------------
# Example Usage
# -------------------------------

tsl = TrailingStopLoss(entry_price=150, sl_gap=10)

prices = [150, 160, 170]   # incoming market prices

for p in prices:
    sl = tsl.update_price(p)
    print(f"Price: {p} → Trailing SL: {sl}")
