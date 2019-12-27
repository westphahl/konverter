from __future__ import annotations

import pathlib
import shutil
import tempfile
import typing

import click
from cryptography.fernet import Fernet

from .yaml import BaseYAML, KonvertType

if typing.TYPE_CHECKING:
    from ruamel.yaml.nodes import ScalarNode
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


class DecryptYAML(BaseYAML):
    def __init__(self, fernet: Fernet):
        super().__init__()
        self.fernet = fernet
        self.register_type(KonvertVault)

    def decrypt(self, encrypted: typing.IO[str], decrypted: typing.IO[str]) -> None:
        data = self.load(encrypted)
        if data is None:
            return
        self.dump(data, stream=decrypted)


class EncryptYAML(BaseYAML):
    def __init__(self, fernet: Fernet):
        super().__init__()
        self.fernet = fernet
        self.register_type(KonvertEncrypt)

    def encrypt(self, decrypted: typing.IO[str], encrypted: typing.IO[str]) -> None:
        data = self.load(decrypted)
        if data is None:
            return
        self.dump(data, stream=encrypted)


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
            f"Key exists! Overwrite with new key?", default=False, err=True, abort=True,
        )
    with open(key_path, "wb") as key_file:
        key_file.write(Fernet.generate_key())


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def encrypt(ctx: click.Context, file_path: str):
    fernet = ctx.obj["fernet"]

    encrypt_yaml = EncryptYAML(fernet)
    with tempfile.NamedTemporaryFile(mode="wt", suffix=".yaml") as tmp_file:
        with open(file_path, "r") as yaml_file:
            encrypt_yaml.encrypt(yaml_file, tmp_file)

        tmp_file.flush()
        shutil.copy(tmp_file.name, file_path)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def decrypt(ctx: click.Context, file_path: str):
    fernet = ctx.obj["fernet"]

    decrypt_yaml = DecryptYAML(fernet)
    with tempfile.NamedTemporaryFile(mode="wt", suffix=".yaml") as tmp_file:
        with open(file_path, "r") as yaml_file:
            decrypt_yaml.decrypt(yaml_file, tmp_file)

        tmp_file.flush()
        shutil.copy(tmp_file.name, file_path)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def edit(ctx: click.Context, file_path: str):
    fernet = ctx.obj["fernet"]

    decrypt_yaml = DecryptYAML(fernet)
    with tempfile.NamedTemporaryFile(mode="w+t", suffix=".yaml") as tmp_file:
        with open(file_path, "r+") as yaml_file:
            decrypt_yaml.decrypt(yaml_file, tmp_file)
        tmp_file.flush()

        while True:
            click.edit(filename=tmp_file.name)
            tmp_file.flush()
            tmp_file.seek(0)
            try:
                encrypt_yaml = EncryptYAML(fernet)
                with tempfile.NamedTemporaryFile(mode="wt") as out_tmp:
                    encrypt_yaml.encrypt(tmp_file, out_tmp)
                    out_tmp.flush()
                    shutil.copy(out_tmp.name, file_path)
                break
            except Exception:
                click.echo(f"Failed to load and encrypt file!", err=True)
                click.confirm(
                    f"Continue editing? (if not, changes will be lost)",
                    default=True,
                    err=True,
                    abort=True,
                )


if __name__ == "__main__":
    cli()
