
import uuid
import datetime
from typing import List, Dict, Optional
from core.memory.symbolic_lexicon import symbolic_lexicon

class MemoryPulse:
    def __init__(self, signal: str, tags: List[str], timestamp=None):
        self.id = str(uuid.uuid4())
        self.signal = signal
        self.tags = tags
        self.timestamp = timestamp or datetime.datetime.utcnow()

    def __repr__(self):
        return f"<Pulse {self.signal[:30]}... | Tags: {self.tags}>"

class NodeAnchor:
    def __init__(self, node_id: str, content: str, category: str):
        self.node_id = node_id
        self.content = content
        self.category = category

    def __repr__(self):
        return f"<Anchor {self.node_id} | {self.category}>"

class HarmonicReconciler:
    def __init__(self):
        self.pulses: Dict[str, MemoryPulse] = {}
        self.anchors: Dict[str, NodeAnchor] = {}
        self.bridges: Dict[str, str] = {}

    def register_pulse(self, signal: str, tags: List[str]) -> str:
        pulse = MemoryPulse(signal, tags)
        self.pulses[pulse.id] = pulse
        return pulse.id

    def register_anchor(self, node_id: str, content: str, category: str):
        anchor = NodeAnchor(node_id, content, category)
        self.anchors[node_id] = anchor

    def reconcile_all(self):
        for pid, pulse in self.pulses.items():
            for aid, anchor in self.anchors.items():
                anchor_text = anchor.content.lower()
                category_tag = anchor.category.lower()

                # Collect expanded symbolic tags
                expanded_tags = set(pulse.tags)
                for tag in pulse.tags:
                    expanded_tags.update(symbolic_lexicon.get(tag, []))

                # Match logic
                if (
                    any(tag in anchor_text for tag in expanded_tags)
                    or category_tag in expanded_tags
                ):
                    self.bridges[pid] = aid
                    break

    def fetch_bridge(self, pulse_id: str) -> Optional[NodeAnchor]:
        anchor_id = self.bridges.get(pulse_id)
        return self.anchors.get(anchor_id, None)

    def debug_state(self):
        return {
            "pulses": list(self.pulses.values()),
            "anchors": list(self.anchors.values()),
            "bridges": self.bridges
        }
