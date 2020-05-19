from __future__ import annotations

import json
import pathlib
import shutil
import tempfile
import typing

import click
from cryptography.fernet import Fernet
from ruamel.yaml.nodes import ScalarNode

from .yaml import BaseYAML, KonvertType

if typing.TYPE_CHECKING:
    from ruamel.yaml.constructor import Constructor
    from ruamel.yaml.representer import Representer

DEFAULT_VAULT_KEY_PATH = ".konverter-vault"


class KonvertEncrypt(KonvertType):
    yaml_tag = "!k/encrypt"

    @classmethod
    def to_yaml(
        cls, representer: Representer, instance: KonvertType, yaml
    ) -> ScalarNode:
        value = yaml.fernet.encrypt(bytes(instance.node.value, encoding="utf8"))
        return representer.represent_scalar(
            tag=KonvertVault.yaml_tag,
            value=str(value, encoding="utf8"),
            style=instance.node.style,
        )


class KonvertVault(KonvertType):
    yaml_tag = "!k/vault"

    @classmethod
    def to_yaml(
        cls, representer: Representer, instance: KonvertType, yaml
    ) -> ScalarNode:
        value = yaml.fernet.decrypt(bytes(instance.node.value, encoding="utf8"))
        return representer.represent_scalar(
            tag=KonvertEncrypt.yaml_tag,
            value=str(value, encoding="utf8"),
            style=instance.node.style,
        )


class KonvertVaultValue(KonvertVault):
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


class KonvertEncryptValue(KonvertEncrypt):
    @classmethod
    def from_yaml(cls, constructor: Constructor, node: ScalarNode, yaml) -> ScalarNode:
        return constructor.construct_scalar(
            ScalarNode(tag="tag:yaml.org,2002:str", value=node.value, style=node.style)
        )


class VaultYAML(BaseYAML):
    def __init__(self, fernet: typing.Callable[[], Fernet]):
        super().__init__()
        if isinstance(fernet, Fernet):
            self.fernet: Fernet = fernet
        else:
            self._lazy_fernet = fernet

    def __getattr__(self, name):
        if name == "fernet":
            self.fernet = self._lazy_fernet()
            return self.fernet
        raise AttributeError(name)


class VaultToEditableYAML(VaultYAML):
    def __init__(self, fernet: typing.Callable[[], Fernet]):
        super().__init__(fernet)
        self.register_type(KonvertVault)

    def convert(self, vault: typing.IO[str], decrypted: typing.IO[str]) -> None:
        data = self.load(vault)
        if data is None:
            return
        self.dump(data, stream=decrypted)


class EditableToVaultYAML(VaultYAML):
    def __init__(self, fernet: typing.Callable[[], Fernet]):
        super().__init__(fernet)
        self.register_type(KonvertEncrypt)

    def convert(self, decrypted: typing.IO[str], vault: typing.IO[str]) -> None:
        data = self.load(decrypted)
        if data is None:
            return
        self.dump(data, stream=vault)


class VaultToPlainYAML(VaultYAML):
    def __init__(self, fernet: typing.Callable[[], Fernet]):
        super().__init__(fernet)
        self.register_type(KonvertEncryptValue)
        self.register_type(KonvertVaultValue)

    def convert(self, encrypted: typing.IO[str], plain: typing.IO[str]) -> None:
        data = self.load(encrypted)
        if data is None:
            return
        self.dump(data, stream=plain)


def key_from_file(key_path: typing.Union[str, pathlib.Path]) -> bytes:
    with open(key_path, "rb") as kfile:
        return kfile.read()


@click.group()
@click.option(
    "--key-path", default=DEFAULT_VAULT_KEY_PATH, type=click.Path(dir_okay=False),
)
@click.pass_context
def cli(ctx: click.Context, key_path: str) -> None:
    ctx.ensure_object(dict)
    if ctx.invoked_subcommand == "keygen":
        ctx.obj["key_path"] = key_path
        return

    if not pathlib.Path(key_path).exists():
        raise click.BadParameter("Key file not found", param_hint="key_path")
    ctx.obj["fernet"] = Fernet(key_from_file(key_path))


@cli.command()
@click.pass_context
def keygen(ctx: click.Context) -> None:
    key_path = ctx.obj["key_path"]
    if pathlib.Path(key_path).exists():
        click.confirm(
            "Key exists! Overwrite with new key?", default=False, err=True, abort=True,
        )
    with open(key_path, "wb") as key_file:
        key_file.write(Fernet.generate_key())


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def encrypt(ctx: click.Context, file_path: str):
    fernet = ctx.obj["fernet"]

    encrypt_yaml = EditableToVaultYAML(fernet)
    with tempfile.NamedTemporaryFile(mode="wt", suffix=".yaml") as tmp_file:
        with open(file_path, "r") as yaml_file:
            encrypt_yaml.convert(yaml_file, tmp_file)

        tmp_file.flush()
        shutil.copy(tmp_file.name, file_path)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def decrypt(ctx: click.Context, file_path: str):
    fernet = ctx.obj["fernet"]

    decrypt_yaml = VaultToEditableYAML(fernet)
    with tempfile.NamedTemporaryFile(mode="wt", suffix=".yaml") as tmp_file:
        with open(file_path, "r") as yaml_file:
            decrypt_yaml.convert(yaml_file, tmp_file)

        tmp_file.flush()
        shutil.copy(tmp_file.name, file_path)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def edit(ctx: click.Context, file_path: str):
    fernet = ctx.obj["fernet"]

    decrypt_yaml = VaultToEditableYAML(fernet)
    with tempfile.NamedTemporaryFile(mode="w+t", suffix=".yaml") as tmp_file:
        with open(file_path, "r+") as yaml_file:
            decrypt_yaml.convert(yaml_file, tmp_file)
        tmp_file.flush()

        while True:
            click.edit(filename=tmp_file.name)
            tmp_file.flush()
            tmp_file.seek(0)
            try:
                encrypt_yaml = EditableToVaultYAML(fernet)
                with tempfile.NamedTemporaryFile(mode="wt") as out_tmp:
                    encrypt_yaml.convert(tmp_file, out_tmp)
                    out_tmp.flush()
                    shutil.copy(out_tmp.name, file_path)
                break
            except Exception:
                click.echo("Failed to load and encrypt file!", err=True)
                click.confirm(
                    "Continue editing? (if not, changes will be lost)",
                    default=True,
                    err=True,
                    abort=True,
                )


def to_terraform_format(data: dict) -> dict:
    def _convert(v):
        if isinstance(v, str):
            return v
        if isinstance(v, (float, int, bool)):
            return str(v)
        raise TypeError("Terraform JSON output only supports string values")

    return {k: _convert(v) for k, v in data.items() if v is not None}


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "-f",
    "--format",
    "output_format",
    type=click.Choice(["yaml", "json", "terraform"], case_sensitive=False),
    default="yaml",
)
@click.pass_context
def show(ctx: click.Context, file_path: str, output_format: str):
    fernet = ctx.obj["fernet"]

    encrypt_yaml = VaultToPlainYAML(fernet)
    with open(file_path, "r+") as yaml_file:
        with click.open_file("-", "wt") as stdout:
            data = encrypt_yaml.load(yaml_file)
            if output_format == "json":
                json.dump(data, stdout, indent=2)
            elif output_format == "terraform":
                json.dump(to_terraform_format(data), stdout, indent=2)
            else:
                encrypt_yaml.dump(data, stdout)


if __name__ == "__main__":
    cli()
