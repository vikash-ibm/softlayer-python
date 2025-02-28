"""Display details for a specified volume."""
# :license: MIT, see LICENSE for more details.

import click
import SoftLayer
from SoftLayer.CLI import environment
from SoftLayer.CLI import formatting
from SoftLayer.CLI import helpers
from SoftLayer import utils


@click.command(cls=SoftLayer.CLI.command.SLCommand, )
@click.argument('volume_id')
@environment.pass_env
def cli(env, volume_id):
    """Display details for a specified volume."""
    block_manager = SoftLayer.BlockStorageManager(env.client)
    block_volume_id = helpers.resolve_id(block_manager.resolve_ids, volume_id, 'Block Volume')
    block_volume = block_manager.get_block_volume_details(block_volume_id)
    block_volume = utils.NestedDict(block_volume)

    table = formatting.KeyValueTable(['Name', 'Value'])
    table.align['Name'] = 'r'
    table.align['Value'] = 'l'

    storage_type = block_volume['storageType']['keyName'].split('_').pop(0)
    table.add_row(['ID', block_volume['id']])
    table.add_row(['Username', block_volume['username']])
    table.add_row(['Type', storage_type])
    table.add_row(['Capacity (GB)', "%iGB" % block_volume['capacityGb']])
    table.add_row(['LUN Id', "%s" % block_volume['lunId']])

    if block_volume.get('provisionedIops'):
        table.add_row(['IOPs', float(block_volume['provisionedIops'])])

    if block_volume.get('storageTierLevel'):
        table.add_row([
            'Endurance Tier',
            block_volume['storageTierLevel'],
        ])

    table.add_row([
        'Data Center',
        block_volume['serviceResource']['datacenter']['name'],
    ])
    table.add_row([
        'Target IP',
        block_volume['serviceResourceBackendIpAddress'],
    ])

    if block_volume['snapshotCapacityGb']:
        table.add_row([
            'Snapshot Capacity (GB)',
            block_volume['snapshotCapacityGb'],
        ])
        if 'snapshotSizeBytes' in block_volume['parentVolume']:
            table.add_row([
                'Snapshot Used (Bytes)',
                block_volume['parentVolume']['snapshotSizeBytes'],
            ])

    table.add_row(['# of Active Transactions', "%i"
                   % block_volume['activeTransactionCount']])

    if block_volume['activeTransactions']:
        for trans in block_volume['activeTransactions']:
            if 'transactionStatus' in trans and 'friendlyName' in trans['transactionStatus']:
                table.add_row(['Ongoing Transaction', trans['transactionStatus']['friendlyName']])

    table.add_row(['Replicant Count', "%u" % block_volume.get('replicationPartnerCount', 0)])

    if block_volume['replicationPartnerCount'] > 0:
        # This if/else temporarily handles a bug in which the SL API
        # returns a string or object for 'replicationStatus'; it seems that
        # the type is string for File volumes and object for Block volumes
        if 'message' in block_volume['replicationStatus']:
            table.add_row(['Replication Status', "%s"
                           % block_volume['replicationStatus']['message']])
        else:
            table.add_row(['Replication Status', "%s"
                           % block_volume['replicationStatus']])

        for replicant in block_volume['replicationPartners']:
            replicant_table = formatting.Table(['Name',
                                                'Value'])
            replicant_table.add_row(['Replicant Id', replicant['id']])
            replicant_table.add_row([
                'Volume Name',
                utils.lookup(replicant, 'username')])
            replicant_table.add_row([
                'Target IP',
                utils.lookup(replicant, 'serviceResourceBackendIpAddress')])
            replicant_table.add_row([
                'Data Center',
                utils.lookup(replicant,
                             'serviceResource', 'datacenter', 'name')])
            replicant_table.add_row([
                'Schedule',
                utils.lookup(replicant,
                             'replicationSchedule', 'type', 'keyname')])
            table.add_row(['Replicant Volumes', replicant_table])

    if block_volume.get('originalVolumeSize'):
        original_volume_info = formatting.Table(['Property', 'Value'])
        original_volume_info.add_row(['Original Volume Size', block_volume['originalVolumeSize']])
        if block_volume.get('originalVolumeName'):
            original_volume_info.add_row(['Original Volume Name', block_volume['originalVolumeName']])
        if block_volume.get('originalSnapshotName'):
            original_volume_info.add_row(['Original Snapshot Name', block_volume['originalSnapshotName']])
        table.add_row(['Original Volume Properties', original_volume_info])

    notes = '{}'.format(block_volume.get('notes', ''))
    table.add_row(['Notes', notes])

    env.fout(table)
