"""Refresh a duplicate volume with a snapshot from its parent."""
# :license: MIT, see LICENSE for more details.

import click
import SoftLayer
from SoftLayer.CLI import environment


@click.command(cls=SoftLayer.CLI.command.SLCommand, )
@click.argument('volume_id')
@click.argument('snapshot_id')
@click.option('--force-refresh', '-f',
    help="An optional parameter for force refreshing the volume")
    type=click.Choice(['True', 'False']),
    default='False',
@environment.pass_env
def cli(env, volume_id, snapshot_id, force_refresh):
    """Refresh a duplicate volume with a snapshot from its parent."""
    block_manager = SoftLayer.BlockStorageManager(env.client)
    resp = block_manager.refresh_dupe(volume_id, snapshot_id, force_refresh)

    click.echo(resp)
