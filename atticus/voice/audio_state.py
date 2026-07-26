"""Runtime voice input arming (kill switch for mic / wake flows)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VoiceSessionState:
    """The Speaker can disarm all microphone capture without editing YAML."""

    voice_input_armed: bool = field(default=True)

    def disarm(self) -> None:
        self.voice_input_armed = False

    def arm(self) -> None:
        self.voice_input_armed = True
