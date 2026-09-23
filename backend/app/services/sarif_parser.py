from app.models.finding import Finding
from app.utils.severity import SeverityNormalizer
from uuid import UUID
from urllib.parse import unquote
from hashlib import md5


def text(value: dict | None) -> str:
    value = value or {}
    return value.get("text") or value.get("markdown") or ""


def severity_value(result: dict, rule: dict) -> str:
    result_properties = result.get("properties", {}) or {}
    rule_properties = rule.get("properties", {}) or {}
    value = (
        result_properties.get("severity")
        or result_properties.get("problem.severity")
        or rule_properties.get("severity")
        or rule_properties.get("problem.severity")
    )
    if value:
        return str(value)
    score = result_properties.get("security-severity", rule_properties.get("security-severity"))
    try:
        score = float(score)
        if score >= 9: return "critical"
        if score >= 7: return "high"
        if score >= 4: return "medium"
        if score > 0: return "low"
    except (TypeError, ValueError):
        pass
    return result.get("level") or rule.get("defaultConfiguration", {}).get("level") or "warning"


def classification_tags(result: dict, rule: dict) -> tuple[str | None, str | None]:
    rule_properties = rule.get("properties", {}) or {}
    result_properties = result.get("properties", {}) or {}

    def as_list(value) -> list[str]:
        if not value:
            return []
        return [value] if isinstance(value, str) else list(value)

    cwe_values = as_list(rule_properties.get("cwe")) or as_list(result_properties.get("cwe"))
    owasp_values = as_list(rule_properties.get("owasp")) or as_list(result_properties.get("owasp"))

    if not cwe_values or not owasp_values:
        tags = as_list(rule_properties.get("tags")) + as_list(result_properties.get("tags"))
        for tag in tags:
            normalized = str(tag).strip()
            if not cwe_values and normalized.upper().startswith("CWE"):
                cwe_values.append(normalized)
            elif not owasp_values and normalized.upper().startswith("OWASP"):
                owasp_values.append(normalized)

    def dedupe_join(values: list[str]) -> str | None:
        seen = list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))
        return ", ".join(seen) if seen else None

    return dedupe_join(cwe_values), dedupe_join(owasp_values)


def extract_fingerprint(result: dict) -> str | None:
    """Pick a stable fingerprint for cross-scan dedup.

    Fingerprint objects can carry several algorithms side by side (e.g. Snyk's
    `identity` vs its code-context-based `0`/`1` hashes), and dict key order in
    the source JSON isn't guaranteed to be consistent between scans of the same
    code -- picking "whichever value comes first" silently breaks dedup. Prefer
    each tool's known-stable key explicitly; only fall back to positional pick
    for tools/keys we don't recognize.
    """
    partial = result.get("partialFingerprints") or {}
    if partial:
        for key in ("matchBasedId/v1",):
            if key in partial:
                return str(partial[key])
        return str(next(iter(partial.values())))

    fingerprints = result.get("fingerprints") or {}
    if fingerprints:
        for key in ("snyk/asset/finding/v1", "identity"):
            if key in fingerprints:
                return str(fingerprints[key])
        return str(next(iter(fingerprints.values())))

    return None


def result_identity(
    rule_id: str,
    fingerprint: str | None,
    file_path: str,
    line_number: int | None,
    message: str,
) -> str:
    if fingerprint and fingerprint.strip():
        identity = f"{rule_id.strip().lower()}|fp|{fingerprint.strip().lower()}"
    else:
        identity = (
            f"{rule_id.strip().lower()}|src|{file_path.strip().lower()}|"
            f"{line_number or ''}|{message.strip().lower()}"
        )

    return md5(identity.encode("utf-8"), usedforsecurity=False).hexdigest()


class SarifParser:

    @staticmethod
    def parse(scan_id: UUID, sarif: dict) -> list[Finding]:

        findings = []

        runs = sarif.get("runs", [])

        for run in runs:

            rules = {}

            tool = run.get("tool", {})
            driver = tool.get("driver", {})

            tool_name = driver.get("name", "")

            rule_list = list(driver.get("rules", []))
            for extension in tool.get("extensions", []):
                rule_list.extend(extension.get("rules", []))
            for rule in rule_list:
                rules[rule.get("id")] = rule

            for result in run.get("results", []):

                rule_index = result.get("ruleIndex")
                indexed_rule = rule_list[rule_index] if isinstance(rule_index, int) and 0 <= rule_index < len(rule_list) else {}
                rule_id = result.get("ruleId") or indexed_rule.get("id") or "Unknown"

                rule = rules.get(rule_id, indexed_rule)

                title = (
                    text(rule.get("shortDescription"))
                    or text(rule.get("fullDescription"))
                    or rule.get("name")
                    or rule_id
                )

                message = (
                    text(result.get("message"))
                    or ""
                )

                level = (
                    severity_value(result, rule)
                )

                severity = SeverityNormalizer.normalize(
                    tool=tool_name,
                    level=level,
                    message=message
                )

                file_path = ""
                line_number = None
                end_line = None
                start_column = None
                end_column = None
                snippet = None

                try:
                    location = result["locations"][0]["physicalLocation"]

                    file_path = unquote(location["artifactLocation"].get("uri", ""))

                    region = location["region"]
                    line_number = region.get("startLine")
                    end_line = region.get("endLine")
                    start_column = region.get("startColumn")
                    end_column = region.get("endColumn")
                    snippet = (region.get("snippet") or {}).get("text") or None

                except Exception:
                    pass

                cwe, owasp = classification_tags(result, rule)
                help_uri = rule.get("helpUri")

                try:
                    fingerprint = extract_fingerprint(result)
                except Exception:
                    fingerprint = None

                findings.append(
                    Finding(
                        scan_id=scan_id,
                        rule_id=rule_id,
                        title=title,
                        severity=severity,
                        message=message,
                        file_path=file_path,
                        line_number=line_number,
                        end_line=end_line,
                        start_column=start_column,
                        end_column=end_column,
                        snippet=snippet,
                        cwe=cwe,
                        owasp=owasp,
                        help_uri=help_uri,
                        fingerprint=fingerprint,
                        dedup_key=result_identity(
                            rule_id,
                            fingerprint,
                            file_path,
                            line_number,
                            message,
                        ),
                    )
                )

        return findings
