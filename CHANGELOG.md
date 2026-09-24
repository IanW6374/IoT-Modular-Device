# Changelog

## Unreleased

## 3.0.0-alpha.62 - 2026-09-24

- Add a signed dummy release for exercising the Alpha 61 upgrade and
  configuration-profile workflow. No intentional functional changes; retain
  native ABI 6 and use release sequence 2767.

## 3.0.0-alpha.61 - 2026-09-24

- Add a dedicated `configuration:write` Device API scope and validated profile
  endpoint for applying reusable, non-secret operational settings from the
  Management Suite. Reject passwords, trust material, identity and network
  addressing; audit successful application and require a restart. Retain
  native ABI 6; sequence 2766.

## 3.0.0-alpha.60 - 2026-09-24

- Normalize the ESP32 MicroPython 2000-based runtime clock to Unix time before
  evaluating signed fleet policy validity and recording fleet result times.
  This aligns Device API policy enforcement with Management Suite timestamps.
- Execute managed deployment checks against the policy's selected channel and
  exact release sequence, and leave activation pending until the signed local
  maintenance window opens. Retain native ABI 6; sequence 2765.

## 3.0.0-alpha.59 - 2026-09-24

- Replace the unavailable MicroPython `PermissionError` built-in with a
  portable API authorization exception. Previously, evaluating the first
  `except PermissionError` clause raised `NameError` while handling any policy
  validation failure, masking the real error and closing TLS without an HTTP
  response. Retain native ABI 6; sequence 2764.

## 3.0.0-alpha.58 - 2026-09-23

- Receive the complete bounded Device API request body before inspecting the
  authenticated peer certificate. MicroPython's TLS stream can stop yielding
  application data when `getpeercert()` is called between header and body
  reads, producing an EOF before request dispatch. Retain native ABI 6;
  sequence 2763.

## 3.0.0-alpha.57 - 2026-09-23

- Restore direct, bounded Device API reads from the TLS stream instead of
  applying the portal's read-ahead buffer. Some MicroPython TLS streams wait
  for the requested buffer size, so a 512-byte header read could stall before
  any POST body handling or request logging occurred. Retain native ABI 6;
  sequence 2762.

## 3.0.0-alpha.56 - 2026-09-23

- Read Device API request bodies using their exact remaining Content-Length
  instead of inflating small TLS reads to the header buffer size. Device
  testing subsequently showed that the header read-ahead itself could still
  stall before dispatch; Alpha 57 completes the correction. Retain native ABI
  6; sequence 2761.

## 3.0.0-alpha.55 - 2026-09-23

- Add a signed application-only dummy release for exercising the Alpha 54
  discard-during-verification and subsequent retry workflow. No intentional
  functional changes; sequence 2760.

## 3.0.0-alpha.54 - 2026-09-23

- Make **Discard** clear resumable-upload, sequential-universal, staged
  component and automatic-release orchestration state as one operation.
- Honour a discard requested during background verification at its next
  progress checkpoint, preventing the abandoned task from interfering with a
  subsequent upgrade. Retain native ABI 6; sequence 2759.

## 3.0.0-alpha.53 - 2026-09-23

- Allow an administrator to edit an enrolled mTLS API client's scopes in place
  from Device API or API Client Trust, without re-enrolling its certificate.
- Present the supported permissions in a compact multi-select scope editor,
  validate that at least one known scope remains, and audit successful changes.
  Retain native ABI 6; sequence 2758.

## 3.0.0-alpha.52 - 2026-09-23

- Add a signed dummy release for exercising the Alpha 51 disabled-to-active
  **Restart and install** transition. No intentional functional changes.
- Provide matching production-secure application, core and universal artifacts
  for the final Alpha 52 hardware-qualification candidate. Retain native ABI 6;
  sequence 2757.

## 3.0.0-alpha.51 - 2026-09-23

- Replace the inactive circular **Manual** marker at the final Upgrade step
  with the same disabled **Restart and install** control that becomes active
  after staging completes.
- Apply the final-action presentation consistently to static, manual,
  automatic, application, core and universal workflows. Retain native ABI 6;
  sequence 2756.

## 3.0.0-alpha.50 - 2026-09-23

- Add a signed application-only dummy release for exercising the Alpha 49
  Upgrade action placement. No intentional functional changes; sequence 2755.

## 3.0.0-alpha.49 - 2026-09-23

- Move **Discard** out of release selection and into the bottom-right
  workflow-action area for in-progress manual and staged upgrades.
- Remove the redundant **Verified** badge from staged application, core and
  universal workflows; completed progress steps remain the verification
  indicator. Retain native ABI 6; sequence 2754.

## 3.0.0-alpha.48 - 2026-09-22

- Add a signed application-only dummy release for exercising the Alpha 47
  cross-method Upgrade format. No intentional functional changes; sequence
  2753.

## 3.0.0-alpha.47 - 2026-09-22

- Apply the chart-attached Upgrade format consistently across Automatic,
  Manual, Staged and Rollback methods.
- Keep automatic release selection, channel checking and the selected release
  within **Select version**, and remove duplicate normal-operation task text.
- Present the retained rollback application beneath **Previous application
  retained**, reserving below-chart status space for failures only. Retain
  native ABI 6; sequence 2752.

## 3.0.0-alpha.46 - 2026-09-22

- Add a signed application-only dummy release for exercising the repaired
  Alpha 45 manual staging workflow. No intentional functional changes;
  sequence 2751.

## 3.0.0-alpha.45 - 2026-09-22

- Keep the complete manual-upload form attached when file selection rebuilds
  the progress workflow, restoring the **Stage upgrade** submit action.
- Enforce hidden state for selected-file guidance and controls so recovery-file
  guidance disappears after selection and completed actions stay hidden.
  Retain native ABI 6; sequence 2750.

## 3.0.0-alpha.44 - 2026-09-22

- Add a signed application-only dummy release for exercising the Alpha 43 to
  Alpha 44 continuous staged workflow. No intentional functional changes;
  sequence 2749.

## 3.0.0-alpha.43 - 2026-09-22

- Make selected manual files and automatic versions visually prominent beneath
  their workflow steps, and use the destructive colour for **Discard**.
- Replace the post-verification page navigation with an in-place staged-state
  update for manual and automatic upgrades.
- Keep reopened staged upgrades in the same chart-based layout, with the
  selected release, Discard, Verified and restart actions attached to their
  respective steps. Retain native ABI 6; sequence 2748.

## 3.0.0-alpha.42 - 2026-09-22

- Add a signed application-only dummy release for exercising the Alpha 41 to
  Alpha 42 staged upgrade, restart, confirmation and rollback path. No
  intentional functional changes; sequence 2747.

## 3.0.0-alpha.41 - 2026-09-22

- Consolidate Upgrade progress and actions into one workflow: remove the
  duplicate current-task row and divider, center file/version selection under
  its step, and place the Verified badge beneath **Verify and stage**.
- Replace the disabled **Working…** action with the live progress step and rename
  **Cancel** to **Discard**. Discard now aborts and removes resumable upload
  state without refreshing the page.
- Keep staging explicitly separate from activation so an operator can leave the
  page and restart later. Retain native ABI 6; sequence 2746.

## 3.0.0-alpha.40 - 2026-09-22

- Add a signed application-only test release for exercising the Alpha 39 to
  Alpha 40 upgrade workflow. No functional behavior changes; sequence 2745.

## 3.0.0-alpha.39 - 2026-09-22

- Size Upgrade method choices against the four-method desktop layout even when
  only Automatic and Manual are currently available, with two- and one-column
  responsive layouts.
- Replace the final restart percentage with a manual action and integrate the
  signed install or rollback button directly into the final progress step.
- Standardise final actions as **Restart and install** or **Restart and
  rollback**, without type or version suffixes. Retain ABI 6; sequence 2744.

## 3.0.0-alpha.38 - 2026-09-22

- Create qualification controls only after the runtime logger is defined,
  preventing the Alpha 37 application-startup rollback.
- Keep Upgrade method choices a consistent desktop width and suppress link
  underlining for their hover and keyboard-focus states.
- Use the concise **Restart and install** action for staged application, core
  and universal upgrades. Retain native ABI 6 and use release sequence 2743.

## 3.0.0-alpha.37 - 2026-09-21

- Add administrator portal and dedicated-scope mTLS API workflows for recording
  observed controlled-campaign evidence without directly editing gate status.
- Add guarded Alpha-only watchdog and native-recovery scenario initiation,
  an automated watchdog HIL observer, and a broad host fault-simulation campaign
  whose output is explicitly marked non-qualifying.
- Retain native ABI 6 and the existing cross-release qualification campaign;
  use release sequence 2742.

## 3.0.0-alpha.36 - 2026-09-21

- Retry qualification history writes under encrypted-storage pressure by trimming
  older diagnostic records, while retaining the latest failure and failing closed
  if it cannot be archived. Align the Automatic method badge at the top right.

## 3.0.0-alpha.35 - 2026-09-21

- Replace the upgrade status summary with a concise Automatic method badge;
  retain conditional Staged activation and explicit stage/restart actions.
- Show upgrade history without expansion and persist a separate bounded history
  of manual and scheduled release checks, including outcomes and versions.
- Allow administrators to restart only a failed qualification test with a reason
  and confirmation, archiving its evidence before resetting its observation window.
  Preserve unrelated gates and migrate existing evidence without clearing failures.
- Retain MicroPython 1.29.0, ESP-IDF 5.5.5 and native ABI 6; release sequence 2740.

## 3.0.0-alpha.34 - 2026-09-20

- Open the shared upgrade workflow directly, with Automatic, Manual and
  conditional Staged and Rollback methods together above the milestones.
- Fix horizontal milestone layout under the strict portal CSP without inline
  style attributes or a horizontal scrollbar; retain a mobile vertical layout.
- Make staging explicit, keep the same milestones after staging, and separate
  the subsequent restart action. Keep release checks inline without percentages.
- Keep automatic upgrade form actions inside their card and map receiving
  progress to the appropriate component milestone.
- Pin ESP-IDF 5.5.5 in the build lock and CI, retaining MicroPython 1.29.0 and
  native ABI 6. Use release sequence 2739; renew hardware qualification for the
  changed SDK baseline.

## 3.0.0-alpha.33 - 2026-09-15

- Replace the upgrade ladder with a responsive horizontal milestone track whose
  task names sit above circular per-stage progress indicators; retain a compact
  vertical layout on narrow screens.
- Make Automatic and Manual explicit selectable methods in the shared install
  workflow, with a signed-file input for Manual and an authenticated release
  version selector for Automatic.
- Consume the Management Suite's bounded multi-version channel inventory,
  filter every independently signed release set for compatibility and monotonic
  sequence, preselect the newest valid version and reject stale submissions.
- Retain native ABI 6 and use release sequence 2738.

## 3.0.0-alpha.32 - 2026-09-15

- Decode the standard SEC1 DER renewal key written during IoT CA enrollment
  before signing a manual or scheduled renewal request.
- Retain compatibility with early development installations that persisted the
  P-256 renewal scalar directly, while rejecting malformed or out-of-range
  renewal keys.
- Retain native ABI 6 and use release sequence 2737.

## 3.0.0-alpha.31 - 2026-09-15

- Keep manual uploads moving when their browser tab is hidden by scheduling
  each chunk from the preceding network completion rather than animation
  frames; warn before leaving while a local file transfer is active.
- Make asynchronous release and certificate operations reconnectable through
  stable task URLs, a bounded device-side task registry and a compact global
  running-task indicator.
- Resynchronise live portal views when a tab becomes visible, reduce background
  polling, show current refresh times and provide a client-side Device log
  filter used by failure links.
- Add skip navigation, complete keyboard menu movement, consistent focus and
  target treatment, reduced-motion support, automatic dark presentation and
  forced-colour compatibility.
- Apply a per-response nonce Content Security Policy, use a browser-enforced
  `__Host-` HTTPS session cookie and add strong conditional caching for
  fingerprinted portal assets.
- Warn about unsaved form changes and improve the accessible explanation of
  sole-administrator protection without adding permanent visual clutter.
- Add a non-destructive Playwright and axe qualification suite covering
  Chromium, Firefox, WebKit and representative mobile viewports.
- Retain native ABI 6 and use release sequence 2736.

## 3.0.0-alpha.30 - 2026-09-15

- Present the sole-administrator protection explanation as hover and accessible
  help on the protected user controls instead of permanent form text.
- Remove the redundant **Install upgrade** navigation entry, retain its route
  as the transient installation workflow, and rename **Available upgrades** to
  **Upgrade**.
- Right-align the Automatic upgrade action row and keep **Check for upgrades**
  as its rightmost action, matching the other upgrade sections.
- Make qualification status reads side-effect free so an NVS capacity error
  cannot prevent the portal or its error page from rendering.
- Preserve authoritative qualification counters while pruning older derived
  release summaries when encrypted NVS is under pressure.
- Reclaim the inactive encrypted configuration and native transactional slots
  before allocating their replacements, while retaining the selected valid
  generation throughout every power-loss transition.
- Record the HTTP method and route with future portal request failures.
- Retain native ABI 6 and use release sequence 2735.


## 3.0.0-alpha.29 - 2026-09-14

- Consolidate upgrade discovery into ordered Summary, staged-upgrade,
  Rollback, Automatic upgrade and Manual upgrade sections.
- Route both automatic and manual selections through the same dedicated
  installation workflow, with type-specific steps and no device mutation
  before the operator selects **Initiate upgrade**.
- Keep automatic download progress inside the normal portal shell, return to
  the same installation workflow after staging and use a consistent **Restart
  and install** final action.
- Retain Alpha 28's signed universal-plan storage authority so constrained
  devices can reclaim an inactive application generation between sequential
  core and application uploads without granting that authority to standalone
  recovery files.
- Provide an application-first bridge for Alpha 26 and Alpha 27 devices that
  cannot initially stage the larger paired universal release.
- Retain native ABI 6 and use release sequence 2734.

## 3.0.0-alpha.28 - 2026-09-14

- Carry the signed universal-plan storage policy through sequential firmware
  and application uploads, allowing the inactive application generation to be
  reclaimed when the inner core bundle cannot otherwise fit on the filesystem.
- Retain each inner component's real installer type while limiting this reclaim
  authority to uploads already bound to a verified universal manifest.
- Provide an application-first bridge path for devices unable to stage the
  Alpha 27 core: activate the Alpha 28 application, then install the Alpha 28
  universal release.
- Retain native ABI 6 and use release sequence 2733.

## 3.0.0-alpha.27 - 2026-09-14

- Reclaim only the stale alternating encrypted-NVS snapshot when ESP-IDF
  reports `ESP_ERR_NVS_NOT_ENOUGH_SPACE`, preserving the latest qualification
  record throughout the retry and replacing the raw `4357` failure.
- Protect the sole enabled administrator in both the portal controls and the
  existing server-side policy; role and enabled controls unlock only after a
  second enabled administrator exists.
- Replace the single Upgrades entry with an alphabetic submenu containing
  **Available upgrades**, **Install upgrade**, and **Settings**.
- Send automatic downloads and local signed uploads to the dedicated install
  page, while release checks and discarded releases return to the available
  upgrade workflow.
- Keep automatic release-channel, schedule, download and activation settings
  on their own administrator-only page.
- Retain native ABI 6 and publish application and core together because the
  qualification storage repair spans native firmware and the portal runtime.

## 3.0.0-alpha.26 - 2026-09-14

- Preflight application-slot capacity before selecting a paired core and, when
  flash is temporarily constrained, retain the verified application bundle in
  PSRAM while releasing its staging blocks for transactional extraction.
- Freeze the constrained-capacity activator into the recovery core so paired
  activation remains available without importing the product application.
- Consolidate release-channel and local-file upgrades into one consistent
  source workflow and use the same staged activation panel for either path.
- Present automatic upgrade settings as a collapsible secondary section and
  suppress duplicate available-release notices after a release is staged.
- Show percentages only while device tasks are running; completed release
  checks now report the useful result, such as **Release available** or **No
  newer release**, before returning to Upgrades.
- Retain native ABI 6 and publish application and core together because the
  storage activation repair spans the frozen core and application coordinator.

## 3.0.0-alpha.24 - 2026-09-13

- Prevent the qualification recorder from exhausting the native four-handle
  storage table across application restarts or failed initialization.
- Make native storage namespace opens idempotent, so reopening `v3qual`,
  `v3qualhist` or `v3qualcamp` reuses the existing NVS handle.
- Close every qualification namespace after partial startup failure and during
  orderly application shutdown, while retaining all persisted evidence.
- Retain native ABI 6 and release the application and core as one paired
  universal update because the repair spans both components.

## 3.0.0-alpha.23 - 2026-09-13

- Publish a paired release with sequence 2728 so the automatic
  universal upgrade path introduced in Alpha 22 can be exercised end to end.
- Make restart recovery probes time-bounded so an unavailable connection cannot
  prevent the restart page from returning automatically to sign-in.
- Proactively sign out an inactive browser at its per-user timeout instead of
  waiting for the next navigation.
- Rename **Portal users** to **Users**, align existing/new user fields and
  actions, and align overview status labels and values.
- Surface **Renew now** with the installed identities under **Device
  certificates**, and bottom-align removal actions across every trust card.
- Pair with Management Suite 2.2.6, whose GitHub synchronization removes
  releases and unreferenced files that have been deleted upstream.
- Retain native ABI 6 and all existing qualification campaign evidence.

## 3.0.0-alpha.22 - 2026-09-10

- Move Portal users from its own top-level menu into Maintenance and align the
  existing-user sign-in status with the new-user initial-password field.
- Let administrators create a disabled portal user while keeping **Enabled**
  selected by default.
- Keep USB-staged application updates in the ready state until frozen recovery
  activates them during reboot, preventing a premature trial from rolling back.
- Prefer a Management Suite universal descriptor during automatic checks and
  pass its download through the same paired verifier, activation and rollback
  transaction as a manual `.iotuni` upload. Retain component descriptors for
  first-time setup and recovery without silently falling back to a mismatched
  pair.


## 3.0.0-alpha.21 - 2026-09-09

- Correct the compact release builder's portal route contract so request,
  session and user-management context is passed into every generated
  MicroPython dispatcher instead of failing with undefined names.
- Validate every captured portal dispatcher dependency during source tests to
  prevent installed bundles diverging from the source-tested request paths.
- Identify automatic two-component releases as paired core-and-application
  upgrades and identify individual application, core and universal artifacts
  explicitly.
- Rename the automatic action to **Download and stage**, right-align it beside
  the release information and move staged state into a neutral **Upgrade
  process** panel shared by automatic and manual workflows.
- Retain native platform ABI 6 and the Alpha 20 qualification campaign state.

## 3.0.0-alpha.20 - 2026-09-09

- Preserve paired-upgrade, certificate-renewal, power-recovery and controlled
  validation evidence across release changes within the native ABI 6
  qualification campaign, while restarting release-specific soak and health
  sampling for each build.
- Keep expected paired-update rollback diagnostic without treating rollback
  itself as a failed qualification, and expose the worst consecutive unhealthy
  run behind the Health gate result.
- Recover a configured MQTT service through bounded background retries instead
  of permanently latching an otherwise healthy device into the failed state.
- Add per-user failed-sign-in limits, encrypted account lockout, administrator
  unlock, individual inactive-session timeouts and forced password replacement
  for administrator-issued credentials.
- Return expired sessions to a signed-out login page and make long-running
  portal requests handle session expiry consistently.
- Add immediate managed certificate renewal using the currently selected
  enrollment method and record its observed qualification result.
- Correct certificate distinguished-name escaping on MicroPython so apostrophes
  are never rendered as literal HTML entities in any certificate view.
- Present existing and new portal users as equal fixed-width cards in one
  section, and add a compact green/amber/red device-state LED before the Status
  menu.

## 3.0.0-alpha.19 - 2026-09-08

- Record a successful physical power recovery automatically once a genuine
  `pwron_reset` boot following a healthy boot reaches the healthy `running`
  stage.
- Exclude first boots, software resets, failed or degraded starts and repeated
  observations of the same runtime from power-recovery qualification evidence.
- Retain the preceding durable boot snapshot in memory without changing the
  rollback-compatible boot-state record format.
- Add a persistent `power_recovery_qualified` health event and identify the
  power-recovery qualification gate as device-observed in the portal.
- Retain native platform ABI 6 and all Alpha 18 recovery and qualification
  history protections.

## 3.0.0-alpha.18 - 2026-09-08

- Add clear visual separation between the manual-upgrade filename state and
  the pre-selection artifact guidance.
- Prevent a transient Wi-Fi association failure from falsely entering recovery:
  warning events are now valid legacy log severities, unknown severities fall
  back safely, and a failed diagnostic callback cannot abort bounded retries.
- Keep the current release's qualification counters and soak start in the
  existing rollback-compatible transactional record, and retain compact
  summaries for the four preceding releases in a separate encrypted namespace.
- Label each portal qualification gate as an automatic device observation or a
  controlled qualification test, and expose the missing renewal, power and
  validation recording methods through the runtime qualification bridge.
- Retain native platform ABI 6 and all implemented greenfield mechanisms;
  qualification and controlled cutover remain the only open architecture gates.

## 3.0.0-alpha.17 - 2026-09-08

- Present the active manual-upgrade operation as one prominent **Current
  task** label without duplicating the step number already shown by the
  vertical workflow.
- Preserve each file type's detailed workflow after verification, including
  all eight universal stages through activation and reboot.
- Hide artifact-type guidance once a file is selected so it cannot run into
  the selected filename.
- Add the Alpha automatic-upgrade channel throughout portal preferences,
  credential validation, signed catalog validation/schema and release
  publishing.
- Align the Management Suite 2.2.3 release catalog, promotion selector,
  storage paths and HTTPS endpoint with the new Alpha channel.
- Retain native platform ABI 6 and all implemented greenfield mechanisms;
  qualification and controlled cutover remain the only open architecture gates.

## 3.0.0-alpha.16 - 2026-09-08

- Restore Grove AC Voltage calibration in compact release packages by making
  the generated live-route module import its calibration transport explicitly.
- Render unexpected authenticated request failures inside the normal portal
  shell, with safe recovery actions and full detail retained in Device log.
- Recover the manual-upgrade controls immediately after a rejected file: stop
  the working state, clear the rejected selection, and allow another file to
  be chosen without pressing Cancel.
- Replace the terse manual-artifact guidance with plain-language universal and
  recovery-file guidance.
- Keep linked overview text unadorned on hover and keyboard focus so only the
  tile outline, elevation and focus ring change.
- Retain native platform ABI 6 and all implemented greenfield mechanisms;
  qualification and controlled cutover remain the only open architecture gates.

## 3.0.0-alpha.15 - 2026-09-08

- Simplify manual upgrade staging to one file-specific vertical workflow and
  one current-task progress area. Hide the selected file once staging starts,
  keep Cancel and the state-aware primary action at the lower right, and make
  Cancel return to file selection.
- Persist Grove AC Voltage calibration through an atomic, read-back-verified
  settings transaction while retaining the previous settings generation for
  recovery.
- Display the active Grove AC calibration multiplier and offset in module
  diagnostics, and show calibration success or persistence failure on the same
  diagnostics page.
- Retain whole-tile keyboard focus and pointer feedback for linked overview
  metrics without changing the semantic status colours of their text.
- Retain Alpha 14's portal consistency work and Alpha 13's paired-update state
  migration without changing native platform ABI 6.

## 3.0.0-alpha.14 - 2026-09-06

- Make overview health and service metrics direct links to their relevant
  configuration, diagnostics, upgrade or qualification pages, with consistent
  keyboard focus and hover treatment.
- Preview the file-specific application, core or universal workflow as soon as
  a manual upgrade file is selected. Rename the primary action to **Upload and
  stage** and replace the separate guidance panel with a concise inline note.
- Standardise certificate badges so installed identities and trust anchors are
  green, expiry warnings are amber, and invalid or expired material is red.
- Align Power & reset, Current runtime health and Portal users with the shared
  portal card patterns, including removal of the redundant user-role badge.
- Retain Alpha 13's paired-update migration and all Alpha 12 confirmation and
  rollback protections unchanged.

## 3.0.0-alpha.13 - 2026-09-06

- Upgrade activating universal transactions created by pre-ABI-6 frozen
  coordinators before native pair preparation. The new core reconstructs the
  bounded pair identifier, trial runtime slot, previous slot and confirmation
  fields from the signed release sequence and live component state.
- Record `pair_state_upgraded` when this compatibility migration occurs, so
  qualification evidence distinguishes migrated trials from newly staged ones.
- Retain all Alpha 12 paired-confirmation ordering, failure recording and
  power-loss recovery protections.

## 3.0.0-alpha.12 - 2026-09-06

- Keep the previous application slot authoritative until native ESP-IDF core
  confirmation succeeds, so bootloader rollback cannot strand a newer runtime
  on an older frozen core.
- Prepare and reconcile the native pair through a frozen direct ABI adapter,
  rather than importing an application-slot adapter before that slot is on the
  module path; this ensures the native trial actually exists for confirmation.
- Persist each paired-confirmation phase and its exact failure before rollback,
  allowing the next boot and support history to identify confirmation faults.
- Permit a newer signed release sequence to replace a stale native pair journal
  left by an interrupted or bootloader-rejected trial.
- Remove the replaceable runtime's dependency on the newly frozen
  `application_slot_recovery` helper while retaining trial-aware version
  reporting, preserving operation with the previous confirmed core.

## 3.0.0-alpha.11 - 2026-09-06

- Make universal rollback restore the recorded previous application slot when
  the ESP bootloader rejects the matching core, preventing mixed releases.
- Report the application actually executing during its uncommitted trial while
  keeping the durable active-slot pointer unchanged until confirmation.
- Require native OTA-valid readback before committing the paired-update
  journal and use exact release-sequence matches for pair confirmation.
- Replace the manual-upgrade status fragments with one vertical workflow, one
  current-task progress bar, Cancel and a state-aware primary action.
- Remove the redundant password-verification message from sign-in.
- Add durable migration handle intents, interrupted-cutover reconciliation and
  an executable v3 product bootstrap.
- Remove the v3 production driver translator's dependency on v2 driver and
  logical resource-manager code.

## 3.0.0-alpha.10 - 2026-09-05

- Advance the native platform boundary to ABI 6 with an encrypted paired-update
  journal binding the release sequence, platform partition and runtime slot.
- Require the runtime trial to report healthy before the native platform can
  confirm the ESP-IDF OTA image; journal rollback intent before restoring the
  runtime slot and requesting bootloader rollback.
- Reconcile paired update state from the frozen recovery supervisor and preserve
  the previous runtime selection across interrupted activation or rollback.
- Add side-effect-free shadow comparison, the production v3 composition root,
  generation-safe migration staging and a complete 13-variant v2-to-v3 driver
  declaration bridge.
- Surface all nine greenfield implementation gates separately from their HIL
  qualification state. Active-v3 cutover remains fail-closed until the release
  evidence ledger and native qualification capabilities pass.

## 3.0.0-alpha.9 - 2026-09-05

- Advance the native platform boundary to ABI 5 with physical GPIO, ADC, UART,
  I2C and SPI construction, deterministic release and peripheral recovery.
- Permit only identically configured I2C/SPI buses to share a physical native
  instance; retain exclusive ownership for GPIO, ADC and UART.
- Route native GPIO edges through the bounded platform event queue and remove
  interrupt ownership during resource cleanup.
- Advance runtime configuration to version 4 with physical resource parameters,
  explicit shared-bus signatures and fail-closed migration from version 3.
- Add production lifecycle bridges for Wi-Fi/reconnection, MQTT/Home Assistant,
  HTTPS portal, mTLS Device API and syslog without coupling domain services to
  sockets or compatibility-runtime objects.
- Add a production certificate/trust bridge with encrypted transactional opaque
  handle mappings, all managed enrollment/renewal methods and generation-safe
  trust removal. Physical resources, adapters and identity remain unqualified
  until their HIL and interoperability evidence passes.

## 3.0.0-alpha.8 - 2026-09-05

- Add separate current-stage and overall manual-upgrade progress, with workflow-specific
  steps for application, core and universal bundles and a persistent completed-stage trail.
- Count browser upload bytes even when Safari does not mark its progress event as length
  computable, and yield between acknowledged chunks so intermediate percentages can paint.
- Replace the filtered SSID datalist with an unfiltered detected-network selector and an
  in-place manual-entry mode in both first-boot setup and Device > Network.
- Retry startup Wi-Fi three times within approximately the prior connection budget before
  latching frozen recovery, cleaning the station between failed attempts and logging each
  bounded retry. This prevents one transient association timeout after a power cycle from
  immediately stranding a remote device in recovery.

## 3.0.0-alpha.7 - 2026-09-05

- Register the native v3 platform module in MicroPython's generated import
  table, restoring the Alpha release-qualification recorder on hardware.
- Reject production core builds unless all three native IoT-MD modules are
  both compiled and registered as importable modules.
- Yield briefly after displaying the sign-in verification status so Safari
  paints it consistently before the password request is submitted.
- Advance the native platform boundary to ABI 4 with guarded OTA trial
  observation, confirmation and rollback mechanisms. Production paired-trial
  and rollback claims remain disabled until hardware qualification passes.
- Persist boot attempts and explicit recovery requests in encrypted native NVS
  before loading replaceable product code, so repeated incomplete boots enter
  the frozen signed-recovery path with bounded reset diagnostics.
- Add a fixed-capacity native job and event boundary for recovery and OTA trial
  operations, including structured error codes, retryability, a declared
  operation timeout and non-blocking queue-full behavior.

## 3.0.0-alpha.6 - 2026-09-05

- Keep universal core-firmware upload progress terminology stable between
  browser byte events and completed chunks instead of alternating between
  `core firmware` and the internal `firmware` component name.
- Require two consecutive, complete login-page and stylesheet readiness checks
  before leaving the restart page, with sequential probes and a short settling
  interval for resource-constrained portal listeners.
- Add a persistent 15-gate operational qualification contract covering soak,
  health, storage, network recovery, certificate renewal, paired upgrades,
  power interruption, canary state, release confirmation, native/watchdog
  recovery, identity/fleet interoperability, migration rollback and all 13
  physical driver variants. The 48-hour soak also requires sustained health
  and storage sample counts, preventing one late sample from qualifying it.
- Surface qualification state on the installed Overview, Maintenance portal,
  Device API inventory and support output without reporting unexecuted tests as
  passed or treating an unreachable device as an unhealthy/storage sample.
- Add a resumable host qualification runner for mTLS monitoring and explicit
  renewal, upgrade, power, recovery, interoperability, migration and driver
  observations.
- Add a persistent compatibility/shadow/active cutover coordinator. Active v3
  ownership is fail-closed until native paired trial/rollback and every
  recorded qualification gate pass; a failed v3 boot or health check invokes
  recovery and persistently returns to the compatibility runtime.

## 3.0.0-alpha.5 - 2026-09-04

- Advance runtime configuration to version 3 with explicit identity and fleet
  domains, multi-resource modules and non-mutating migration from earlier alpha
  contracts.
- Add opaque-handle certificate lifecycle orchestration, managed renewal for
  non-manual enrollment methods and generation-guarded trust removal.
- Add signed, scoped fleet policy validation, bounded inventory/canary reports
  and dedicated `fleet:read` and `fleet:write` Device API routes.
- Add previewed, fingerprint-bound v2 complete-backup migration which stages
  secrets in isolated platform storage and activates them only after a healthy
  v3 trial.
- Port the supported v2.5 driver catalog to a multi-resource lifecycle contract
  with deterministic claim cleanup, and add bounded identity, fleet and
  migration portal summaries.
- Retain the v2.5 compatibility product runtime while Alpha 5 certificate,
  fleet, migration, physical-driver and interruption HIL gates remain open.

## 3.0.0-alpha.4 - 2026-09-04

- Add browser byte-level progress to manual upgrade chunks so the initial
  upload visibly advances instead of remaining at zero percent.
- Distinguish resumable transport hashing from signed application verification,
  removing the misleading appearance that a universal upgrade verifies the
  application twice.
- Advance runtime configuration to version 2 with bounded, dependency-ordered
  product transport declarations and non-mutating Alpha 3 migration.
- Add injected Wi-Fi, MQTT, server-rendered portal and mTLS Device API v3
  services over transport-neutral request, response and state contracts.
- Generate role-aware navigation and diagnostic forms from shared metadata and
  add bounded DNS, time, TLS, MQTT, CA, syslog and release probes with redacted
  failures.
- Retain the v2.5 compatibility network runtime until Alpha 4 parity, security
  and network-fault hardware qualification is complete.

## 3.0.0-alpha.3 - 2026-09-04

- Advance the native platform boundary to ABI 3 with owner-scoped, bounded
  resource claims for ADC, GPIO, I2C, SPI and UART identities.
- Add an exact, versioned runtime configuration contract and a non-mutating
  migration preview from the initial draft configuration.
- Add the greenfield application kernel, dependency-aware service registry and
  cooperative supervisor with isolated degradation, restart and cleanup.
- Port a small reference sensor through the new driver/resource contracts and
  cover restart, invalid configuration, resource conflict and transient failure.
- Add bounded health, event and support snapshots with executable JSON schemas;
  configuration settings and secret material are not included.
- Retain the v2.5 compatibility product runtime and keep hardware-only Alpha 1
  and Alpha 2 recovery gates explicitly open.

## 3.0.0-alpha.2 - 2026-09-04

- Advance the native platform boundary to ABI 2 with bounded opaque encrypted-
  NVS namespace handles and alternating, CRC-protected snapshot generations.
- Add the runtime transactional-storage adapter and the first executable paired
  platform/runtime state machine covering staging, trial, confirmation,
  mismatch detection and restoration of the previous confirmed pair.
- Add schemas and interruption tests proving each Alpha 2 state transition
  recovers to either the complete old generation or complete new generation.
- Return from update-finalisation requests immediately and run verification as
  an asynchronous task, allowing the portal to display live firmware and
  application byte progress instead of remaining at zero percent.
- Install the Management Suite release-signing key through its own validated,
  power-safe protected-file transaction instead of incorrectly routing it
  through the X.509 certificate path validator.
- Keep native paired trial selection and rollback capability reported as
  unavailable until partition-control and power-cut HIL qualification pass.

## 3.0.0-alpha.1 - 2026-09-01

- Add the first versioned native `_iotmd_platform_v3` capability ABI and a
  fail-closed MicroPython adapter backed by an executable JSON contract.
- Report the real platform security, PSRAM, OTA partition and interface gates
  without claiming USB NCM availability.
- Retain the stable v2.5 product behavior as an explicitly temporary
  compatibility payload so the new native/runtime boundary can be qualified
  independently before application services are ported.

## 2.5.0 - 2026-09-01

- Promote the tested 2.5 beta series to stable with transport-neutral Device
  API contracts, smaller API projections and centrally resolved feature flags.
- Add hardware resource management, explicit USB/NCM capability diagnostics
  and safe ESP32-S3 gating while retaining Wi-Fi as the production transport.
- Improve runtime reliability, boot-health reporting, certificate and logging
  navigation, portal-user administration and consistent upgrade terminology.
- Finalise the Status, Device, Module, User, Maintenance navigation order with
  alphabetised destinations, click-to-expand Maintenance categories and
  origin-preserving avatar-menu password changes.

## 2.5.0-beta.5 - 2026-09-01

- Restore the requested Status, Device, Module, User, Maintenance top-level
  order while keeping the destinations within each dropdown alphabetical.
- Make the Maintenance Certificates and Logging categories click-to-expand,
  keep unrelated categories collapsed, and retain the active category on its
  destination pages.
- Return successful avatar-menu password changes to the originating portal
  page and give portal-user cards a bounded width with clearly separated user
  actions.

## 2.5.0-beta.4 - 2026-09-01

- Standardise the portal navigation around **Device**, **Maintenance**,
  **Module**, **Status** and **User**, alphabetise destinations and render
  certificate and logging destinations as always-visible labelled groups in
  the Maintenance menu.
- Rename Messaging to **MQTT**, Device control to **Power & reset**, and use
  **upgrade** consistently for device software installation while retaining
  compatible internal `update` routes and state keys.
- Move password changes into an avatar-menu dialog, split existing and new
  portal users, and allow administrator usernames and other portal identities
  to be renamed without invalidating their current sessions.
- Restore Health History timestamps and expose current device state, boot
  stage, active network transport, hardware allocations, USB NCM availability
  and effective runtime features alongside the persistent health counters.

## 2.5.0-beta.3 - 2026-09-01

- Replace the flat certificate links in Maintenance with a grouped
  **Certificates** submenu containing enrollment, CA/signing trust, API client
  trust and device-certificate destinations.
- Keep the certificate destinations visible whenever Maintenance is open,
  mark the active destination and increment the portal asset version so
  browsers fetch the corrected navigation CSS and JavaScript.

## 2.5.0-beta.2 - 2026-09-01

- Freeze the TLS-session compatibility seam required by the recovery-layer
  release client, allowing a firmware-first universal trial to start while the
  previous application generation is still active.
- Enforce the complete project-local import closure of every frozen recovery
  module at build/test time, preventing another core from depending on files
  available only in its matching application bundle.

## 2.5.0-beta.1 - 2026-09-01

- Introduce transport-neutral Device API request/response contracts and retain
  HTTPS/mTLS as an adapter, allowing the same API router to serve any qualified
  IP interface without duplicating domain behavior.
- Add smaller `/api/v2/device`, `/interfaces`, `/hardware`, `/services`, and
  `/configuration` projections while retaining the combined inventory endpoint
  for backward compatibility.
- Add central signed feature flags resolved against the release channel,
  firmware build and detected runtime capabilities; expose both enabled state
  and the reason a requested feature is unavailable.
- Add the experimental USB NCM transport contract, lifecycle and capability
  gating. The current ESP32-S3 core reports it unavailable because MicroPython
  1.29's generic driver is not yet integrated with the ESP32 network/TinyUSB
  port; Wi-Fi remains the required interface.
- Separate USB device hardware, NCM hardware, runtime symbol and validated NCM
  availability diagnostics so `network.USBD_NCM` alone cannot enable the
  production transport.
- Add an opaque TLS-session handle accepted by outbound clients without claiming
  resumption support on MicroPython 1.29, which exposes no stable session API.
- Extend hardware preflight into an owner-scoped logical resource manager with
  provider injection and shared-instance caching; migrate MAX31865 SPI and
  chip-select construction to the injected resource path.
- Show a healthy running Device State tile with the same green treatment as
  other healthy services and keep certificate destinations persistently visible
  in the open Maintenance menu.

## 2.4.0-beta.3 - 2026-08-31

- Expose all four certificate-management destinations directly in the
  Maintenance menu and remove the redundant certificate-page tab bar.
- Expand managed-task diagnostics with lifecycle state, criticality, start and
  failure counts, last error, and successful heartbeat timing.
- Record current free and allocated heap alongside the minimum free heap since
  boot, without making point-in-time observations trigger flash checkpoints.
- Route portal background operations through the central task supervisor so
  their failures participate in the same runtime-health model.

## 2.4.0-beta.2 - 2026-08-31

- Load the activation-heap policy through the signed application settings
  boundary, fixing the beta.1 startup `NameError` observed on hardware.
- Guard the compact application entry against an older recovery core after a
  paired firmware rollback, restoring the confirmed application without
  importing modules available only in the newer frozen core.

## 2.4.0-beta.1 - 2026-08-31

- Add a staged boot supervisor record covering platform, persistent state,
  update reconciliation, filesystem, configuration, certificates, hardware,
  network, portal, essential services, activation health and running state.
- Retain the compact boot record across resets in CRC-protected RTC no-init
  memory provided by the native IoT-MD platform module, with an atomic flash
  fallback and no secret material.
- Detect runtime capabilities rather than inferring them from the MicroPython
  version, including PSRAM heap, OTA partitions, watchdog and reset-persistent
  memory support.
- Refuse trial confirmation when required PSRAM, activation heap, local portal,
  network or a configured watchdog is unavailable; classify NTP, Device API,
  MQTT and other external-service failures as degraded operation.
- Expose the unified device state, boot stage, boot record and capability
  matrix through portal status, Device API inventory and support bundles.
- Preserve the proven MicroPython 1.29.0 and ESP-IDF 5.5.1 toolchain while the
  boot architecture is qualified independently of a future IDF major upgrade.

## 2.3.13 - 2026-08-31

- Place the four certificate-management pages beneath a single Maintenance >
  Certificates entry with a persistent certificate submenu and hierarchical
  breadcrumbs.
- Show the manual portal or Device API certificate-and-key upload controls
  directly when Manual certificate package is selected, retaining the
  Certificate enrollment page after validation.

## 2.3.12 - 2026-08-31

- Restore the ESP32-S3 PSRAM-backed MicroPython heap in the 1.29 firmware by
  combining the S3 SPIRAM base settings with the octal-mode variant.
- Reject production core builds when PSRAM, boot initialisation, malloc
  integration, or octal mode is absent, preventing internal-RAM-only firmware
  from being packaged again.

## 2.3.11 - 2026-08-31

- Store large renderer-local HTML and JavaScript constants as bounded 2 KiB
  chunks in compact application bytecode, deferring their assembly until the
  relevant page is requested.
- Eliminate the hardware-observed 8,850-byte contiguous allocation during
  `portal_live_views` import while preserving byte-for-byte renderer output.
- Use core-firmware-first activation for the v2.2.9 to v2.3.11 universal
  transition so MicroPython 1.29 and the compact v2.3 application start as one
  paired, rollback-protected trial.

## 2.3.10 - 2026-08-31

- Extract the remaining access-control and update-upload dispatchers from the
  portal transport after the v2.3.9 hardware trial showed its reduced module
  still requested the same 8,850-byte aggregate import allocation.
- Preserve login/session mutations across the access-route boundary and share
  upload progress through an explicit request-state record.
- Reduce the compiled portal transport from 13,286 to 8,550 bytes and tighten
  its build-time growth ceiling to 10,000 bytes.

## 2.3.9 - 2026-08-31

- Compile the settings and live portal route dispatchers as independent
  MicroPython modules, eliminating the aggregate 8,850-byte allocation that
  caused the v2.3.8 A/B trial to roll back despite ample total free heap.
- Add compact-bytecode size gates for the portal transport and extracted route
  modules so future portal growth cannot silently restore the trial-boot fault.

## 2.3.8 - 2026-08-31

- Load the split portal transport through a release-specific application
  module identity during A/B trial startup, preventing the active v2.2.9
  generation from satisfying the import with its 8,960-byte handler.
- Compile the canonical portal implementation into that new module name while
  retaining the existing development and test import surface.

## 2.3.7 - 2026-08-30

- Split portal access control, settings, update upload and live routes into
  bounded MicroPython coroutines, reducing the largest portal bytecode
  allocation from 8,687 bytes to 2,471 bytes during trial startup.
- Add architecture ceilings for each portal request-handler boundary so the
  hardware-observed contiguous-allocation failure cannot silently return.

## 2.3.6 - 2026-08-30

- Load the remaining large web-portal bytecode module immediately after a
  startup garbage collection, before smaller imports fragment the heap.
- Add an import-order regression gate for the 17 KiB contiguous allocation
  failure observed during the v2.3.5 hardware trial.

## 2.3.5 - 2026-08-30

- Replace the 126 KiB source application entry with a compact,
  recovery-compatible bootstrap and package the full runtime as precompiled
  MicroPython bytecode.
- Preserve the existing `iotmd.py` activation contract so devices running an
  earlier recovery core can install the application safely.
- Add entry-size and bundle-compaction regression gates to prevent the
  trial-boot source-compilation memory failure from returning.

## 2.3.4 - 2026-08-30

- Reduce normal startup heap pressure by loading certificate-administration
  actions, transport and views only when their portal routes are used.
- Compile the application entry and release its source buffer before execution,
  avoiding a second large live allocation while imports initialize.
- Record free and allocated heap before application load and immediately before
  execution when startup fails, preserving actionable diagnostics in update
  history and on USB serial.
- Add architecture and recovery regression coverage for the lazy certificate
  boundary and loader heap diagnostics.

## 2.3.3 - 2026-08-30

- Reconcile orphaned universal-update transactions after a paired component
  rollback, allowing a remote portal upload to retry without USB intervention
  while preserving legitimate staged and trial updates.
- Preserve the underlying trial-application startup exception in update
  history and print its traceback to USB before performing a paired rollback.

## 2.3.2 - 2026-08-30

- Correct the automatic-upgrade server default to
  `https://iot-upgrade.home.arpa:8443`.

## 2.3.1 - 2026-08-30

- Make the automatic-upgrade release server visible and editable under
  Maintenance > Upgrades, defaulting to
  `https://iotmd-update.home.arpa:8443` and deriving the selected Stable or
  Beta catalog path automatically.
- Require an HTTPS origin with a valid hostname and optional port before a
  release-server change is stored or used.

## 2.3.0 - 2026-08-29

- Accept Management Suite format-3 Stable/Beta release catalogs signed by the
  existing fleet-policy identity, while continuing to verify every downloaded
  application or core bundle with the immutable offline update key.
- Add **Management Suite verification key** import under Maintenance >
  Certificates and retain that shared fleet/catalog trust identity through update, encrypted
  backup/restore and factory reset workflows.
- Preserve format-2 offline-signed release catalogs for direct/static release
  publication.
- Use `iot-md-001` and `iot-md-001.local` as the first-boot device-name and
  mDNS defaults, and align device identity examples without changing the WHES
  module name or identifiers.
- Show remote syslog health alongside Wi-Fi, MQTT and Device API state on the
  overview page.
- Split certificate enrollment, outbound CA/signing trust, Device API client
  trust and device identities into focused Maintenance pages. Show and change
  the active enrollment method, and remove obsolete trust anchors explicitly.
- Standardise **IoT CA enrollment authorization (`.iotenroll`)** and the other
  certificate-method names across first boot, maintenance and IoT CA.
- Include every certificate enrollment, trust and portal module in application
  update bundles, with a regression check against incomplete releases.
- Update the reproducible firmware baseline to MicroPython 1.29.0 while
  retaining the supported ESP-IDF 5.5.1 toolchain.

## 2.2.9 - 2026-08-28

- Standardise the human-facing product acronym as **IoT-MD** across the web
  portal, setup and recovery pages, access-point names, device display,
  Home Assistant metadata, syslog application labels and documentation while
  preserving compatibility-sensitive protocol and update identifiers.
- Keep the daily and weekly automatic-upgrade schedule fields the same width
  as the adjacent release-channel and schedule controls.

## 2.2.8 - 2026-08-28

- Keep the certificate-enrollment **Check status now** button visually stable
  during automatic polling instead of repeatedly applying the disabled style.
- Prevent overlapping automatic and manual enrollment-status requests with an
  internal in-flight guard that does not alter the control’s appearance.

## 2.2.7 - 2026-08-28

- Show only the schedule fields relevant to disabled, daily or weekly automatic
  upgrade checks, and give selects and other form controls a consistent height.
- Combine scanned and manually entered Wi-Fi network names into one editable
  SSID control in both first-boot setup and System > Network.
- Preserve non-secret setup values after a failed Wi-Fi join, clear all
  password fields, and reset the ESP station interface before a retry to avoid
  stale `Wifi Internal State Error` failures.
- Embed the setup-complete page styling before reboot and centre its login
  action, eliminating the remaining Safari render race during first boot.

## 2.2.6 - 2026-08-28

- Close and await setup, recovery and upgrade HTTP responses before restarting
  or continuing background verification, so Safari renders styled transition
  pages immediately instead of waiting for the browser to stop the request.
- Use the same MicroPython-safe stream shutdown for the Device API, outbound
  release and ACME clients, ACME challenge handling and TLS syslog retries.
- Make the factory-reset setup address clickable and add a dedicated
  **Open device setup** button for reconnecting to `http://192.168.4.1`.

## 2.2.5 - 2026-08-27

- Restore **IoT CA enrollment file (`.iotenroll`)** as a first-class setup
  wizard choice instead of hiding it beneath automatic provisioning.
- Standardise certificate method names across IoT-MD and IoT CA.
- Automatically rotate IoT CA public portal, private Device API and renewal
  identities as one authenticated set, and regenerate self-signed identities
  after two-thirds of their lifetime.
- Make **Manual certificate package** the only non-renewing method and warn in
  both the Certificates portal page and Device log.

## 2.2.4 - 2026-08-27

- Validate all portal and recovery password pairs together, marking both
  fields in every mismatched or duplicated pair without retaining stale
  browser validation errors.
- Confirm the home Wi-Fi station connection before presenting the network
  handover page and retain the setup access point long enough to load its UI.
- Keep automatic IoT CA enrollment on a styled progress page that polls the
  device, tolerates temporary connection loss and redirects only after the
  enrollment reaches a terminal state.

## 2.2.3 - 2026-08-27

- Keep setup password validation on the wizard page, identify each invalid
  field in red and explain duplicate or mismatched credentials inline.
- Replace the combined certificate page with a choice-first workflow that
  reveals only the selected self-signed, IoT CA, private ACME or manual route.
- Make the IoT CA provisioning port configurable and treat blank IoT CA and
  ACME endpoint fields as the documented `iot-ca.home.arpa` defaults.

## 2.2.2 - 2026-08-27

- Restore the factory-reset first-boot access point by removing an application-
  layer logging dependency from the certificate enrollment module frozen into
  the core.
- Retain certificate enrollment failure diagnostics through the normal Device
  log when the application is mounted and the USB console during first boot.
- Add a regression test that imports the frozen enrollment path with the
  application package deliberately unavailable.

## 2.2.1 - 2026-08-26

- Replace file-backed combined universal staging with a signed sequential
  transport: validate the outer `.iotuni` manifest, then upload and verify its
  signed core and application components one at a time before paired activation.
- Reduce the measured v2.2.0 filesystem peak from 1,974,272 bytes to 1,556,480
  bytes on the device's 4096-byte FAT allocation units.
- Adopt completed resumable application bundles in place instead of creating a
  second full temporary copy.
- Include filesystem allocation rounding and metadata work blocks in update
  preflight checks, and translate raw error 28 into a named storage failure.
- Persist the universal component plan so a browser refresh or interrupted
  component upload resumes without weakening signed size, digest, version or
  release-sequence binding.
- Record the original universal rejection detail, including final state-write
  failures, in update history.
- Add one-step IoT CA certificate provisioning from an explicitly enabled CA
  enrollment window while retaining the one-time authorization-file fallback.
- Correct certificate filename wrapping throughout first boot, and display
  enrollment failures in a red status box with actionable DNS error text.

## 2.2.0 - 2026-08-26

- Add a host-bound IoT CA enrollment workflow to first boot while retaining
  explicit public-certificate, local ACME, manual-certificate and self-signed
  choices for the administrator.
- Generate separate P-256 portal, private Device API and renewal keys on the
  device, submitting only signed CSRs to IoT CA over pinned HTTPS.
- Validate enrollment expiry, authorized hostnames, CSR usages and returned
  identities before activating all certificate and state files atomically.
- Keep Cloudflare credentials and all device private keys on their respective
  systems; neither is included in the enrollment response or persistent token
  state.

## 2.1.3 - 2026-08-26

- Compile importable application modules to compact MicroPython bytecode so a
  universal update remains within the device's safe LittleFS staging budget.
- Reject oversized universal artifacts during the release build instead of
  allowing a device upgrade to fail later with raw error 28 (`ENOSPC`).
- Divide automatic upgrade controls into a manual release check and saved
  automatic-update settings.
- Move signed-in user details and the sign-out action into the avatar menu.

## 2.1.2 - 2026-08-26

- Separate the public portal and private Device API/fleet server identities so
  public portal renewal cannot alter private service trust.
- Extend first-boot provisioning for IoT CA public-portal packages containing
  public portal files, private API files and private trust anchors.
- Preserve separate `.local` mDNS and public portal DNS names for correct TLS
  validation and restart reconnection.
- Include both server identities in complete encrypted backup and validate each
  certificate/key pair before restore.
- Migrate an existing 2.1.1 portal identity once to the independent API path so
  the test device remains manageable until its private identity is installed.
- Standardise portal status presentation with semantic information, success,
  warning and failure boxes, including live upgrade progress and state tiles.

## 2.1.1 - 2026-08-25

- Keep Home Assistant discovery publishing inside the Home Assistant section
  of **Messaging** and clarify the discovery integration label.
- Replace the compact `IM` portal mark with a stacked, accessible `IoT` / `MD`
  mark in both the application and recovery portal shells.
- Compact universal application tails with block-by-block LittleFS reclamation
  so copy-on-write storage does not fail with raw error 28 (`ENOSPC`).
- Correct the documented v2.0 transition to use the v2.0.15 application/core
  components, the v2.0.16 core bridge, then the v2.1 components in order.

## 2.1.0 - 2026-08-25

- Rebrand the product as IoT Modular Device (IoT-MD), including the runtime,
  firmware board, native module, repository references and signed update
  formats (`.iotapp`, `.iotcore` and `.iotuni`).
- Replace platform-specific MQTT topics with administrator-defined templates,
  QoS, retained-state and command-subscription controls.
- Make Home Assistant discovery an optional integration layered over the same
  MQTT connection and combine both settings under **Messaging**.
- Publish a complete API contract, MQTT and Home Assistant integration guides,
  detailed per-module references and the WHES calculation assumptions.
- Define the companion IoT-MD Management Suite for fleet and secure release
  management while retaining the generic IoT Certificate Authority and IoT
  Syslog Server as independent add-ons.
- Persist upgrade upload, verification, staging, download and activation
  failures in the Device log and structured health/update history with the
  original failure detail.

### Required transition from v2.0

- Install the v2.0.15 application and core components separately, followed by
  the v2.0.16 core bridge and then the v2.1 application and core components.
- Do not use a universal container while crossing the v2.0/v2.1 boundary.

## 2.0.14 - 2026-08-25

- Add a one-time transition core that accepts both the established v2 update
  containers and the new IoT-MD application, core and universal formats.
- Allow the normal and recovery upload interfaces to select either generation
  so a deployed v2.0.13 device can cross the v2.1 format boundary safely.

## 2.0.13 - 2026-08-25

- Replace unsupported frozen `bytearray` slice deletion with MicroPython-safe
  buffer slicing so portal and API requests parse correctly on the device.
- Version the optional buffered-reader capability and bypass implementations
  that do not advertise the corrected contract during application-first upgrades.
- Extend the MicroPython compatibility gate to reject slice deletion in future
  application or frozen-core changes.

## 2.0.12 - 2026-08-25

- Restore Web Portal and Device API request handling when the v2.0.11
  application is bootstrapped on a v2.0.9 core that does not yet provide the
  optional buffered HTTP reader and timeout classifier.
- Retain the persistent-connection performance improvements automatically
  after the matching core has been installed.

## 2.0.11 - 2026-08-25

- Reclaim only the inactive application generation when a universal resumable
  upload would otherwise exceed available storage; the active generation is
  never removed.
- Compact a completed `.iotuni` in place after its core component is written,
  adopting the verified inner `.iotapp` without temporarily storing both files.
- Release resumable metadata before installation mutates its artifact so an
  interrupted compaction is safely replaced by the next upload attempt.

### Upgrade from 2.0.9 or 2.0.10

- Install `application-2.0.11.iotapp` first to update the uploader, restart and
  confirm it, then install `universal-2.0.11.iotuni` to update the core.

## 2.0.10 - 2026-08-25

- Reuse normal Web Portal and mTLS API connections for up to 32 requests,
  avoiding a new TLS handshake for every navigation, asset, or API call.
- Buffer encrypted HTTP reads, briefly cache read-only portal status snapshots,
  and allow versioned CSS and JavaScript assets to remain in the browser cache.
- Reuse the API client fingerprint within its TLS connection while checking the
  live registry on every request so scope changes and revocation remain immediate.
- Make the Device restarting page enter readiness checks even when a fast reboot
  occurs between offline probes, and cache-bust every automatic reconnect probe.

## 2.0.9 - 2026-08-25

- Resume interrupted universal `.iotuni` uploads from their last committed chunk
  and reclaim only an inactive application generation when staging space is
  otherwise insufficient.
- Report remote syslog delivery failures and recovery in the local Device log,
  with delivery, queue, drop and failure counters in runtime status.
- Remove retired one-shot portal upload routes and extract module presentation
  logic from the runtime composition root.
- Restore linked documentation for every supported module type, correct the
  production N8R8 hardware specification, and record v2.0.8 field qualification.

## 2.0.8 - 2026-08-24

### Changed

- Reordered the remote syslog Transport and Port fields and select port 514
  for UDP or 6514 for TLS when the administrator changes transport, while
  retaining support for a subsequent custom port override.
- Aligned the restart and shutdown controls on the right and emphasized the
  physical-recovery implications of shutdown with a danger action.
- Restart pages now wait until the portal has gone offline, then retry every
  two seconds and return to login only after the restarted portal responds.

### Fixed

- Hide and disable the private-key file control for certificate types that
  require only one or more certificate files.
- Restore shutdown through the hardware deep-sleep capability supplied by the
  matching core firmware release.

### Upgrade order

- The universal `.iotuni` release activates core firmware before the application.
- When installing the component files manually, install the `.iotcore` first and
  the `.iotapp` second so the shutdown capability is available to the portal.

## 2.0.7 - 2026-08-24

### Changed

- Standardized Logging configuration terminology on Device log entries and
  Audit log events, replacing the former system logs and audit events labels.

## 2.0.6 - 2026-08-24

### Changed

- Renamed Maintenance Log viewer to Device log throughout the portal.

## 2.0.5 - 2026-08-24

### Added

- Replaced the Maintenance Factory default tab with Device control, adding
  non-destructive restart and deep-sleep shutdown actions while retaining the
  factory reset workflow in a separate danger section.
- Added audit events for authenticated restart and shutdown requests.

## 2.0.4 - 2026-08-24

### Changed

- Positioned the authenticated user badge before the Sign out button in the
  portal tab banner.

## 2.0.3 - 2026-08-24

### Fixed

- Removed the remaining unsupported `str.capitalize()` calls from
  authenticated portal rendering on MicroPython.
- Extended the MicroPython compatibility gate to reject unsupported
  `capitalize()` and `title()` calls in application bundles.

## 2.0.2 - 2026-08-24

### Added

- Added a dedicated administrator Audit log under Maintenance for portal
  authentication, authorization and mTLS API connection events.
- Added independent remote-syslog forwarding controls for device logs and
  audit events.

### Changed

- Moved routine authenticated portal page requests and API request traces to
  DEBUG-level system logging instead of emitting them as INFO audit messages.

### Fixed

- Restored authenticated portal rendering on MicroPython cores whose compact
  string implementation does not provide `str.isalnum()`.
- Added a MicroPython compatibility check that rejects unsupported
  `str.isalnum()` calls before an application bundle is built.

## 2.0.1 - 2026-08-24

### Fixed

- Stream universal `.iotuni` upgrades directly into the transactional installers
  instead of caching the complete container on constrained device storage.
- Reclaim superseded or unfinishable resumable uploads automatically and reject
  uploads that cannot fit before they consume the remaining filesystem space.

## 2.0.0 - 2026-08-24

IoT-MD v2 is the first production release of the clean-seed ESP32-S3 platform.

### Added

- Secure first-boot provisioning, encrypted credentials, Secure Boot and flash
  encryption.
- Role-aware web portal, MQTT discovery and mandatory-mTLS API v2.
- Modular resource contracts, diagnostics and persistent calibration.
- Signed application, core and universal updates with resumable uploads,
  progress, trial activation, health confirmation and rollback.
- Time-zone/DST scheduling, local-midnight WHES energy reset, audit/health
  history, syslog, ACME and encrypted complete backup/restore.
- Fleet inventory, policy and rollout API consumed by the standalone Home
  Assistant add-on.

### Changed

- Replaced the original monolithic runtime with explicit application, service,
  transport, storage, driver and recovery boundaries.
- Moved Home Assistant fleet management to the standalone
  `IoTMD-Home-Assistant-Addons` repository.

### Fixed

- Corrected portal restart responses, update progress/error propagation,
  configuration restore validation, API error status, permission-aware actions
  and bounded update storage.

## 1.9.0 - 2026-08-22

Final release of the original architecture. v2 devices are provisioned as
clean seeds and do not depend on v1 configuration compatibility.
