import re
import pdfplumber
import pandas as pd

# Path to the uploaded PDF
pdf_path = "SchedePaeseConversioneVotiEsteri.pdf"

data = []
current_country = None

with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue

        # Detect country names (all caps, sometimes with spaces)
        for line in text.splitlines():
            if re.match(r"^[A-ZÀ-Ü\s\’\-]+$", line.strip()) and len(line.strip()) > 3:
                current_country = line.strip().title()  # normalize name
                continue

            # Extract rows of ECTS tables
            match = re.match(r"^(A|B|C|D|E)\s+([\d,\.]+)\s+([\d,\.]+)", line.strip())
            if match and current_country:
                grade, min_val, max_val = match.groups()
                # Normalize decimals (commas → dots)
                min_val = float(min_val.replace(",", "."))
                max_val = float(max_val.replace(",", "."))
                data.append(
                    {
                        "Country": current_country,
                        "ECTS Grade": grade,
                        "Min": min_val,
                        "Max": max_val,
                    }
                )

# Convert to DataFrame
df = pd.DataFrame(data)

# Save to CSV for convenience
df.to_csv("ects_grade_scales_by_country.csv", index=False)

print("Extracted rows:", len(df))
print("Extracted countries:", df["Country"].nunique())
print(df.head())
