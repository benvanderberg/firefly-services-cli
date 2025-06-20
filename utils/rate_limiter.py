import time
from threading import Lock

class RateLimiter:
    def __init__(self, max_calls, period, min_delay=0.0):
        self.max_calls = max_calls
        self.period = period
        self.min_delay = min_delay
        self.calls = []
        self.last_call_time = 0
        self.lock = Lock()

    def acquire(self):
        with self.lock:
            now = time.time()
            
            # Enforce minimum delay between calls
            if self.min_delay > 0 and self.last_call_time > 0:
                time_since_last = now - self.last_call_time
                if time_since_last < self.min_delay:
                    sleep_time = self.min_delay - time_since_last
                    time.sleep(sleep_time)
                    now = time.time()
            
            # Remove calls outside the period
            self.calls = [t for t in self.calls if now - t < self.period]
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                now = time.time()
                self.calls = [t for t in self.calls if now - t < self.period]
            
            self.calls.append(now)
            self.last_call_time = now 