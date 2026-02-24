"""Shared data types for the banksia pipeline."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PatientContext:
    """Demographic and lifestyle context for a single synthetic patient.

    Population module produces these; downstream modules (laboratory, etc.) consume them.
    """
    sex: str
    age: int
    lifestyle: List[str] = field(default_factory=list)
    condition: str = "Healthy"
    snomed_code: Optional[str] = None
    snomed_display: Optional[str] = None
    state: Optional[str] = None
    height_cm: Optional[int] = None
    weight_kg: Optional[int] = None
    medicines: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        self.sex = self.sex.lower()
