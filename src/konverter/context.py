from __future__ import annotations

import pathlib
import typing

from cryptography.fernet import Fernet
from ruamel.yaml.nodes import ScalarNode

from .vault import KonvertEncrypt, KonvertVault, key_from_file
from .yaml import BaseYAML

if typing.TYPE_CHECKING:
    from ruamel.yaml.constructor import Constructor


class KonvertContextVault(KonvertVault):
    @classmethod
    def from_yaml(cls, constructor: Constructor, node: ScalarNode, yaml) -> ScalarNode:
        value = yaml.fernet.decrypt(bytes(node.value, encoding="utf8"))
        return constructor.construct_scalar(
            ScalarNode(
                tag="tag:yaml.org,2002:str",
                value=str(value, encoding="utf8"),
                style=node.style,
            )
        )


class KonvertContextEncrypt(KonvertEncrypt):
    @classmethod
    def from_yaml(cls, constructor: Constructor, node: ScalarNode, yaml) -> ScalarNode:
        return constructor.construct_scalar(
            ScalarNode(tag="tag:yaml.org,2002:str", value=node.value, style=node.style)
        )


class ContextYAML(BaseYAML):
    def __init__(self, provider: ContextProvider):
        super().__init__()
        self.provider = provider
        self.register_type(KonvertContextEncrypt)
        self.register_type(KonvertContextVault)

    @property
    def fernet(self) -> Fernet:
        return self.provider.fernet


class ContextProvider:
    def __init__(
        self, work_dir: pathlib.Path, key_path: typing.Union[str, pathlib.Path]
    ):
        self.work_dir = work_dir
        self.key_path = key_path
        self._fernet: typing.Optional[Fernet] = None

    @property
    def fernet(self) -> Fernet:
        if self._fernet is None:
            self._fernet = Fernet(key_from_file(self.work_dir / self.key_path))
        return self._fernet

    def load_context(self, path: pathlib.Path) -> typing.Mapping[str, typing.Any]:
        with open(path) as yaml_file:
            return ContextYAML(self).load(yaml_file)
