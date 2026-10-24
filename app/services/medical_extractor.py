import re


def extract_cbc_values(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    tests = {
        "haemoglobin": ["haemoglobin", "hemoglobin"],
        "total_leucocyte_count": [
            "total leucocyte count",
            "total leukocyte count",
        ],
        "platelet_count": ["platelet count"],
        "rbc_count": ["rbc count", "red blood cell count"],
    }

    results = {}

    for test_name, aliases in tests.items():
        results[test_name] = None

        for i, line in enumerate(lines):
            normalized_line = line.lower().strip()

            if not any(re.fullmatch(re.escape(alias) + r"(?:\s*\([^)]*\))?",normalized_line)
                       for alias in aliases):
                continue

            # Look at the next lines for the numeric value and unit
            following_lines = lines[i + 1:i + 4]

            if not following_lines:
                break

            value_match = re.fullmatch(
                r"(\d[\d,]*(?:\.\d+)?)",
                following_lines[0]
            )

            if not value_match:
                break

            value = value_match.group(1)
            unit = following_lines[1] if len(following_lines) > 1 else None

            results[test_name] = {
                "raw_value": value,
                "unit": unit
            }
            break

    return results