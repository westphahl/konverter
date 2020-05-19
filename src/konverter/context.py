from __future__ import annotations

import functools
import pathlib
import typing

from cryptography.fernet import Fernet

from .vault import key_from_file, VaultToPlainYAML


class ContextProvider:
    def __init__(
        self, work_dir: pathlib.Path, key_path: typing.Union[str, pathlib.Path]
    ):
        self.work_dir = work_dir
        self.key_path = key_path
        self._fernet: typing.Optional[Fernet] = None

    def fernet(self) -> Fernet:
        if self._fernet is None:
            self._fernet = Fernet(key_from_file(self.work_dir / self.key_path))
        return self._fernet

    def load_context(self, path: pathlib.Path) -> typing.Mapping[str, typing.Any]:
        with open(path) as yaml_file:
            # We don't pass the property directly as this would try to load the
            # key from file which won't work when no key file is provided.
            # This is a valid use case e.g. when the context doesn't use
            # encrypted values.
            return VaultToPlainYAML(functools.partial(self.fernet)).load(yaml_file)
