# Portfolio interaction review

This review covers IoT-MD, Management, Certificate Authority and Syslog. It does
not change device configuration, firmware security or live deployments.

## Common rules

- Use the existing Home Assistant-aligned 14px body/field text and 42px single-line
  controls. Keep labels above fields; help text sits below, at 12px and normal weight.
- Put native checkboxes before their text. Required markers follow the label, not
  the input. Only genuinely required, editable controls receive the marker.
- Keep boolean preferences as checkboxes and single-choice filters as ordinary
  selects. Use grouped selection for multi-item choices, not every dropdown.
- Use visible status messages for success/progress and alert announcements for
  errors. Preserve previously loaded data during a failed refresh. Clear recovered
  refresh errors without removing unrelated validation errors.
- Retain selections, open disclosures and searches during polling. Keyboard users
  can open selection menus, expand groups and close with Escape.
- Completed milestones use green ticks; pending installation remains an unfinished
  circle even after staging succeeds. Primary actions live outside the progress rail.

## Changes from the review

| Area | Finding and correction |
| --- | --- |
| All four portals | Required-field annotation moved bare label text ahead of checkboxes. Keep the checkbox first, including after dynamically rendered content. |
| Add-on forms | Share label, help text, focus and control styling; avoid changing radio-card workflow layouts. |
| IoT-MD API | Authentication was a differently sized information box beside Port. Present it as an aligned, read-only field with explanatory text. Authentication remains mandatory mTLS. |
| Management actions | Deploy/backup device and group choices now use the profile selector's visual pattern: search, select all, mixed-state group controls, individual choices and removable group chips. Keep the actual named form inputs and change events. |
| Management refresh | Preserve dropdown state and keyboard focus across render cycles; snapshot native details state before redraw rather than waiting for its asynchronous toggle event. |
| Management errors | Profile initialization and backup refresh failures are displayed, not only written to the developer console. A successful backup refresh clears its own failure notice. |
| Syslog refresh | Receiver status HTTP/network failures are surfaced while old data is retained. A successful refresh clears that failure notice. |
| IoT-MD updates | Start update remains visible while staging. Restart/install uses the primary action location; the last milestone is a ring, not a button. Transient task connection failures remain visible without resetting progress. |
| IoT-MD navigation | Device / Update settings; Maintenance / Update; Maintenance / Logging / Update activity. Keep existing update URLs compatible. |
| IoT-MD activity | Search release checks and update events, filter outcomes and show coloured dots with accessible status tooltips. Remove history from the installation workspace. |

## Selection and data safety

The target picker uses the existing `target_device`, `target_cohort`,
`backup_target_device` and `backup_target_cohort` inputs. Group/select-all controls
are unnamed and cannot enter the request payload. Disabled choices cannot be
selected in bulk. Searching never clears hidden selections. Profile secret
selection and masked-value preservation are unchanged.

Certificate Authority currently has boolean approval/preferences rather than
large multi-select lists. Syslog filters currently accept one value each. Keeping
these simple avoids changing their API contracts solely for visual uniformity.

## Verification

Run each repository's Python suite and architecture/accessibility/MicroPython
checks. Management also has real DOM regression tests:

```sh
npm install
npm test
```

IoT-MD's offline DOM contracts live in `tests/browser`:

```sh
cd tests/browser
npm install
npm run test:contracts
```

These tests do not visit live devices. Existing Playwright device qualification
tests are separate and must not be run against a device without authorization.

`tools/check_portfolio_layout.py` creates isolated desktop/mobile fixtures and
checks rendered geometry using local headless Chromium. It requires the three
HA repositories beside IoT-MD. In this environment Chromium timed out even on an
empty headless page: DOM/functional checks passed, but rendered geometry and
screenshots still need visual verification on a working browser runner.

## Further review

Before release, check the real HA ingress pages and the device first-run wizard
at desktop and mobile widths, especially long labels, translated text and expanded
profile/certificate sections. These screens are not all represented by the offline
geometry fixtures; do not treat a shared stylesheet as proof of every page's layout.
