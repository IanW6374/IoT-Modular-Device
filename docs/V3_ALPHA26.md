# IoT-MD v3.0.0-alpha.26

Alpha 26 is a paired repair and portal-consistency release. It retains native
platform ABI 6 and uses release sequence 2731.

## Constrained paired activation

Alpha 24 automatic staging successfully verified both components, but its
application activation then required 1,228,079 bytes while only 1,171,456 bytes
were free. The core trial had already been selected, so the application could
not enter its matching trial slot and paired confirmation correctly rolled the
transaction back.

Alpha 26 checks application-slot capacity before selecting the new core. When
the only shortage is the verified application bundle occupying flash, frozen
recovery reads that signed bundle into PSRAM, records the activating state,
releases the staging file and extracts into the inactive application slot. The
active application slot remains untouched, and interrupted activation follows
the existing paired rollback path.

## Upgrade portal

- Release-channel and local-file updates now share one **Choose upgrade
  source** panel.
- Either source returns to the same **Staged upgrade** panel and activation
  action.
- Automatic scheduling and channel preferences are available in a collapsed
  secondary section.
- Release checks display progress only while running and finish with the useful
  result rather than a redundant completion percentage.
- A staged release no longer appears simultaneously as a separate available
  release.

Install `universal-3.0.0-alpha.26.iotuni`; an application-only update cannot
install the frozen constrained-capacity activator.
