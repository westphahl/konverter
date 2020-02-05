from __future__ import annotations

import collections
import importlib
import pathlib
import sys
import typing

from ruamel.yaml import YAML

from .context import ContextProvider
from .yaml import KonverterYAML

if typing.TYPE_CHECKING:
    import types

DEFAULT_PROVIDER = {
    "default": {"key_path": ".konverter-vault",},
}


class Konverter:
    def __init__(self, templates, template_plugins, context, work_dir):
        self.templates = templates
        self.template_plugins = template_plugins
        self.context = context
        self.work_dir = work_dir

    def render(self, out_file):
        yaml = KonverterYAML(self, self.template_plugins)
        # We want to have the documents from different files
        # separated by "---".
        yaml.explicit_start = True
        for template_path in self.templates:
            with open(template_path) as template:
                yaml.render(template, out_file)

    @classmethod
    def from_file(cls, config_path: typing.Union[str, pathlib.Path]):
        config_path = pathlib.Path(config_path)
        work_dir = config_path.parent.absolute()

        with open(config_path) as config_file:
            cfg = YAML().load(config_file)

        return cls.from_dict(cfg, work_dir)

    @classmethod
    def from_dict(cls, config, work_dir):
        templates = list(
            cls._collect_templates(
                (pathlib.Path(p) for p in config["templates"]), work_dir
            )
        )
        template_plugins = list(
            cls._load_template_plugins(config.get("template_plugins", []), work_dir)
        )
        providers = dict(
            cls._create_providers(
                collections.ChainMap(config.get("providers", {}), DEFAULT_PROVIDER),
                work_dir,
            )
        )
        context = collections.ChainMap(*cls._load_context(config["context"], providers))
        return cls(templates, template_plugins, context, work_dir)

    @staticmethod
    def _collect_templates(
        templates: typing.List[str], work_dir: pathlib.Path
    ) -> typing.Generator[pathlib.Path, None, None]:
        for template_path in templates:
            path = work_dir / template_path
            if path.is_file():
                yield path
            elif path.is_dir():
                yield from sorted(path.glob("**/*.y[a]ml"))
            else:
                raise RuntimeError(f"Template path '{path}' not found")

    @staticmethod
    def _create_providers(
        providers, work_dir: pathlib.Path,
    ) -> typing.Generator[typing.Tuple[str, ContextProvider], None, None]:
        for name, provider in providers.items():
            yield name, ContextProvider(
                key_path=pathlib.Path(provider["key_path"]).expanduser(),
                work_dir=work_dir,
            )

    @staticmethod
    def _load_context(context, providers):
        for ctx in context:
            if isinstance(ctx, str):
                provider, path = "default", ctx
            else:
                provider, path = ctx["provider"], ctx["path"]
            yield providers[provider].load_context(path)

    @staticmethod
    def _load_template_plugins(
        plugin_names: typing.List[str], work_dir: pathlib.Path
    ) -> typing.Generator[types.ModuleType, None, None]:
        path = str(work_dir)
        if path not in sys.path:
            sys.path.append(path)
        for module_name in plugin_names:
            yield importlib.import_module(module_name)
