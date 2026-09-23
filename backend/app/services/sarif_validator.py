import json
from app.services.sarif_tools import SarifToolRegistry


class SarifValidator:

    @staticmethod
    def validate(file_bytes: bytes) -> dict:

        try:
            data = json.loads(file_bytes)
        except Exception:
            raise ValueError("Invalid JSON")

        if not isinstance(data, dict) or not isinstance(data.get("runs"), list) or not data["runs"]:
            raise ValueError("Invalid SARIF file")

        version = str(data.get("version", ""))
        if version and not version.startswith("2."):
            raise ValueError("Unsupported SARIF version")

        return data

    @staticmethod
    def detect_tool(data: dict) -> str:

        try:
            name = data["runs"][0]["tool"]["driver"]["name"]
            return SarifToolRegistry.canonical_name(name)
        except Exception:
            return "Unknown SARIF Tool"
