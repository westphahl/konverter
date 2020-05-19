# Konverter - YAML templating for responsible users

Konverter is a YAML templating tool that uses Jinja [expression](https://jinja.palletsprojects.com/en/2.10.x/templates/#expressions) and [templates](https://jinja.palletsprojects.com/en/2.10.x/templates/) and supports inline-encrypted variables.

**Features:**
- generic YAML templating (**not** specific to e.g. Kubernetes)
- works on the **YAML structure**; text templating only available for values
- support for simple **inline-encrypted variables**
- ... more to come (see "[planned features](#planned-features)")

The project is still at an **early stage**, so I'm happy about any contribution!

### Motivation

I created this tool mainly to scratch my own itch. I needed a simple way to store encrypted values along my Kubernetes manifests, but found that e.g. [Kustomize](https://kustomize.io/) makes this [extra hard](https://github.com/kubernetes-sigs/kustomize/issues/692).

In that regard Konverter follows the Python philosophy: "We are all [consenting adults](https://docs.python-guide.org/writing/style/#we-are-all-responsible-users)". So yes, you can do potentially dangerous things with it.

Also, the way Kustomize works by [patching and transforming](https://github.com/kubernetes-sigs/kustomize/blob/master/docs/fields.md#transformers) YAML, as well as the concept of `Secret` and `ConfigMap` [generators](https://github.com/kubernetes-sigs/kustomize/blob/master/docs/fields.md#generators), didn't feel natural to me.

To each his own :)

## Installation

The easiest way to install Konverter is via [pipx](https://github.com/pipxproject/pipx):

```shell
$ pipx install konverter
```

Or just with plain pip:

```shell
$ pip install konverter
```

## Usage

Konverter is configured via a YAML file (of course). In this config file, you define your templates and the context (variables) used to render those templates. If you want to render your templates with a different context (e.g. templating Kubernetes manifests for staging, production, ...) you need a separate config file.

Here's a simple example of a config file:
```yaml
templates:
  - manifest.yaml

context:
  - vars/common.yaml
  - vars/prod.yaml
```

The templates are rendered using the `konverter` command by passing it the config file:
```shell
$ konverter production.yaml
...
```

The rendered templates will be written to `stdout` as a multi-document YAML. This allows for easy composition with other tools like `kubectl`:

```shell
$ konverter production.yaml | kubectl apply -f -
```

### Templates

Under the `templates` key, you can configure a list of files or directories. In the case of a directory, Konverter will recursively include all `*.y[a]ml` files.

Konverter uses [YAML tags](https://yaml.org/spec/1.2/spec.html#id2761292) to declare expressions (`!k/expr`) and templates (`!k/template`):

```yaml
foo: !k/expr foo.bar
FOO: !k/expr foo.bar|upper

not_defined: !k/expr missing_variable|default('default value')

config: !k/template |-
  Hello {{ name }}

  {% for item in list_of_values %}
    Hello {{ item }}
  {% endfor %}
```

#### Expressions

Expressions are mainly useful for injecting data from the context and performing simple transformations:

```yaml
# Example context
value:
  from:
    context: barfoo
    other: foobar
```

```yaml
# Use !k/expr to inject the values in a template
foo:
  bar: !k/expr value.from.context
  foo: !k/expr value.from.other|upper
```

When using the `!k/expr` tag, the value can be any valid [Jinja2 expression](https://jinja.palletsprojects.com/en/2.10.x/templates/#expressions). In addition to the standard Jinja [filters](https://jinja.palletsprojects.com/en/2.10.x/templates/#list-of-builtin-filters), [tests](https://jinja.palletsprojects.com/en/2.10.x/templates/#list-of-builtin-tests) and [global functions](https://jinja.palletsprojects.com/en/2.10.x/templates/#list-of-global-functions) the following filters are currently available:

- `to_json`: dump an object as a *JSON string*
- `b64encode`: encode value using Base64

Missing a filter? Let me know or feel free to contribute!

#### Templates

The `!k/template` tag supports the full [Jinja2 template syntax](https://jinja.palletsprojects.com/en/2.10.x/templates/) (currently with some exceptions, like template inheritance), but the output will always be a string value. Inline templates are most useful for customizing config files.

### Context

The `context` key in the config contains a list of files or directories that Konverter uses for loading variable definitions. Those variables serve as the context (hence the name) when rendering templates. In the case of multiple context files containing the same top-level key, the entry from the last listed file wins (in the future we might support merging those contexts).

This is how a simple context file might look like
```yaml
deployment:
  name: foobar
  server_name: foobar.example.com
annotations:
  version: 1.0
  environment: production
```

#### Encrypted values

In addition there can be inline-encrypted values:

```yaml
credentials:
  user: root
  password: !k/vault gAAAAABeKd7EEt-jCYJSLS_ze6oO401yRDCthJFkuR4ptIFNnSElTccUnOVSQ1rSCDbIdljB59SRWjy2rDq7174stq3FFzyE_w==
```

Konverter uses [Fernet symmetric encryption](https://cryptography.io/en/latest/fernet/) with secret keys. To use encrypted values we have to create key first:

```shell
$ konverter-vault keygen
```

This will create a key file `.konverter-vault` in the current directory containing the key. **Make sure to never commit this file to version control!**

By default, Konverter will look for the vault key in the same directory as the config file when rendering templates. See the section "[advanced configuration](#advanced-configuration)" on how to use a different path.

The following command will decrypt any encrypted values in the given file and launch your `$EDITOR`:

```shell
$ konverter-vault edit vars/secret.yaml
```

Values that should be encrypted are marked with the `!k/encrypt` YAML tag:

```yaml
credentials:
  user: root
  password: !k/encrypt secret-password
```

After closing the editor Konverter will encrypt the values:

```yaml
credentials:
  user: root
  password: !k/vault gAAAAABeKd7EEt-jCYJSLS_ze6oO401yRDCthJFkuR4ptIFNnSElTccUnOVSQ1rSCDbIdljB59SRWjy2rDq7174stq3FFzyE_w==
```

Instead of editing the file via the `konverter-vault edit` command you can also encrypt/decrypt the files separately:

```shell
$ konverter-vault encrypt vars/secret.yaml
...
$ konverter-vault decrypt vars/secret.yaml
```

In case the decrypted content should be passed to another tool that expects
YAML or JSON, the `konverter-vault show` command can come in handy:

```shell
$ konverter-vault show --format=json vars/secret.yaml
{
  "credentials": {
    "user": "root",
    "password": "secret-password"
  }
}
```

It will decrypt the given file and remove all `!k/(encrypt|vault)` YAML tags.
Supported output formats are `yaml` (default), `json` or `terraform`.

The `terraform` output format is usefull for using `konverter-vault` as an
[external data source in
Terraform](https://www.terraform.io/docs/providers/external/data_source.html)

```hcl
data "external" "konverter" {
  program = [
    "konverter-vault", "show", "--format=terraform", "vars/secrets.yaml"
  ]
}
```

Unfortunately the "[external program
protocol](https://www.terraform.io/docs/providers/external/data_source.html#external-program-protocol)"
only allows string values (no lists or objects). All `float`, `int` and `bool`
values will be converted to strings. Other types will cause an error when
using this output format.

### Advanced configuration

The above config file could be rewritten in a more verbose format:

```yaml
templates:
  - manifest.yaml

providers:
  default:
    key_path: .konverter-vault

context:
  - provider: default
    path: vars/common.yaml
  - provider: default
    path: vars/prod.yaml
```

In case we want to change the location of the vault key, we can simply override the default provider:

```yaml
...
providers:
  default:
    key_path: ~/.my-vault-key
...
```

## Planned features

- better error handling
- improve test coverage
- importing templates from a file
- support for other context providers

Feel free to create an issue or a pull-request if you are missing something!
