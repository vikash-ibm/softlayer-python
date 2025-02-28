"""Failback from a replicant volume."""
# :license: MIT, see LICENSE for more details.

import click

import SoftLayer
from SoftLayer.CLI import environment


@click.command(cls=SoftLayer.CLI.command.SLCommand, )
@click.argument('volume-id')
@environment.pass_env
def cli(env, volume_id):
    """Failback a file volume from the given replicant volume."""
    file_storage_manager = SoftLayer.FileStorageManager(env.client)

    success = file_storage_manager.failback_from_replicant(volume_id)

    if success:
        click.echo("Failback from replicant is now in progress.")
    else:
        click.echo("Failback operation could not be initiated.")
