"""Cooperative staging cancellation; activation is deliberately not reversible."""


class UpdateCancelled(ValueError):
    """An intentional operator cancellation, not a failed upgrade."""


class UpdateCancellation:
    def __init__(self, upload, downloads, fleet, components, orchestrator, telemetry, operations=None):
        self.upload = upload
        self.downloads = downloads
        self.fleet = fleet
        self.components = components
        self.orchestrator = orchestrator
        self.telemetry = telemetry
        self.operations = operations

    def status(self):
        requested = self.fleet.state.get('update_cancelled')
        if not requested:
            return {'status': 'idle'}
        busy = (self.upload.installing() or self.downloads.download_active() or
                any(item.update_status().get('status') == 'ready' for item in self.components))
        return dict(requested, status='cancelling' if busy else 'cancelled')

    def finalize(self):
        """Resume cleanup from durable intent on the worker, never on a GET."""
        if self.operations:
            active = self.operations.active()
            if active and active['state'] == 'cancelling' and not (
                    self.upload.installing() or self.downloads.download_active()):
                self.upload.discard_staged()
                self.orchestrator.clear()
                self.telemetry.progress = {}
        return self.status()

    def cancel(self, request=None):
        request = request or {}
        if not isinstance(request, dict):
            raise ValueError('update cancellation must be an object')
        operation = None
        if self.operations:
            operation = self.operations.active()
            identifier = request.get('update_operation_id')
            if identifier:
                result = self.operations.snapshot(identifier)
                if result['state'] in ('complete', 'failed', 'cancelled', 'interrupted'):
                    return {'status': result['state'], 'update_operation_id': identifier}
                if not operation or operation['id'] != identifier:
                    raise ValueError('The requested operation is not the active update')
                if (int(request.get('release_sequence', 0)) != operation['release_sequence'] or
                        request.get('release_type') != operation['release_type']):
                    raise ValueError('Cancellation release does not match the requested operation')
            elif request and operation:
                raise ValueError('Cancellation requires the exact update operation ID')
            if operation and operation['state'] == 'installing':
                raise ValueError('Installation has begun; cancellation is no longer safe')
        states = [component.update_status() for component in self.components]
        if (any(item.get('status') in ('activating', 'trial', 'committing') for item in states)
                or self.orchestrator.load().get('status') == 'activating'):
            raise ValueError('Installation has begun; cancellation is no longer safe. Wait for confirmation or use rollback afterwards.')
        sequence = int(request.get('release_sequence', 0) or 0)
        kind = str(request.get('release_type', '') or '')
        if sequence:
            if self.upload.installing():
                raise ValueError('A browser upload is staging on this device; cancel it from the device portal')
            live = self.telemetry.progress
            if self.downloads.download_active() and (
                    int(live.get('release_sequence', 0) or 0) != sequence or live.get('type') != kind):
                raise ValueError('The requested release is not this device’s current update')
            if any(item.get('status') == 'ready' and
                   int(item.get('release_sequence', 0) or 0) != sequence for item in states):
                raise ValueError('A different release is staged; cancel it from the device portal')
            candidates = list((self.fleet.state.get('policy') or {}).get('commands', ()))
            candidates += [dict(item, release_type=item.get('type', component_type))
                           for item, component_type in zip(states, ('application', 'firmware', 'universal'))]
            candidates.append(dict(self.telemetry.progress,
                                   release_type=self.telemetry.progress.get('type', '')))
            if not any(int(item.get('release_sequence', 0) or 0) == sequence and
                       item.get('release_type') == kind for item in candidates):
                raise ValueError('The requested release is not this device’s current update')
        # Persist revocation before signalling the running coroutine. A captured
        # command list must not activate a staged release after cancellation.
        if operation:
            self.operations.transition('cancelling', detail='Cancellation requested; awaiting safe staging stop')
        self.fleet.cancel_updates(sequence, kind)
        self.upload.cancel()
        if self.downloads.download_active():
            self.downloads.discard_update(self.upload.discard_staged)
        if not self.upload.installing() and not self.downloads.download_active():
            self.upload.discard_staged()
            self.orchestrator.clear()
            self.telemetry.progress = {}
        return self.status()
