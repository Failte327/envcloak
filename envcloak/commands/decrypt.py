import os
import shutil
from pathlib import Path
import click
from click import style
from envcloak.utils import debug_log, calculate_required_space
from envcloak.decorators.common_decorators import (
    debug_option,
    dry_run_option,
    force_option,
)
from envcloak.validation import (
    check_file_exists,
    check_directory_exists,
    check_directory_not_empty,
    check_output_not_exists,
    check_permissions,
    check_disk_space,
)
from envcloak.encryptor import decrypt_file
from envcloak.exceptions import (
    OutputFileExistsException,
    DiskSpaceException,
    FileDecryptionException,
)


@click.command()
@debug_option
@dry_run_option
@force_option
@click.option(
    "--input",
    "-i",
    required=False,
    help="Path to the encrypted input file (e.g., .env.enc).",
)
@click.option(
    "--directory",
    "-d",
    required=False,
    help="Path to the directory of encrypted files.",
)
@click.option(
    "--output",
    "-o",
    required=True,
    help="Path to the output file or directory for decrypted files.",
)
@click.option(
    "--key-file", "-k", required=True, help="Path to the decryption key file."
)
def decrypt(input, directory, output, key_file, dry_run, force, debug):
    """
    Decrypt environment variables from a file or all files in a directory.
    """
    try:
        debug_log("Debug mode is enabled", debug)

        # Always perform validation
        debug_log("Debug: Validating input and directory parameters.", debug)
        if not input and not directory:
            raise click.UsageError("You must provide either --input or --directory.")
        if input and directory:
            raise click.UsageError(
                "You must provide either --input or --directory, not both."
            )
        if input:
            debug_log(f"Debug: Validating input file {input}.", debug)
            check_file_exists(input)
            check_permissions(input)
        if directory:
            debug_log(f"Debug: Validating directory {directory}.", debug)
            check_directory_exists(directory)
            check_directory_not_empty(directory)
        debug_log(f"Debug: Validating key file {key_file}.", debug)
        check_file_exists(key_file)
        check_permissions(key_file)

        # Handle overwrite with --force
        debug_log("Debug: Handling overwrite logic with force flag.", debug)
        if not force:
            check_output_not_exists(output)
        else:
            if os.path.exists(output):
                debug_log(
                    f"Debug: Existing file or directory found at {output}. Overwriting due to --force.",
                    debug,
                )
                click.echo(
                    style(
                        f"⚠️  Warning: Overwriting existing file or directory {output} (--force used).",
                        fg="yellow",
                    )
                )
                if os.path.isdir(output):
                    debug_log(f"Debug: Removing existing directory {output}.", debug)
                    shutil.rmtree(output)  # Remove existing directory
                else:
                    debug_log(f"Debug: Removing existing file {output}.", debug)
                    os.remove(output)  # Remove existing file

        debug_log(
            f"Debug: Calculating required space for input {input} or directory {directory}.",
            debug,
        )
        required_space = calculate_required_space(input, directory)
        check_disk_space(output, required_space)

        if dry_run:
            debug_log("Debug: Dry-run flag set. Skipping actual decryption.", debug)
            click.echo("Dry-run checks passed successfully.")
            return

        # Actual decryption logic
        with open(key_file, "rb") as kf:
            key = kf.read()
            debug_log(f"Debug: Key file {key_file} read successfully.", debug)

        if input:
            debug_log(
                f"Debug: Decrypting file {input} -> {output} using key {key_file}.",
                debug,
            )
            decrypt_file(input, output, key)
            click.echo(f"File {input} decrypted -> {output} using key {key_file}")
        elif directory:
            input_dir = Path(directory)
            output_dir = Path(output)
            if not output_dir.exists():
                debug_log(
                    f"Debug: Output directory {output_dir} does not exist. Creating it.",
                    debug,
                )
                output_dir.mkdir(parents=True)

            for file in input_dir.iterdir():
                if file.is_file() and file.suffix == ".enc":  # Only decrypt .enc files
                    output_file = output_dir / file.stem  # Remove .enc from filename
                    debug_log(
                        f"Debug: Decrypting file {file} -> {output_file} using key {key_file}.",
                        debug,
                    )
                    decrypt_file(str(file), str(output_file), key)
                    click.echo(
                        f"File {file} decrypted -> {output_file} using key {key_file}"
                    )
    except (
        OutputFileExistsException,
        DiskSpaceException,
        FileDecryptionException,
    ) as e:
        click.echo(f"Error during decryption: {str(e)}")
