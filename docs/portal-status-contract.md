# Portal status contract

- Blue: work requested/in progress. Acceptance is not completion.
- Green: a confirmed successful outcome.
- Amber: incomplete/recoverable state, intentional cancellation, or interrupted
  status reads. Retained data must not still be described as live.
- Red: a rejected action or failed operation. Never infer success solely from
  HTTP 200: an explicit `ok: false` is an error.

Use `portalStatus` for dynamic notices and `render_notice` for static notices.
Errors use `role=alert`/assertive announcements; warnings and progress use
`role=status`/polite announcements. Text is escaped or assigned with textContent.
Errors/warnings occupy a full row above action controls, not alongside buttons.
Keep field validation next to the field as well as any operation-level notice.

Read failures retain the last valid data and show a warning until a successful
refresh. GETs may retry with bounded timeouts; mutations must not be replayed
automatically. Do not reset form defaults after a rejected write.

Staging cancellation is cooperative. It revokes pending policy commands and
waits for the writer to stop before removing staging artifacts. It must not
interrupt activation/trial, or cancel another release using an old policy.
Management shows cancelling until it reads a matching acknowledgement, while
an uncertain mutation remains uncertain rather than being labelled successful.
