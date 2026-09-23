import re


class SeverityNormalizer:

    STANDARD_SEVERITIES = {"critical", "high", "medium", "low", "info"}
    SARIF_LEVEL_MAPPING = {
        "error": "high",
        "warning": "medium",
        "note": "low",
        "none": "info",
    }

    @staticmethod
    def normalize(tool: str, level: str, message: str = "") -> str:

        tool = tool.lower()
        normalized_level = (level or "none").lower()

        # Some producers put their native severity directly in the SARIF level.
        if normalized_level in SeverityNormalizer.STANDARD_SEVERITIES:
            return normalized_level

        if "trivy" in tool:

            match = re.search(
                r"Severity:\s*(CRITICAL|HIGH|MEDIUM|LOW|UNKNOWN)",
                message,
                re.IGNORECASE
            )

            if match:
                return match.group(1).lower()

            return SeverityNormalizer.SARIF_LEVEL_MAPPING.get(normalized_level, "info")

        if "gitleaks" in tool or "trufflehog" in tool:

            return "critical"

        if "semgrep" in tool:

            mapping = {
                "error": "high",
                "warning": "medium",
                "info": "low"
            }

            return mapping.get(normalized_level, "info")

        if "snyk" in tool:

            mapping = {
                "critical": "critical",
                "high": "high",
                "medium": "medium",
                "low": "low"
            }

            return mapping.get(normalized_level, "info")

        # KICS and other SARIF producers use the standard SARIF levels rather
        # than vulnerability severities. Never persist those raw values.
        return SeverityNormalizer.SARIF_LEVEL_MAPPING.get(normalized_level, "info")
