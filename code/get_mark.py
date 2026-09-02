import pandas as pd
from datetime import date
from pathlib import Path

# Load data
df = pd.read_csv("ects_grade_scales_by_country.csv")
df_student = pd.read_csv("student_grades.csv")

# Output folder
output_dir = Path("voti")
output_dir.mkdir(exist_ok=True)

# UNIBO ECTS → Italian mapping (A.A. 2024-25)
italian_mapping = {
    "A": {"IT_Min": 31, "IT_Max": 31},
    "B": {"IT_Min": 29, "IT_Max": 30},
    "C": {"IT_Min": 26, "IT_Max": 28},
    "D": {"IT_Min": 21, "IT_Max": 25},
    "E": {"IT_Min": 18, "IT_Max": 20},
}


def get_ects_and_scaled_grade(
    country_name: str,
    grade_value: float,
    comment: str,
    esame_estero: str,
    esame_unibo: str,
):
    subset = df[df["Country"].str.lower() == country_name.lower()].copy()
    if subset.empty:
        raise ValueError(f"No ECTS data found for country: {country_name}")

    subset = subset.dropna(subset=["Min", "Max"])

    asc_scale = subset["Min"].mean() < subset["Max"].mean()

    e_min = subset.loc[subset["ECTS Grade"] == "E", "Min"].iloc[0]
    a_max = subset.loc[subset["ECTS Grade"] == "A", "Max"].iloc[0]

    ects_grade = None
    ects_min = None
    ects_max = None

    for _, row in subset.iterrows():
        min_val, max_val = row["Min"], row["Max"]

        if asc_scale and min_val <= grade_value <= max_val:
            ects_grade = row["ECTS Grade"]
            ects_min, ects_max = min_val, max_val
            break

        if not asc_scale and max_val <= grade_value <= min_val:
            ects_grade = row["ECTS Grade"]
            ects_min, ects_max = min_val, max_val
            break

    if asc_scale:
        grade_clipped = min(max(grade_value, e_min), a_max)
        scaled_linear = 18 + (grade_clipped - e_min) / (a_max - e_min) * (31 - 18)
    else:
        grade_clipped = max(min(grade_value, e_min), a_max)
        scaled_linear = 18 + (e_min - grade_clipped) / (e_min - a_max) * (31 - 18)

    italian_equiv = italian_mapping.get(ects_grade, {"IT_Min": None, "IT_Max": None})

    if ects_grade and ects_min != ects_max:
        scaled_ects = italian_equiv["IT_Min"] + (
            (grade_clipped - ects_min)
            / (ects_max - ects_min)
            * (italian_equiv["IT_Max"] - italian_equiv["IT_Min"])
        )
    else:
        scaled_ects = italian_equiv["IT_Max"]

    return {
        "Country": country_name,
        "Ext min": ects_min,
        "Ext max": ects_max,
        "ITA Min": italian_equiv["IT_Min"],
        "ITA Max": italian_equiv["IT_Max"],
        "Scaled Linear (18-31)": round(scaled_linear, 2),
        "Comment": comment,
        "Esame estero": esame_estero,
        "Esame UniBO": esame_unibo,
        "Voto estero": grade_value,
        "Conversione ECTS": ects_grade,
        "Voto UniBO": (None if scaled_ects is None else round(scaled_ects)),
    }


# === Process per student ===
for (student, generate), student_df in df_student.groupby(["Student", "Generate"]):
    if generate:
        results = student_df.apply(
            lambda r: get_ects_and_scaled_grade(
                r["Country"],
                r["Grade"],
                r["Comment"],
                r["Esame estero"],
                r["Esame UniBO"],
            ),
            axis=1,
        )

        results_df = pd.DataFrame(results.tolist())
        results_df.insert(0, "Student", student)

        # Save one Excel per student
        output_file = (
            output_dir
            / f"{date.today()}-{student}-{'_'.join(sorted(student_df['Country'].unique()))}.xlsx"
        )
        results_df.to_excel(output_file, index=False)
        # Print
        print(f"\n=== {student} ===")
        print(
            results_df[
                [
                    "Esame estero",
                    "Esame UniBO",
                    "Conversione ECTS",
                    "Voto UniBO",
                ]
            ].to_markdown(index=False)
        )
