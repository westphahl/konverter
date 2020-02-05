from __future__ import annotations

import base64
import json
import typing

import jinja2

if typing.TYPE_CHECKING:
    import types


def to_json(value: typing.Any) -> str:
    return json.dumps(value)


def b64encode(value: typing.Union[str, bytes]) -> str:
    # Only do str to bytes conversion
    if isinstance(value, str):
        value = value.encode("utf8")
    encoded_value = base64.b64encode(value)
    return encoded_value.decode("utf8")


class JinjaEnvironment(jinja2.Environment):
    def __init__(
        self,
        *args,
        plugins: typing.Optional[typing.List[types.ModuleType]] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.filters["b64encode"] = b64encode
        self.filters["to_json"] = to_json
        self._enable_plugins(plugins or [])

    def _enable_plugins(self, plugins: typing.List[types.ModuleType]):
        for plugin in plugins:
            self.filters.update(getattr(plugin, "PLUGIN_FILTERS", {}))
            self.tests.update(getattr(plugin, "PLUGIN_TESTS", {}))
            self.globals.update(getattr(plugin, "PLUGIN_GLOBALS", {}))

    def eval_expression(
        self, src: str, context: typing.Mapping[str, typing.Any]
    ) -> str:
        expr = self.compile_expression(src)
        return expr(context)

    def eval_template(
        self, template: str, context: typing.Mapping[str, typing.Any]
    ) -> str:
        tmpl = self.from_string(template)
        return tmpl.render(**context)
