# hecate.py
class Hecate:
    def __init__(self):
        self.permissions = {}

    def grant(self, entity, resource):
        self.permissions.setdefault(entity, []).append(resource)

    def revoke(self, entity, resource):
        if entity in self.permissions and resource in self.permissions[entity]:
            self.permissions[entity].remove(resource)

    def can_access(self, entity, resource):
        return resource in self.permissions.get(entity, [])
