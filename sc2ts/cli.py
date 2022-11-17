import json
import logging
import platform
import sys

import tskit
import tsinfer
import click
import daiquiri

from . import convert
from . import inference


def get_environment():
    """
    Returns a dictionary describing the environment in which sc2ts
    is currently running.
    """
    env = {
        "os": {
            "system": platform.system(),
            "node": platform.node(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "libraries": {
            "tsinfer": {"version": tsinfer.__version__},
            "tskit": {"version": tskit.__version__},
        },
    }
    return env


def get_provenance_dict():
    """
    Returns a dictionary encoding an execution of stdpopsim conforming to the
    tskit provenance schema.
    """
    document = {
        "schema_version": "1.0.0",
        "software": {"name": "sc2ts", "version": "dev"},
        "parameters": {"command": sys.argv[0], "args": sys.argv[1:]},
        "environment": get_environment(),
    }
    return document


def setup_logging(verbosity):
    log_level = "WARN"
    if verbosity > 0:
        log_level = "INFO"
    if verbosity > 1:
        log_level = "DEBUG"
    daiquiri.setup(level=log_level)


@click.command()
@click.argument("fasta", type=click.Path(exists=True, dir_okay=False))
@click.argument("metadata", type=click.Path(exists=True, dir_okay=False))
@click.argument("output", type=click.Path(exists=True, dir_okay=True, file_okay=False))
@click.option("-v", "--verbose", count=True)
def import_fasta(fasta, metadata, output, verbose):
    setup_logging(verbose)
    convert.alignments_to_samples(fasta, metadata, output, show_progress=True)


@click.command()
@click.argument("metadata")
@click.argument("db")
@click.option("-v", "--verbose", count=True)
def import_metadata(metadata, db, verbose):
    """
    Convert a CSV formatted metadata file to a database for later use.
    """
    setup_logging(verbose)
    convert.metadata_to_db(metadata, db)


@click.command()
@click.argument("samples-file")
@click.argument("output-file")
@click.option("--ancestors-ts", "-A", default=None, help="Path base to match against")
@click.option("--num-mismatches", default=None, type=float, help="num-mismatches")
@click.option(
    "--max-submission-delay",
    default=None,
    type=int,
    help=(
        "The maximum number of days between the sample and its submission date "
        "for it to be included in the inference"
    ),
)
@click.option("--num-threads", default=0, type=int, help="Number of match threads")
@click.option("-p", "--precision", default=None, type=int, help="Match precision")
@click.option("--no-progress", default=False, is_flag=True, help="Don't show progress")
@click.option("-v", "--verbose", count=True)
def infer(
    samples_file,
    output_file,
    ancestors_ts,
    num_mismatches,
    max_submission_delay,
    num_threads,
    precision,
    no_progress,
    verbose,
):
    setup_logging(verbose)

    if ancestors_ts is not None:
        ancestors_ts = tskit.load(ancestors_ts)
        logging.info(f"Loaded ancestors ts with {ancestors_ts.num_samples} samples")

    provenance = get_provenance_dict()
    with tsinfer.load(samples_file) as sd:
        ts = inference.infer(
            sd,
            ancestors_ts=ancestors_ts,
            num_threads=num_threads,
            num_mismatches=num_mismatches,
            max_submission_delay=max_submission_delay,
            precision=precision,
            show_progress=not no_progress,
        )
        tables = ts.dump_tables()
        tables.provenances.add_row(json.dumps(provenance))
        ts = tables.tree_sequence()
        ts.dump(output_file)


@click.command()
@click.argument("samples-file")
@click.argument("ts-file")
@click.option("-v", "--verbose", count=True)
@click.option(
    "--max-submission-delay",
    default=None,
    type=int,
    help=(
        "The maximum number of days between the sample and its submission date "
        "for it to be included in the inference"
    ),
)
def validate(samples_file, ts_file, verbose, max_submission_delay):
    setup_logging(verbose)

    ts = tskit.load(ts_file)
    with tsinfer.load(samples_file) as sd:
        inference.validate(
            sd, ts, max_submission_delay=max_submission_delay, show_progress=True
        )


@click.group()
def cli():
    pass


cli.add_command(import_fasta)
cli.add_command(import_metadata)
cli.add_command(infer)
cli.add_command(validate)
