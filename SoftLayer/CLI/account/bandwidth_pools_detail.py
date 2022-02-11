"""Get bandwidth pools."""
# :license: MIT, see LICENSE for more details.
import click

from SoftLayer import AccountManager
from SoftLayer.CLI import environment
from SoftLayer.CLI import formatting
from SoftLayer import utils


@click.command()
@click.argument('identifier')
@environment.pass_env
def cli(env, identifier):
    """Get bandwidth pool details."""

    manager = AccountManager(env.client)
    bandwidths = manager.getBandwidthDetail(identifier)

    table = formatting.KeyValueTable(['name', 'value'])
    table.align['name'] = 'r'
    table.align['value'] = 'l'
    table.add_row(['Id', bandwidths['id']])
    table.add_row(['Name', bandwidths['name']])
    table.add_row(['Create Date', bandwidths['createDate']])
    current = "{} GB".format(utils.lookup(bandwidths, 'billingCyclePublicBandwidthUsage', 'amountOut', 0))
    table.add_row(['Current Usage', current])
    projected = "{} GB".format(bandwidths.get('projectedPublicBandwidthUsage', 0))
    table.add_row(['Projected  Usage', projected])
    inbound = "{} GB".format(bandwidths.get('inboundPublicBandwidthUsage', 0))
    table.add_row(['Inbound   Usage', inbound])
    if bandwidths['hardware'] != []:
        table.add_row(['hardware', _bw_table(bandwidths['hardware'])])
    else:
        table.add_row(['hardware', 'not found'])

    if bandwidths['virtualGuests'] != []:
        table.add_row(['virtualGuests', _virtual_table(bandwidths['virtualGuests'])])
    else:
        table.add_row(['virtualGuests', 'Not Found'])

    if bandwidths['bareMetalInstances'] != []:
        table.add_row(['Netscale', _bw_table(bandwidths['bareMetalInstances'])])
    else:
        table.add_row(['Netscale', 'Not Found'])

    env.fout(table)


def _bw_table(bw_data):
    """Generates a bandwidth useage table"""
    table_data = formatting.Table(['Id', 'HostName', "IP Address", 'Amount', "Current Usage"])
    for bw_point in bw_data:
        amount = "{} GB".format(utils.lookup(bw_point, 'bandwidthAllotmentDetail', 'allocation', 'amountOut', 0))
        current = "{} GB".format(utils.lookup(bw_point, 'outboundBandwidthUsage', 0))
        ip_address = bw_point['primaryIpAddress']
        table_data.add_row([bw_point['id'], bw_point['fullyQualifiedDomainName'], ip_address, amount, current])
    return [table_data]


def _virtual_table(bw_data):
    """Generates a virtual bandwidth usage table"""
    table_data = formatting.Table(['Id', 'HostName', "IP Address", 'Amount', "Current Usage"])
    for bw_point in bw_data:
        amount = "{} GB".format(utils.lookup(bw_point, 'bandwidthAllotmentDetail', 'allocation', 'amountOut', 0))
        current = "{} GB".format(utils.lookup(bw_point, 'outboundBandwidthUsage', 0))
        ip_address = bw_point['primaryIpAddress']
        table_data.add_row([bw_point['id'], bw_point['fullyQualifiedDomainName'], ip_address, amount, current])
    return [table_data]
