import os
import glob
import pandas as pd
from typing import Optional

# ---- SETTINGS ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(BASE_DIR, "course_data")  # folder next to this script
FILE_PATTERN = "*_generalqs.csv"
QUESTION_COLUMN = "Question"
COURSE_MEAN_COLUMN = "Course Mean"

ASSIGNMENTS_ROW_KEYWORD = "Assignments"
OVERALL_ROW_KEYWORD = "Evaluate the course overall"
# -------------------


def get_department_from_filename(filename: str) -> str:
    """
    Extract department from a filename like 'MCB66_generalqs.csv' -> 'MCB'
    by taking leading letters of the first part.
    """
    base = os.path.basename(filename)
    first_part = base.split("_")[0]   # e.g. "MCB66"
    dept_chars = []
    for ch in first_part:
        if ch.isalpha():
            dept_chars.append(ch)
        else:
            break
    return "".join(dept_chars)


def extract_row_mean(csv_path: str, keyword: str) -> Optional[float]:
    """
    From a generalqs CSV, find the row whose Question contains `keyword`
    and return its Course Mean.
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Could not read {csv_path}: {e}")
        return None

    if QUESTION_COLUMN not in df.columns or COURSE_MEAN_COLUMN not in df.columns:
        print(f"Missing expected columns in {csv_path}")
        return None

    mask = df[QUESTION_COLUMN].astype(str).str.contains(
        keyword, case=False, na=False, regex=False
    )
    rows = df.loc[mask]

    if rows.empty:
        print(f"No row containing '{keyword}' found in {csv_path}")
        return None

    row = rows.iloc[0]

    try:
        return float(row[COURSE_MEAN_COLUMN])
    except Exception as e:
        print(f"Could not parse Course Mean in {csv_path}: {e}")
        return None


def extract_assignment_mean(csv_path: str) -> Optional[float]:
    return extract_row_mean(csv_path, ASSIGNMENTS_ROW_KEYWORD)


def extract_overall_mean(csv_path: str) -> Optional[float]:
    return extract_row_mean(csv_path, OVERALL_ROW_KEYWORD)


def compute_department_assignment_means(folder: str, pattern: str) -> pd.DataFrame:
    """
    Returns a DataFrame shaped for Datawrapper:

        rows  = metrics (mean_assignment_satisfaction, ...)
        cols  = departments (HIST, MCB, ...)

    so you can drop it straight into a chart.
    """
    paths = glob.glob(os.path.join(folder, pattern))
    print("Found files:", paths)

    records = []

    if not paths:
        print("No files matched the pattern. Check FOLDER and FILE_PATTERN.")
        return pd.DataFrame()

    for path in paths:
        dept = get_department_from_filename(path)
        course_code = os.path.basename(path).split("_")[0]  # e.g. "MCB66"

        assignment_mean = extract_assignment_mean(path)
        overall_mean = extract_overall_mean(path)

        if assignment_mean is None or overall_mean is None:
            continue

        records.append({
            "department": dept,
            "course": course_code,
            "assignment_mean": assignment_mean,
            "overall_mean": overall_mean,
            "assignment_minus_overall": assignment_mean - overall_mean,
        })

    if not records:
        print("No assignment/overall means found in any files.")
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Department-level averages (departments as index, metrics as columns)
    dept_means = (
        df.groupby("department")[["assignment_mean", "overall_mean", "assignment_minus_overall"]]
        .mean()
        .rename(columns={
            "assignment_mean": "mean_assignment_satisfaction",
            "overall_mean": "mean_overall_satisfaction",
            "assignment_minus_overall": "mean_assignment_minus_overall",
        })
    )

    # Now transpose so:
    #   rows  = metrics
    #   cols  = departments
    dept_means_for_datawrapper = dept_means.T

    return dept_means_for_datawrapper


if __name__ == "__main__":
    dept_means = compute_department_assignment_means(FOLDER, FILE_PATTERN)
    print("\nTable shaped for Datawrapper (rows = metrics, columns = departments):")
    print(dept_means)

    # To save for upload to Datawrapper:
    dept_means.to_csv("department_assignment_vs_overall_means.csv")
