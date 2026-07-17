"""
Mapping between FILE_A and FILE_B
"""
import pandas as pd

FILE_A = "results.csv"
FILE_B = "job_history.csv"

OUTPUT_MATCHED = "matched.csv"
OUTPUT_UNMATCHED = "unmatched.csv"

df_a = pd.read_csv(FILE_A)
df_b = pd.read_csv(FILE_B)

df_a["Workspace"] = df_a["Workspace"].astype(str).str.strip()
df_a["Job_Name"] = df_a["Job_Name"].astype(str).str.strip()

df_b["Workspace"] = df_b["Workspace"].astype(str).str.strip()
df_b["Job_Name"] = df_b["Job_Name"].astype(str).str.strip()
df_b["SubmittedBy"] = df_b["SubmittedBy"].astype(str).str.strip()

df_b["Submitted"] = pd.to_datetime(
    df_b["Submitted"], format="%m/%d/%Y %I:%M:%S %p", errors="coerce"
)

df_b_latest = df_b.sort_values("Submitted").drop_duplicates(
    subset=["Workspace", "Job_Name"], keep="last"
)

result = df_a.merge(
    df_b_latest[["Workspace", "Job_Name", "SubmittedBy", "Submitted"]],
    on=["Workspace", "Job_Name"],
    how="left",
    indicator=True,
)

matched = result[result["_merge"] == "both"].copy()
unmatched = result[result["_merge"] == "left_only"].copy()

matched.drop(columns=["_merge"], inplace=True)
unmatched.drop(columns=["_merge"], inplace=True)

matched.to_csv(OUTPUT_MATCHED, index=False, encoding="utf-8-sig")

unmatched.to_csv(OUTPUT_UNMATCHED, index=False, encoding="utf-8-sig")


print(f"File A Rows        : {len(df_a):,}")
print(f"File B Rows        : {len(df_b):,}")
print(f"File B Unique Keys : {len(df_b_latest):,}")
print(f"Matched            : {len(matched):,}")
print(f"Unmatched          : {len(unmatched):,}")
print(f"Total              : {len(matched) + len(unmatched):,}")

print(f"Matched File     : {OUTPUT_MATCHED}")
print(f"Unmatched File   : {OUTPUT_UNMATCHED}")
