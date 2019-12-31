import asyncio
import concurrent.futures
import unittest
from typing import Awaitable, List, Tuple, Union

from asyncio_resource import Resource


class TestResource(unittest.TestCase):
    def setUp(self) -> None:
        self.loop = asyncio.get_event_loop()
        self.resource = Resource(0, self.loop)

    def test_scheduling_function(self) -> None:
        def fn(value: int) -> str:
            self.assertEqual(asyncio.get_running_loop(), self.loop)
            return str(value)

        def concurrent_fn() -> int:
            result = self.resource.schedule(fn).result()
            self.assertEqual(result, "0")

            self.loop.call_soon_threadsafe(lambda: self.loop.stop())
            return int(result)

        future = concurrent.futures.ThreadPoolExecutor().submit(concurrent_fn)
        self.loop.run_forever()
        self.assertEqual(future.result(), 0)

    def test_scheduling_coroutine(self) -> None:
        async def coro(value: int) -> str:
            self.assertEqual(asyncio.get_running_loop(), self.loop)
            return str(value)

        def concurrent_fn() -> int:
            result = self.resource.schedule_async(coro).result()
            self.assertEqual(result, "0")

            self.loop.call_soon_threadsafe(lambda: self.loop.stop())
            return int(result)

        future = concurrent.futures.ThreadPoolExecutor().submit(concurrent_fn)
        self.loop.run_forever()
        self.assertEqual(future.result(), 0)

    def test_scheduling_awaitable(self) -> None:
        async def coro(value: int) -> str:
            self.assertEqual(asyncio.get_running_loop(), self.loop)
            return str(value)

        def concurrent_fn() -> int:
            # Scheduling a lambda which returns an Awaitable, instead of the coroutine itself.
            result = self.resource.schedule_async(lambda val: coro(val)).result()
            self.assertEqual(result, "0")

            self.loop.call_soon_threadsafe(lambda: self.loop.stop())
            return int(result)

        future = concurrent.futures.ThreadPoolExecutor().submit(concurrent_fn)
        self.loop.run_forever()
        self.assertEqual(future.result(), 0)

    def test_using_resource_too_early(self) -> None:
        async def coro(s: str) -> List[str]:
            self.assertEqual(asyncio.get_running_loop(), self.loop)
            return [s]

        # Ensures that accessing the resource even before dispatch should be "safe."
        def too_early(value: int) -> Awaitable[List[str]]:
            self.assertEqual(asyncio.get_running_loop(), self.loop)
            return coro(str(value))

        def concurrent_fn() -> int:
            results = self.resource.schedule_async(too_early).result()
            self.assertEqual(results, ["0"])

            self.loop.call_soon_threadsafe(lambda: self.loop.stop())
            return len(results)

        future = concurrent.futures.ThreadPoolExecutor().submit(concurrent_fn)
        self.loop.run_forever()
        self.assertEqual(future.result(), 1)
