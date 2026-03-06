"""CSV output formatting for generated data."""

from typing import Any, Dict, List, Optional

import pandas as pd

from common.types import PatientContext
from medicines.generator import MAX_MEDICINES


def contexts_to_dataframe(
    contexts: List[PatientContext],
    lab_results: Optional[List[Dict[str, Any]]] = None,
) -> pd.DataFrame:
    """Convert PatientContexts and optional lab results to a DataFrame.

    If lab_results is provided, each dict is merged with the context's
    demographic fields. If not, only demographic columns are included.
    """
    rows = []
    for i, ctx in enumerate(contexts):
        row: Dict[str, Any] = {
            "Sex": ctx.sex,
            "Age": ctx.age,
            "State": ctx.state,
            "LifestyleFactors": ctx.lifestyle,
            "Height_cm": ctx.height_cm,
            "Weight_kg": ctx.weight_kg,
            "GivenName": ctx.given_name,
            "FamilyName": ctx.family_name,
            "BirthDate": ctx.birth_date,
            "StreetAddress": ctx.street_address,
            "City": ctx.city,
            "Condition": ctx.condition,
            "SNOMED_Code": ctx.snomed_code,
            "SNOMED_Display": ctx.snomed_display,
        }
        for j in range(MAX_MEDICINES):
            if j < len(ctx.medicines):
                med = ctx.medicines[j]
                row[f"Medicine_{j+1}_Category"] = med.get("category")
                row[f"Medicine_{j+1}_Code"] = med.get("code")
                row[f"Medicine_{j+1}_Display"] = med.get("display")
            else:
                row[f"Medicine_{j+1}_Category"] = None
                row[f"Medicine_{j+1}_Code"] = None
                row[f"Medicine_{j+1}_Display"] = None
        if lab_results and i < len(lab_results):
            lab = lab_results[i]
            for k, v in lab.items():
                if k not in ("Sex", "Age", "Condition"):
                    row[k] = v
        rows.append(row)

    return pd.DataFrame(rows)


def write_csv(df: pd.DataFrame, output_path: str) -> None:
    """Write a DataFrame to CSV."""
    df.to_csv(output_path, index=False)
