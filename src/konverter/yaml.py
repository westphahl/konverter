from __future__ import annotations

import abc
import copy
import functools
import typing

import jinja2
from ruamel.yaml import YAML
from ruamel.yaml.constructor import RoundTripConstructor
from ruamel.yaml.representer import RoundTripRepresenter

from .template import JinjaEnvironment

if typing.TYPE_CHECKING:
    from ruamel.yaml.nodes import Node, ScalarNode
    from ruamel.yaml.constructor import Constructor
    from ruamel.yaml.representer import Representer

    from .app import Konverter


class UnsharedRoundTripConstructor(RoundTripConstructor):
    def __new__(cls, *args, **kwargs):
        klass = type(
            cls.__name__,
            (cls,),
            {
                "yaml_constructors": copy.deepcopy(cls.yaml_constructors),
                "yaml_multi_constructors": copy.deepcopy(cls.yaml_multi_constructors),
            },
        )
        return super().__new__(klass)


class UnsharedRoundTripRepresenter(RoundTripRepresenter):
    def __new__(cls, *args, **kwargs):
        klass = type(
            cls.__name__,
            (cls,),
            {
                "yaml_representers": copy.deepcopy(cls.yaml_representers),
                "yaml_multi_representers": copy.deepcopy(cls.yaml_multi_representers),
            },
        )
        return super().__new__(klass)


class BaseYAML(YAML):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Representer = UnsharedRoundTripRepresenter
        self.Constructor = UnsharedRoundTripConstructor

    def register_type(self, klass: typing.Type[KonvertType]) -> None:
        self.representer.add_representer(
            klass, functools.partial(klass.to_yaml, yaml=self)
        )
        self.constructor.add_constructor(
            klass.yaml_tag, functools.partial(klass.from_yaml, yaml=self)
        )


class KonvertType(abc.ABC):
    yaml_tag: str

    def __init__(self, node: ScalarNode):
        self.node = node

    @classmethod
    def from_yaml(cls, constructor: Constructor, node: ScalarNode, yaml) -> typing.Any:
        return cls(node)

    @classmethod
    @abc.abstractmethod
    def to_yaml(cls, representer: Representer, instance: KonvertType, yaml) -> Node:
        pass


class KonvertExpression(KonvertType):
    yaml_tag = "!k/expr"

    @classmethod
    def to_yaml(cls, representer: Representer, instance: KonvertType, yaml) -> Node:
        return representer.represent_data(
            yaml.env.compile_expression(instance.node.value, undefined_to_none=False)(
                yaml.app.context
            )
        )


class KonvertTemplate(KonvertType):
    yaml_tag = "!k/template"

    @classmethod
    def to_yaml(cls, representer: Representer, instance: KonvertType, yaml) -> Node:
        value = yaml.env.eval_template(instance.node.value, yaml.app.context)
        return representer.represent_scalar(
            tag="tag:yaml.org,2002:str", value=value, style=instance.node.style
        )


class KonverterYAML(BaseYAML):
    def __init__(self, app: Konverter):
        super().__init__()
        self.app = app
        self.env = JinjaEnvironment(undefined=jinja2.StrictUndefined)
        self.register_type(KonvertExpression)
        self.register_type(KonvertTemplate)

    def render(self, in_file: typing.IO[str], out_file: typing.IO[str]) -> None:
        self.dump_all(self.load_all(in_file), out_file)
