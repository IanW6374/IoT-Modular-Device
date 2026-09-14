# IoT-MD v3.0.0-alpha.28

Alpha 28 repairs constrained sequential universal uploads. It retains native
platform ABI 6 and uses release sequence 2733.

## Cause of the Alpha 27 storage rejection

The portal correctly inspected a universal container in the browser and sent
its core and application bundles one at a time. The upload store nevertheless
evaluated the inner core as an ordinary `firmware` upload. Its storage
reclaimer is deliberately restricted to `universal` updates, so it did not
release the inactive application generation and rejected the 1.51 MB core when
only about 1.30 MB was free.

Alpha 28 carries an internal universal reclaim classification alongside the
real component type. The signed outer plan must authorize the exact component
size and digest before that classification is used. The component remains a
firmware or application upload for verification and installation; standalone
component uploads cannot request universal reclamation.

## Bridge installation from Alpha 26 or Alpha 27

A device running the earlier uploader cannot obtain this correction from a
large universal file directly. Install and activate
`application-3.0.0-alpha.28.iotapp` first. Then upload
`universal-3.0.0-alpha.28.iotuni`. The universal planner skips the application
already at sequence 2733 and reclaims its inactive predecessor if the core
needs the space.

Do not replace or republish the signed Alpha 27 artifacts; Alpha 28 is a new
monotonic release with its own provenance.
