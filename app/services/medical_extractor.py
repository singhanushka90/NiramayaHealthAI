import re


def extract_cbc_values(text: str) -> dict:
    # Step 1: Split extracted text into non-empty lines
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # Step 2: Define test names and their possible labels
    tests = {
        "haemoglobin": [
            "haemoglobin",
            "hemoglobin",
        ],
        "total_leucocyte_count": [
            "total leucocyte count",
            "total leukocyte count",
            "tlc",
        ],
        "rbc_count": [
            "rbc count",
            "red blood cell count",
            "red blood cells",
            "total rbcs",
            "total rbc",
        ],
        "platelet_count": [
            "platelet count",
            "platelets",
        ],
        "neutrophils": [
            "neutrophils",
            "neutrophil",
        ],
        "lymphocytes": [
            "lymphocytes",
            "lymphocyte",
        ],
        "eosinophils": [
            "eosinophils",
            "eosinophil",
        ],
        "monocytes": [
            "monocytes",
            "monocyte",
        ],
        "basophils": [
            "basophils",
            "basophil",
        ],
    }

    
    number_pattern = re.compile(
        r"\d[\d,]*(?:\.\d+)?"
    )

    # Step 4: Match reference ranges
    range_pattern = re.compile(
        r"^\s*"
        r"[<>]?\s*\d[\d,]*(?:\.\d+)?"
        r"\s*(?:-|–|—|to)\s*"
        r"[<>]?\s*\d[\d,]*(?:\.\d+)?"
        r"\s*$",
        re.IGNORECASE,
    )

    
    results = {}

    
    for test_name, aliases in tests.items():
        results[test_name] = None

        for i, line in enumerate(lines):

            # Normalize spaces and convert to lowercase
            normalized_line = " ".join(line.lower().split())

            # Check whether the line matches a test label
            matched = any(
                re.fullmatch(
                    re.escape(alias)
                    + r"(?:\s*\([^)]*\))?\s*:?",
                    normalized_line,
                )
                for alias in aliases
            )

            if not matched:
                continue

            # Read the next three non-empty lines
            following_lines = lines[i + 1:i + 4]

            if not following_lines:
                break

            # The first following line should contain the value
            value_match = number_pattern.fullmatch(
                following_lines[0].strip()
            )

            if not value_match:
                break

            value = value_match.group(0).replace(",", "")

            unit = None
            reference_range = None

            
            if len(following_lines) > 1:
                possible_unit = following_lines[1].strip()

                if not range_pattern.fullmatch(possible_unit):
                    unit = possible_unit

            #
            for candidate in following_lines[1:]:
                candidate = candidate.strip()

                if range_pattern.fullmatch(candidate):
                    reference_range = candidate
                    break

            
            results[test_name] = {
                "raw_value": value,
                "unit": unit,
                "reference_range": reference_range,
            }

            break

    return results