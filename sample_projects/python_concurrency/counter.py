import threading
import time


class Counter:
    def __init__(self) -> None:
        self.value = 0
        self._lock = threading.Lock()

    def increment(self) -> None:
        with self._lock:
            current = self.value
            time.sleep(0.0001)
            self.value = current + 1


def worker(counter: Counter, iterations: int) -> None:
    for _ in range(iterations):
        counter.increment()


def run_workers(num_threads: int = 20, iterations: int = 100) -> int:
    counter = Counter()
    threads = [threading.Thread(target=worker, args=(counter, iterations)) for _ in range(num_threads)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return counter.value
