import re


class SarifToolRegistry:
    """Canonical names for common DevSecOps tools that emit SARIF 2.x."""

    ALIASES = {
        "trivy": "Trivy",
        "aquasecurity trivy": "Trivy",
        "semgrep": "Semgrep",
        "semgrep pro": "Semgrep",
        "codeql": "GitHub CodeQL",
        "github codeql": "GitHub CodeQL",
        "github advanced security": "GitHub Advanced Security",
        "snyk": "Snyk",
        "snyk code": "Snyk Code",
        "snyk open source": "Snyk Open Source",
        "checkmarx": "Checkmarx",
        "checkmarx sast": "Checkmarx SAST",
        "checkmarx one": "Checkmarx One",
        "fortify": "Fortify",
        "fortify sca": "Fortify SCA",
        "sonarqube": "SonarQube",
        "sonar": "SonarQube",
        "gitleaks": "Gitleaks",
        "trufflehog": "TruffleHog",
        "grype": "Grype",
        "anchore grype": "Grype",
        "checkov": "Checkov",
        "kics": "KICS",
        "tfsec": "tfsec",
        "terrascan": "Terrascan",
        "mend": "Mend",
        "whitesource": "Mend",
        "owasp zap": "OWASP ZAP",
        "zap": "OWASP ZAP",
        "bandit": "Bandit",
        "brakeman": "Brakeman",
        "eslint": "ESLint",
        "microsoft.security.devops": "Microsoft Security DevOps",
    }

    @classmethod
    def canonical_name(cls, name: str | None) -> str:
        raw = (name or "").strip()
        if not raw:
            return "Unknown SARIF Tool"
        normalized = re.sub(r"[^a-z0-9.]+", " ", raw.lower()).strip()
        if normalized in cls.ALIASES:
            return cls.ALIASES[normalized]
        for alias, canonical in cls.ALIASES.items():
            if alias in normalized:
                return canonical
        return raw
