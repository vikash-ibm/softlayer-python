"""Find details about this machine."""
# :license: MIT, see LICENSE for more details.

import click

import SoftLayer
from SoftLayer.CLI import environment
from SoftLayer.CLI import exceptions
from SoftLayer.CLI import formatting

META_CHOICES = [
    'backend_ip',
    'backend_mac',
    'datacenter',
    'datacenter_id',
    'fqdn',
    'frontend_mac',
    'id',
    'ip',
    'network',
    'provision_state',
    'tags',
    'user_data',
]

META_MAPPING = {
    'backend_ip': 'primary_backend_ip',
    'ip': 'primary_ip',
}

HELP = """Find details about the machine making these API calls.

.. csv-table:: Choices

    {choices}

""".format(choices="\n    ".join(META_CHOICES))


@click.command(cls=SoftLayer.CLI.command.SLCommand, help=HELP,
               short_help="Find details about this machine.",
               epilog="These commands only work on devices on the backend "
                      "SoftLayer network. This allows for self-discovery for "
                      "newly provisioned resources.")
@click.argument('prop', type=click.Choice(META_CHOICES))
@environment.pass_env
def cli(env, prop):
    """Find details about this machine."""

    try:
        if prop == 'network':
            env.fout(get_network())
            return

        meta_prop = META_MAPPING.get(prop) or prop
        env.fout(SoftLayer.MetadataManager().get(meta_prop))
    except SoftLayer.TransportError as ex:
        message = 'Cannot connect to the backend service address. Make sure '\
                  'this command is being ran from a device on the backend network.'
        raise exceptions.CLIAbort(message) from ex


def get_network():
    """Returns a list of tables with public and private network details."""
    meta = SoftLayer.MetadataManager()
    network_tables = []
    for network_func in [meta.public_network, meta.private_network]:
        network = network_func()

        table = formatting.KeyValueTable(['name', 'value'])
        table.align['name'] = 'r'
        table.align['value'] = 'l'
        table.add_row(['mac addresses',
                       formatting.listing(network['mac_addresses'],
                                          separator=',')])
        table.add_row(['router', network['router']])
        table.add_row(['vlans',
                       formatting.listing(network['vlans'], separator=',')])
        table.add_row(['vlan ids',
                       formatting.listing(network['vlan_ids'], separator=',')])
        network_tables.append(table)

    return network_tables
