"""Host-only transactional NVS substitute, including failed commit injection."""
class MemoryNamespace:
    def __init__(self):
        self.generation = 0
        self.payload = b''
        self.fail = False
        self.closes = 0

    def snapshot(self):
        return self.generation, self.payload

    def commit(self, generation, payload):
        if self.fail:
            raise OSError('injected NVS write failure')
        if generation != self.generation:
            raise RuntimeError('generation conflict')
        self.generation += 1
        self.payload = bytes(payload)
        return self.generation

    def close(self):
        self.closes += 1
