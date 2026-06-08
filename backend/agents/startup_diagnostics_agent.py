from __future__ import annotations

import shutil
import socket


class StartupDiagnosticsAgent:
    def run(self) -> list[str]:
        findings: list[str] = []

        if not shutil.which("npm"):
            findings.append("npm no instalado.")

        if not shutil.which("dotnet"):
            findings.append(".NET SDK no instalado.")

        if self.is_port_in_use(8000):
            findings.append("Puerto 8000 ocupado.")

        if self.is_port_in_use(5173):
            findings.append("Puerto 5173 ocupado.")

        return findings

    def is_port_in_use(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) == 0