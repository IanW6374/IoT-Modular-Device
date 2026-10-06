# Alpha 101: consistent controls and device descriptions

Alpha 101 aligns single-line portal controls to the shared 42 px height without
stretching inputs beside helper text. Text areas and multi-select lists retain
their larger working space.

Management 2.8.14 can edit or clear the device description through the existing
configuration profile API. A description-only change is metadata and does not
require a restart; profiles containing operational settings still do.

The standalone application requires Core API 14. The universal bundle includes
a matched Core API 14 firmware with a private, firmware-first migration inner
application so older compatible cores can stage the pair. Release sequence is
2806. The core API contract is unchanged.

Local automated tests and browser layout checks cover these changes. Confirm
description writes and update completion on hardware before wider deployment.
