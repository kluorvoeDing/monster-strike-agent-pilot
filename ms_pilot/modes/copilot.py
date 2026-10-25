from typing import Any, Dict, List, Optional
from ..core.client import iPhoneClient
from ..core.vision import profile_team_on_screen
from .fast_farm import run_fast_farm_batch


class CoPilotSession:
    """
    Mode 4: Human-in-the-Loop Co-Pilot Mode.
    - Eliminates LLM team hallucinations by visually profiling the 4 character cards on screen.
    - Allows live natural-language tactical overrides (e.g. prioritizing a specific slot or holding SS).
    """

    def __init__(
        self,
        client: iPhoneClient,
        prefer_slot: Optional[int] = None,
        hold_ss_until_boss: bool = True,
        enable_extra_chest: bool = True,
    ):
        self.client = client
        self.prefer_slot = prefer_slot
        self.hold_ss_until_boss = hold_ss_until_boss
        self.enable_extra_chest = enable_extra_chest
        self.team_profile: List[Dict[str, Any]] = []

    def inspect_and_record_team(self) -> List[Dict[str, Any]]:
        """Capture current screen and build a factual visual profile of the 4 party slots."""
        items = self.client.get_ocr_items()
        self.team_profile = profile_team_on_screen(self.client, items)
        print("\n=== [CO-PILOT VISUAL TEAM INTROSPECTION] ===")
        for slot in self.team_profile:
            print(
                f"  Slot {slot['slot']} (x={slot['x']:.2f}): "
                f"Color={slot['dominant_color']} | OCR={slot['labels']}"
            )
        print("============================================\n")
        return self.team_profile

    def build_role_weights(self) -> Dict[int, float]:
        weights = {1: 0.7, 2: 1.5, 3: 1.5, 4: 1.3}
        if self.prefer_slot in (1, 2, 3, 4):
            weights[self.prefer_slot] = 2.5
        return weights

    def run(self, quest_keywords: Optional[List[str]] = None, runs: int = 1) -> Dict[str, Any]:
        self.inspect_and_record_team()
        return run_fast_farm_batch(
            self.client,
            quest_keywords=quest_keywords,
            num_runs=runs,
            enable_extra_chest=self.enable_extra_chest,
            role_weights=self.build_role_weights(),
        )
