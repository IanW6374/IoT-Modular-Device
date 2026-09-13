# IoT-MD v3.0.0-alpha.24

Alpha 24 is a paired repair release for the qualification recorder storage
handle leak observed after installing Alpha 23. It retains native platform ABI
6 and uses release sequence 2729.

## Finding

The native storage boundary has a deliberate four-handle limit. Qualification
owns three encrypted transactional namespaces: current release evidence,
bounded release history and cross-release campaign evidence. A failed recorder
startup discarded its Python objects without closing namespaces. A product
application restart could also lose those objects while the native static
handle table remained alive. Subsequent initialization eventually reported
`storage handle limit reached`, obscuring the original startup condition.

## Repair

- Native `storage_open(namespace)` now returns the existing bounded handle when
  the same namespace is reopened after an application restart.
- Recorder construction is transactional: every namespace opened before an
  initialization failure is closed before a retry.
- The operational recorder owns an explicit `close()` lifecycle, and orderly
  product shutdown invokes it after the event loop stops.
- Stored qualification evidence is not cleared or reset by handle cleanup.

Because native reuse is implemented in the core while lifecycle ownership is
implemented in the application, Alpha 24 must be installed as the universal
paired release.
