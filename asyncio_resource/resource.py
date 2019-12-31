import asyncio
import concurrent.futures
import inspect
import warnings
from typing import Awaitable, Callable, Generic, TypeVar

R = TypeVar("R", covariant=True)
T = TypeVar("T")


class Resource(Generic[R]):
    """
    Abstracts over a resource which has an attachment to a specific thread or asyncio event loop.

    When interacting with non-thread-safe resources, code which is actually "concurrent," in the sense of the `concurrent` module, needs to be careful to use those resources on the thread/event loop they expect to be attached to (to avoid race conditions). The `Resource` class helps enforce this.
    """

    def __init__(
        self, resource: R, loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
    ):
        self._resource = resource
        self._loop = loop
        super().__init__()

    def schedule(self, fn: Callable[[R], T]) -> "concurrent.futures.Future[T]":
        """
        Runs a synchronous operation which needs access to the resource, by scheduling it on the attached event loop.

        Returns a future which can be used to wait for the result of the operation.
        """

        async def invoke() -> T:
            result = fn(self._resource)
            if __debug__ and inspect.isawaitable(result):
                warnings.warn(
                    RuntimeWarning(
                        f"Callable given to Resource.schedule returned an awaitable; did you mean schedule_async?"
                    )
                )

            return result

        return asyncio.run_coroutine_threadsafe(invoke(), self._loop)

    def schedule_async(
        self, fn: Callable[[R], Awaitable[T]]
    ) -> "concurrent.futures.Future[T]":
        """
        Runs an async operation which needs access to the resource, by scheduling it on the attached event loop.

        Returns a future which can be used to wait for the result of the operation.
        """

        # This is formally a coroutine to asyncio, so ensures that we run `fn` only on the event loop, as opposed to inline on the calling thread
        async def invoke() -> T:
            return await fn(self._resource)

        return asyncio.run_coroutine_threadsafe(invoke(), self._loop)

    @property
    def resource_unsafe(self) -> R:
        """
        To support incremental migration to the `Resource` class, this property provides direct access to the wrapped resource.

        However, direct access is unsafe, as it can introduce the very kinds of race conditions that this class is meant to prevent. Use of this property should be avoided as much as possible.
        """

        warnings.warn(
            RuntimeWarning(f"Resource {self._resource!r} accessed unsafely"),
            stacklevel=2,
        )

        return self._resource
