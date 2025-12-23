class ProfitManager:
    def __init__(self,
                 lock_trigger,      # If Profit Reaches
                 lock_value,        # Lock Minimum Profit At
                 trail_step,        # For Every Increase in Profit By
                 trail_amount):     # Trail Profit By

        self.lock_trigger = lock_trigger
        self.lock_value = lock_value
        self.trail_step = trail_step
        self.trail_amount = trail_amount

        self.lock_enabled = False
        self.current_locked_profit = 0
        self.last_trail_base = lock_trigger  # will trail only after reaching trigger

    def update_profit(self, profit):
        """
        Call this function on every profit change.
        Returns updated locked profit.
        """

        # 1️⃣ ENABLE LOCKING WHEN PROFIT REACHES TRIGGER
        if profit >= self.lock_trigger and not self.lock_enabled:
            self.lock_enabled = True
            self.current_locked_profit = self.lock_value

        # 2️⃣ APPLY TRAILING ONLY AFTER LOCK TRIGGER IS HIT
        if self.lock_enabled and self.trail_step > 0:

            # Check if profit increased enough to trail more
            while profit >= self.last_trail_base + self.trail_step:
                self.last_trail_base += self.trail_step
                self.current_locked_profit += self.trail_amount

        return self.current_locked_profit


# ------------------ EXAMPLE USAGE ------------------ #

pm = ProfitManager(
    lock_trigger=1000,     # If Profit Reaches 1000
    lock_value=500,        # Lock Minimum Profit at 500
    trail_step=1000,       # For Every Increase in Profit By 1000
    trail_amount=500       # Trail Profit By 500
)

profits = [200, 800, 1000, 1500, 2100, 3000]

for p in profits:
    locked = pm.update_profit(p)
    print(f"Profit: {p} → Locked Profit: {locked}")
