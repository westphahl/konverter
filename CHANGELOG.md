# Changelog

## [Unreleased]

## [v0.3.0] - 2020-05-19

- Added a `konverter-vault show` command that supports YAML and JSON output
- Added support for `terraform` output format in `konverter-vault show` command
  that allows using it as an [external data source in
  Terraform](https://www.terraform.io/docs/providers/external/data_source.html).

## [v0.2.0] - 2020-03-01

- Added support for directories as context path

## [v0.1.1] - 2020-02-03

- Removed mypy as a runtime dependency ([#1](https://github.com/westphahl/konverter/issues/1))
- Changed minimum required Python version to 3.7 ([#2](https://github.com/westphahl/konverter/issues/2))

## [v0.1.0] - 2020-02-01

Initial release

[unreleased]: https://github.com/westphahl/konverter/compare/v0.3.0...HEAD
[v0.3.0]: https://github.com/westphahl/konverter/compare/v0.2.0...v0.3.0
[v0.2.0]: https://github.com/westphahl/konverter/compare/v0.1.1...v0.2.0
[v0.1.1]: https://github.com/westphahl/konverter/compare/v0.1.0...v0.1.1
[v0.1.0]: https://github.com/westphahl/konverter/releases/tag/v0.1.0
