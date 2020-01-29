import pytest

from click.testing import CliRunner
from ruamel.yaml import YAML

from konverter.__main__ import cli


def pytest_collect_file(parent, path):
    if path.ext == ".yaml" and path.basename.startswith("test_"):
        return E2ETest(path.basename, path, parent)


class E2ETest(pytest.Item):
    def __init__(self, name, fspath, parent):
        super().__init__(name, parent)
        self.fspath = fspath
        *_, identifier = str(fspath.basename).partition("_")
        self.expect_path = f"{fspath.dirname}/expect_{identifier}"

    def runtest(self):
        runner = CliRunner()
        result = runner.invoke(cli, [str(self.fspath)])
        assert result.exit_code == 0, result.output
        with open(self.expect_path) as expect_file:
            assert result.output == expect_file.read()

    @property
    def nodeid(self):
        return f"e2e::{self.fspath.basename}"
