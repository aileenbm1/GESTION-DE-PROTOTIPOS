import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

class ProjectValidationAgent:

    def run(self, project) -> list[str]:

        findings: list[str] = []

        if project.angular_path:
            findings.extend(
                self.validate_angular(
                    Path(project.angular_path)
                )
            )

        if project.backend_path:
            findings.extend(
                self.validate_dotnet(
                    Path(project.backend_path)
                )
            )

        return findings

    def validate_angular(
        self,
        path: Path,
    ) -> list[str]:

        findings: list[str] = []

        try:

            # Instalar dependencias
            install = subprocess.run(
                ["npm", "install"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if install.returncode != 0:

                findings.append(
                    f"npm install falló:\n{install.stderr}"
                )

                return findings

            # Compilar proyecto
            build = subprocess.run(
                ["npm", "run", "build"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if build.returncode != 0:

                findings.append(
                    f"Angular build falló:\n{build.stderr}"
                )

                return findings

            # Arrancar Angular
            process = subprocess.Popen(
                ["npm", "run", "start"],
                cwd=path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            try:

                # Esperar a que Angular levante
                time.sleep(20)

                # Si el proceso terminó, hubo error
                if process.poll() is not None:

                    stderr = ""

                    if process.stderr:
                        stderr = process.stderr.read()

                    findings.append(
                        f"Angular no pudo iniciar:\n{stderr}"
                    )

                    return findings

                # Verificar endpoint
                try:

                    response = urlopen(
                        "http://localhost:4200",
                        timeout=10,
                    )

                    if response.status != 200:

                        findings.append(
                            f"Angular inició pero respondió HTTP {response.status}"
                        )

                except Exception as exc:

                    findings.append(
                        f"Angular arrancó pero localhost:4200 no respondió: {exc}"
                    )

            finally:

                process.kill()

        except Exception as exc:

            findings.append(
                f"Error validando Angular: {exc}"
            )

        return findings

    def validate_dotnet(
        self,
        path: Path,
    ) -> list[str]:

        findings: list[str] = []

        try:

            restore = subprocess.run(
                ["dotnet", "restore"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if restore.returncode != 0:

                findings.append(
                    f".NET restore falló:\n{restore.stderr}"
                )

                return findings

            build = subprocess.run(
                ["dotnet", "build"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if build.returncode != 0:

                findings.append(
                    f".NET build falló:\n{build.stderr}"
                )

        except Exception as exc:

            findings.append(
                f"Error validando .NET: {exc}"
            )

        return findings
