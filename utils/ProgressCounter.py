import asyncio

class ProgressCounter:
    def __init__(self, total):
        self.total = total
        self.current = 0
        self.lock = asyncio.Lock()

    async def increment(self):
        async with self.lock:
            self.current += 1

    def set_total(self, total):
        self.total = total

    def __str__(self):
        return f"{self.current}/{self.total}"
