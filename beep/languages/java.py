"""Java language adapter."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from beep.languages._shared import deduplicate
from beep.languages.base import LanguageAdapter, ProjectCommand


class JavaAdapter(LanguageAdapter):
    @property
    def name(self) -> str:
        return "java"

    @property
    def extensions(self) -> list[str]:
        return [".java", ".gradle", ".kts"]

    def detect(self, root_path: str) -> bool:
        root = Path(root_path)
        indicators = [
            root / "pom.xml",
            root / "build.gradle",
            root / "build.gradle.kts",
            root / "settings.gradle",
            root / "settings.gradle.kts",
        ]
        return any(p.exists() for p in indicators) or bool(list(root.rglob("*.java")))

    def get_build_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        if (root / "pom.xml").exists():
            return [
                ProjectCommand(
                    name="maven-compile",
                    command=["mvn", "compile"],
                    description="Compile Java project with Maven",
                )
            ]
        if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
            return [
                ProjectCommand(
                    name="gradle-build",
                    command=["gradle", "build"],
                    description="Build Java project with Gradle",
                )
            ]
        return []

    def get_test_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        if (root / "pom.xml").exists():
            return [
                ProjectCommand(
                    name="maven-test",
                    command=["mvn", "test"],
                    description="Run Java tests with Maven",
                )
            ]
        if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
            return [
                ProjectCommand(
                    name="gradle-test",
                    command=["gradle", "test"],
                    description="Run Java tests with Gradle",
                )
            ]
        return []

    def get_lint_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        commands: list[ProjectCommand] = []
        if (root / "pom.xml").exists() and _has_maven_plugin(root, "checkstyle"):
            commands.append(
                ProjectCommand(
                    name="maven-checkstyle",
                    command=["mvn", "checkstyle:check"],
                    description="Run Checkstyle via Maven",
                )
            )
        if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
            commands.append(
                ProjectCommand(
                    name="gradle-checkstyle",
                    command=["gradle", "checkstyleMain"],
                    description="Run Checkstyle via Gradle",
                )
            )
        if (root / "spotbugs.xml").exists() or (root / "findbugs.xml").exists():
            commands.append(
                ProjectCommand(
                    name="spotbugs",
                    command=["mvn", "spotbugs:check"],
                    description="Run SpotBugs static analysis",
                )
            )
        return commands

    def find_test_files(self, source_file: str, root_path: str) -> list[str]:
        root = Path(root_path)
        source_name = Path(source_file).stem
        candidates: list[str] = []
        test_dirs = ["src/test/java", "test"]
        for test_dir in test_dirs:
            dir_path = root / test_dir
            if dir_path.is_dir():
                candidates.extend(str(p) for p in dir_path.rglob(f"*{source_name}*.java"))
        candidates.extend(str(p) for p in root.rglob(f"*{source_name}Test.java"))
        candidates.extend(str(p) for p in root.rglob(f"*{source_name}Tests.java"))
        return deduplicate(candidates)

    def get_frameworks(self, root_path: str) -> list[str]:
        root = Path(root_path)
        frameworks: list[str] = []
        pom = root / "pom.xml"
        gradle = root / "build.gradle"
        gradle_kts = root / "build.gradle.kts"

        if pom.exists():
            content = pom.read_text(encoding="utf-8").lower()
            if "spring-boot" in content:
                frameworks.append("Spring Boot")
            if "jakarta.servlet" in content or "javax.servlet" in content:
                frameworks.append("Jakarta EE")
            if "micronaut" in content:
                frameworks.append("Micronaut")
            if "quarkus" in content:
                frameworks.append("Quarkus")

        build_file = gradle if gradle.exists() else gradle_kts
        if build_file.exists():
            content = build_file.read_text(encoding="utf-8").lower()
            if "spring-boot" in content:
                frameworks.append("Spring Boot")
            if "micronaut" in content:
                frameworks.append("Micronaut")
            if "quarkus" in content:
                frameworks.append("Quarkus")

        return deduplicate(frameworks)

    def get_package_managers(self, root_path: str) -> list[str]:
        root = Path(root_path)
        managers: list[str] = []
        if (root / "pom.xml").exists():
            managers.append("maven")
        if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
            managers.append("gradle")
        return managers


def _has_maven_plugin(root: Path, plugin: str) -> bool:
    pom = root / "pom.xml"
    if not pom.exists():
        return False
    try:
        tree = ET.parse(pom)
        root_elem = tree.getroot()
        ns = {"m": "http://maven.apache.org/POM/4.0.0"}
        for build in root_elem.findall(".//m:build", ns) or root_elem.findall(".//build"):
            for plugin_elem in build.findall(".//m:plugin", ns) or build.findall(".//plugin"):
                artifact_id = plugin_elem.find("m:artifactId", ns)
                if (
                    artifact_id is not None
                    and artifact_id.text
                    and plugin in artifact_id.text.lower()
                ):
                    return True
    except ET.ParseError:
        content = pom.read_text(encoding="utf-8").lower()
        if plugin.lower() in content:
            return True
    return False
