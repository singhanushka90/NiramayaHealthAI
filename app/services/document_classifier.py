import re

DOCUMENT_RULES = {
    "cbc_hematology": {
        "hemoglobin": 2,
        "wbc": 2,
        "rbc": 2,
        "platelet": 2,
        "haemoglobin":2,
        "platelet count":2,
        "haematocrit":2,
        "complete blood count":3,
        "total leucocyte count":3,
        "total leukocyte count":3,
        "differential leucocyte count":3,
        "hematocrit": 2,
    },

    "prescription": {
        "rx": 3,
        "tablet": 2,
        "capsule": 2,
        "dosage": 2,
        "frequency": 2,
    },

    "discharge_summary": {
        "discharge summary": 3,
        "diagnosis": 2,
        "hospital course": 2,
        "medication": 1,
    },

    "radiology": {
        "x-ray": 3,
        "mri": 3,
        "ct": 3,
        "findings": 2,
        "impression": 2,
    },

    "general_lab": {
        "reference range": 2,
        "laboratory": 2,
        "blood test": 2,
        "lab report": 3,
    },
}



def classify_document_by_rules(text: str):

    text = text.lower()

    scores = {}
    matched_rules = {}

    for document_type, rules in DOCUMENT_RULES.items():

        score = 0
        matched = []
        matched_spans = []

        sorted_rules = sorted(
            rules.items(),
            key=lambda item: len(item[0]),
            reverse=True
        )

        for keyword, weight in sorted_rules:

            pattern = r"\b" + re.escape(keyword) + r"\b"

            match = re.search(pattern, text)

            if not match:
                continue

          
            # with an already matched longer phrase
            overlaps = False

            for start, end in matched_spans:
                if match.start() < end and match.end() > start:
                    overlaps = True
                    break

            if overlaps:
                continue

            score += weight
            matched.append(keyword)

            matched_spans.append(
                (match.start(), match.end())
            )

        scores[document_type] = score
        matched_rules[document_type] = matched

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score < 3:
        return {
            "document_type": "unknown",
            "score": best_score,
            "matched_rules": []
        }

    return {
        "document_type": best_type,
        "score": best_score,
        "matched_rules": matched_rules[best_type]
    }