import os
import glob
from typing import Optional

import pandas as pd
import matplotlib.pyplot as plt

# ---- SETTINGS ----
# If course_data is in the same folder as this script, this will find it:
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(BASE_DIR, "course_data")

FILE_PATTERN = "*_generalqs.csv"
QUESTION_COLUMN = "Question"
COURSE_MEAN_COLUMN = "Course Mean"

# Substring to identify the overall course enjoyment row
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


def get_course_code_from_filename(filename: str) -> str:
    """
    Get something like 'MCB66' or 'HIST1333' from 'HIST1333_generalqs.csv'.
    """
    base = os.path.basename(filename)
    return base.split("_")[0]


def extract_overall_mean(csv_path: str) -> Optional[float]:
    """
    From a generalqs CSV, find the 'Evaluate the course overall' row
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

    # Find the row whose Question mentions the overall course evaluation
    mask = df[QUESTION_COLUMN].astype(str).str.contains(
        OVERALL_ROW_KEYWORD, case=False, na=False, regex=False
    )
    rows = df.loc[mask]

    if rows.empty:
        print(f"No overall-course row found in {csv_path}")
        return None

    row = rows.iloc[0]

    try:
        return float(row[COURSE_MEAN_COLUMN])
    except Exception as e:
        print(f"Could not parse Course Mean in {csv_path}: {e}")
        return None


def compute_enjoyment_consistency(folder: str, pattern: str) -> pd.DataFrame:
    """
    For each department, compute:
        - mean_overall_rating: average 'Evaluate the course overall' mean across its courses
        - std_overall_rating: standard deviation of those course means (consistency)
        - n_courses: number of courses included

    Returns a DataFrame with one row per department.
    """
    paths = glob.glob(os.path.join(folder, pattern))
    print("Found files:", paths)

    records = []

    if not paths:
        print("No files matched the pattern. Check FOLDER and FILE_PATTERN.")
        return pd.DataFrame()

    for path in paths:
        dept = get_department_from_filename(path)
        course_code = get_course_code_from_filename(path)

        overall_mean = extract_overall_mean(path)
        if overall_mean is None:
            continue

        records.append({
            "department": dept,
            "course": course_code,
            "overall_mean": overall_mean,
        })

    if not records:
        print("No overall means found in any files.")
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Group by department and compute mean, std, and count of course means
    dept_stats = (
        df.groupby("department")["overall_mean"]
        .agg(
            mean_overall_rating="mean",
            std_overall_rating="std",
            n_courses="count",
        )
        .reset_index()
    )

    return dept_stats


def plot_enjoyment_bubble_chart(dept_stats: pd.DataFrame) -> None:
    """
    Bubble chart:
      x = department (categorical)
      y = mean overall rating
      bubble size = number of courses (n_courses)
      vertical error bars = std of overall rating
    """
    if dept_stats.empty:
        print("No data to plot.")
        return

    # Sort departments for nicer ordering on x-axis (optional)
    dept_stats = dept_stats.sort_values("department")

    departments = dept_stats["department"].tolist()
    means = dept_stats["mean_overall_rating"].tolist()
    stds = dept_stats["std_overall_rating"].tolist()
    n_courses = dept_stats["n_courses"].tolist()

    x_positions = range(len(departments))

    plt.figure(figsize=(8, 5))

    # Error bars: standard deviation across courses in the department
    plt.errorbar(
        x_positions,
        means,
        yerr=stds,
        fmt="none",      # no marker from errorbar itself
        capsize=5,
        linewidth=1,
    )

    # Bubble sizes: scale n_courses to something visually reasonable
    size_factor = 20 # tweak this if bubbles are too big/small
    sizes = [(n ** 2) * 30 for n in n_courses]

    # Scatter (bubble) plot
    plt.scatter(
        x_positions,
        means,
        alpha=1,
        edgecolors="black",
        linewidths=0.5,
    )

    # Annotate each bubble with number of courses
    #for x, y, n in zip(x_positions, means, n_courses):
        #plt.text(x-0.1, y + 0.05, str(n), ha="center", va="bottom", fontsize=8)

    plt.xticks(x_positions, departments, rotation=45, ha="right")
    plt.ylabel("Mean Overall Course Rating")
    plt.xlabel("Department")
    plt.title("Course Rating by Department")
    plt.ylim(0, 5.5)  # assuming ratings are on a 1–5 scale

    plt.tight_layout()
    plt.savefig("department_course_ratings.png", dpi=300)
    plt.show()

    # To save the figure instead of or in addition to showing:


if __name__ == "__main__":
    dept_stats = compute_enjoyment_consistency(FOLDER, FILE_PATTERN)

    print("\nEnjoyment consistency by department:")
    print(dept_stats)

    # Save for Datawrapper (rows = departments, columns = metrics)
    dept_stats.to_csv("department_enjoyment_consistency.csv", index=False)

    # Bubble chart
    plot_enjoyment_bubble_chart(dept_stats)

    # If you prefer metrics as rows and departments as columns for Datawrapper:
    # dept_stats_for_dw = dept_stats.set_index("department").T
    # dept_stats_for_dw.to_csv("department_enjoyment_consistency_tidy_for_dw.csv")
