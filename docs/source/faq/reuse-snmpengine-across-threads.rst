
Reusing SnmpEngine across threads
----------------------------------

Q. Creating a new ``SnmpEngine`` for every request is slow.  Can I create one
   instance and share it across multiple threads, each calling
   ``asyncio.run()``?

A. No.  ``SnmpEngine`` is **bound to the event loop** that first issues a
   network request through it.  Specifically, the first call to
   :func:`~pysnmp.hlapi.v3arch.asyncio.get_cmd` (or any other command) lazily
   creates an ``AsyncioDispatcher`` that captures
   ``asyncio.get_event_loop()`` at that moment.  When ``asyncio.run()``
   returns it **closes and destroys** that event loop.  Any subsequent call
   from another thread starts a new event loop, but the engine's dispatcher
   still holds a reference to the old, closed one — the request never
   completes and the thread hangs indefinitely.

   There are three correct patterns depending on your use case.

**Pattern 1 — One engine per thread (simplest)**

   Each thread creates its own ``SnmpEngine`` for the lifetime of its
   ``asyncio.run()`` call.  Using the context manager ensures the dispatcher
   is detached before the event loop is destroyed:

   .. code-block:: python

      import asyncio, threading
      from pysnmp.hlapi.v3arch.asyncio import *

      def worker(host):
          async def _run():
              with SnmpEngine() as engine:
                  ei, es, _, vbs = await get_cmd(
                      engine,
                      CommunityData("public"),
                      await UdpTransportTarget.create((host, 161)),
                      ContextData(),
                      ObjectType(ObjectIdentity("SNMPv2-MIB", "sysDescr", 0)),
                  )
                  return vbs
          return asyncio.run(_run())

      threads = [threading.Thread(target=worker, args=(h,)) for h in hosts]
      for t in threads: t.start()
      for t in threads: t.join()

**Pattern 2 — One engine, one event loop, many concurrent hosts (recommended)**

   A single ``SnmpEngine`` with ``asyncio.gather()`` handles hundreds of
   hosts concurrently without any threading.  This is the intended high-
   throughput pattern:

   .. code-block:: python

      import asyncio
      from pysnmp.hlapi.v3arch.asyncio import *

      async def poll(engine, host):
          ei, es, _, vbs = await get_cmd(
              engine,
              CommunityData("public"),
              await UdpTransportTarget.create((host, 161), timeout=2, retries=1),
              ContextData(),
              ObjectType(ObjectIdentity("SNMPv2-MIB", "sysDescr", 0)),
          )
          return host, ei, vbs

      async def main():
          hosts = ["192.168.1.{}".format(i) for i in range(1, 251)]
          with SnmpEngine() as engine:
              results = await asyncio.gather(*[poll(engine, h) for h in hosts])
          for host, ei, vbs in results:
              print(host, ei or vbs)

      asyncio.run(main())

**Pattern 3 — Thread pool with per-thread engine reuse**

   If you must use threads (for example when integrating with a synchronous
   framework), keep one engine per thread with ``threading.local()`` and call
   ``close_dispatcher()`` after each ``asyncio.run()`` to detach the stale
   loop reference before the next call:

   .. code-block:: python

      import asyncio, threading
      from pysnmp.hlapi.v3arch.asyncio import *

      _local = threading.local()

      def get_engine():
          if not hasattr(_local, "engine"):
              _local.engine = SnmpEngine()
          return _local.engine

      def worker(host):
          async def _run():
              ei, es, _, vbs = await get_cmd(
                  get_engine(),
                  CommunityData("public"),
                  await UdpTransportTarget.create((host, 161)),
                  ContextData(),
                  ObjectType(ObjectIdentity("SNMPv2-MIB", "sysDescr", 0)),
              )
              return vbs
          try:
              return asyncio.run(_run())
          finally:
              # Reset the dispatcher so the next asyncio.run() in this
              # thread starts with a clean event-loop binding.
              get_engine().close_dispatcher()
