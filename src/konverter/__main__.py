import click

from .app import Konverter


@click.command()
@click.argument("config_path", type=click.Path(exists=True, dir_okay=False))
def cli(config_path: str) -> None:
    app = Konverter.from_file(config_path)
    app.render(click.get_text_stream("stdout"))


if __name__ == "__main__":
    cli()
