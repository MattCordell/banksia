"""CSV output formatting for generated data."""

from typing import Any, Dict, List, Optional

import pandas as pd

from common.types import PatientContext


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
            "Condition": ctx.condition,
            "SNOMED_Code": ctx.snomed_code,
            "SNOMED_Display": ctx.snomed_display,
        }
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
