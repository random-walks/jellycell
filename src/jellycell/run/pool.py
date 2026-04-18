"""Kernel reuse across multiple :class:`Runner.run` calls.

Each ``jellycell run`` spawns a fresh Jupyter kernel subprocess (~2s setup,
~1s shutdown). Over ``render_all`` on a project with N notebooks that's N
kernel churns for no reason — the kernel protocol has a ``%reset -f`` magic
for exactly this case.

Usage::

    pool = KernelPool(kernel_name="python3")
    runner = Runner(project, kernel_pool=pool)
    try:
        for nb in notebooks:
            runner.run(nb)
    finally:
        pool.close()

The pool holds exactly one long-lived kernel (``maxsize=1``) for now — most
projects are single-kernel. A multi-kernel pool is straightforward to add
if someone needs parallel execution later.
"""

from __future__ import annotations

from types import TracebackType

from jellycell.run.kernel import Kernel


class KernelPool:
    """Holds one long-lived kernel, resetting its namespace between runs.

    ``acquire()`` returns a kernel. If the pool's kernel died between calls
    (subprocess crashed), a new one is spawned transparently.
    """

    def __init__(self, kernel_name: str = "python3") -> None:
        self.kernel_name = kernel_name
        self._kernel: Kernel | None = None

    def acquire(self) -> Kernel:
        """Return a ready-to-use kernel. Starts or resets as needed."""
        if self._kernel is None or not self._is_alive(self._kernel):
            self._kernel = Kernel(kernel_name=self.kernel_name)
            self._kernel.start()
        else:
            self._reset_namespace(self._kernel)
        return self._kernel

    def _is_alive(self, kernel: Kernel) -> bool:
        mgr = getattr(kernel, "_mgr", None)
        return bool(mgr and mgr.is_alive())

    def _reset_namespace(self, kernel: Kernel) -> None:
        """Clear the kernel's user namespace without killing the subprocess.

        Uses IPython's ``%reset -f`` magic so names defined in the previous
        run don't leak into the next. If the reset fails (kernel got wedged),
        bounce the kernel.
        """
        try:
            result = kernel.execute("get_ipython().run_line_magic('reset', '-f')\n", timeout=5.0)
        except Exception:
            result = None
        if result is None or result.status != "ok":
            # Reset failed — respawn.
            kernel.stop()
            new = Kernel(kernel_name=self.kernel_name)
            new.start()
            self._kernel = new

    def close(self) -> None:
        """Stop the underlying kernel. Idempotent."""
        if self._kernel is not None:
            self._kernel.stop()
            self._kernel = None

    def __enter__(self) -> KernelPool:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
