import os
import os.path

import pytest


def test_run_from_project_root_unless_coverage_file_envvar_resolves() -> None:
    if os.getenv("COVERAGE_FILE") is None and not os.path.exists(
        os.path.join(os.getcwd(), "pyproject.toml")
    ):
        pytest.fail("Please run tests from the project root directory only")
