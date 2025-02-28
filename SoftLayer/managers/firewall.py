"""
    SoftLayer.firewall
    ~~~~~~~~~~~~~~~~~~
    Firewall Manager/helpers

    :license: MIT, see LICENSE for more details.
"""
from SoftLayer import exceptions
from SoftLayer import utils

RULE_MASK = ('mask[orderValue,action,destinationIpAddress,'
             'destinationIpSubnetMask,protocol,destinationPortRangeStart,'
             'destinationPortRangeEnd,sourceIpAddress,sourceIpSubnetMask,'
             'version,notes]')


def has_firewall(vlan):
    """Helper to determine whether or not a VLAN has a firewall.

    :param dict vlan: A dictionary representing a VLAN
    :returns: True if the VLAN has a firewall, false if it doesn't.
    """
    return bool(
        vlan.get('dedicatedFirewallFlag', None) or
        vlan.get('highAvailabilityFirewallFlag', None) or
        vlan.get('firewallInterfaces', None) or
        vlan.get('firewallNetworkComponents', None) or
        vlan.get('firewallGuestNetworkComponents', None)
    )


class FirewallManager(utils.IdentifierMixin, object):
    """Manages SoftLayer firewalls

    See product information here: https://www.ibm.com/cloud/network-security

    :param SoftLayer.API.BaseClient client: the client instance

    """

    def __init__(self, client):
        self.client = client
        self.account = self.client['Account']
        self.prod_pkg = self.client['Product_Package']

    def get_standard_package(self, server_id, is_virt=True):
        """Retrieves the standard firewall package for the virtual server.

        :param int server_id: The ID of the server to create the firewall for
        :param bool is_virt: True if the ID provided is for a virtual server,
                             False for a server
        :returns: A dictionary containing the standard virtual server firewall
                  package
        """

        firewall_port_speed = self._get_fwl_port_speed(server_id, is_virt)

        _value = "%s%s" % (firewall_port_speed, "Mbps Hardware Firewall")
        _filter = {'items': {'description': utils.query_filter(_value)}}

        return self.prod_pkg.getItems(id=0, filter=_filter)

    def get_dedicated_package(self, ha_enabled=False):
        """Retrieves the dedicated firewall package.

        :param bool ha_enabled: True if HA is to be enabled on the firewall
                                False for No HA
        :returns: A dictionary containing the dedicated virtual server firewall
                  package
        """

        fwl_filter = 'Hardware Firewall (Dedicated)'
        ha_fwl_filter = 'Hardware Firewall (High Availability)'
        _filter = utils.NestedDict({})
        if ha_enabled:
            _filter['items']['description'] = utils.query_filter(ha_fwl_filter)
        else:
            _filter['items']['description'] = utils.query_filter(fwl_filter)

        return self.prod_pkg.getItems(id=0, filter=_filter.to_dict())

    def cancel_firewall(self, firewall_id, dedicated=False):
        """Cancels the specified firewall.

        :param int firewall_id: Firewall ID to be cancelled.
        :param bool dedicated: If true, the firewall instance is dedicated,
                               otherwise, the firewall instance is shared.
        """

        fwl_billing = self._get_fwl_billing_item(firewall_id, dedicated)
        billing_item_service = self.client['Billing_Item']
        return billing_item_service.cancelService(id=fwl_billing['id'])

    def add_standard_firewall(self, server_id, is_virt=True):
        """Creates a firewall for the specified virtual/hardware server.

        :param int server_id: The ID of the server to create the firewall for
        :param bool is_virt: If true, will create the firewall for a virtual
                             server, otherwise for a hardware server.
        :returns: A dictionary containing the standard virtual server firewall
                  order
        """

        package = self.get_standard_package(server_id, is_virt)
        if is_virt:
            product_order = {
                'complexType': 'SoftLayer_Container_Product_Order_Network_'
                               'Protection_Firewall',
                'quantity': 1,
                'packageId': 0,
                'virtualGuests': [{'id': server_id}],
                'prices': [{'id': package[0]['prices'][0]['id']}]
            }
        else:
            product_order = {
                'complexType': 'SoftLayer_Container_Product_Order_Network_'
                               'Protection_Firewall',
                'quantity': 1,
                'packageId': 0,
                'hardware': [{'id': server_id}],
                'prices': [{'id': package[0]['prices'][0]['id']}]
            }
        return self.client['Product_Order'].placeOrder(product_order)

    def add_vlan_firewall(self, vlan_id, ha_enabled=False):
        """Creates a firewall for the specified vlan.

        :param int vlan_id: The ID of the vlan to create the firewall for
        :param bool ha_enabled: If True, an HA firewall will be created

        :returns: A dictionary containing the VLAN firewall order
        """

        package = self.get_dedicated_package(ha_enabled)
        product_order = {
            'complexType': 'SoftLayer_Container_Product_Order_Network_'
                           'Protection_Firewall_Dedicated',
            'quantity': 1,
            'packageId': 0,
            'vlanId': vlan_id,
            'prices': [{'id': package[0]['prices'][0]['id']}]
        }
        return self.client['Product_Order'].placeOrder(product_order)

    def _get_fwl_billing_item(self, firewall_id, dedicated=False):
        """Retrieves the billing item of the firewall.

        :param int firewall_id: Firewall ID to get the billing item for
        :param bool dedicated: whether the firewall is dedicated or standard
        :returns: A dictionary of the firewall billing item.
        """

        mask = 'mask[id,billingItem[id]]'
        if dedicated:
            firewall_service = self.client['Network_Vlan_Firewall']
        else:
            firewall_service = self.client['Network_Component_Firewall']
        firewall = firewall_service.getObject(id=firewall_id, mask=mask)
        if firewall is None:
            raise exceptions.SoftLayerError(
                "Unable to find firewall %d" % firewall_id)
        if firewall.get('billingItem') is None:
            raise exceptions.SoftLayerError(
                "Unable to find billing item for firewall %d" % firewall_id)

        return firewall['billingItem']

    def _get_fwl_port_speed(self, server_id, is_virt=True):
        """Determines the appropriate speed for a firewall.

        :param int server_id: The ID of server the firewall is for
        :param bool is_virt: True if the server_id is for a virtual server
        :returns: a integer representing the Mbps speed of a firewall
        """

        fwl_port_speed = 0
        if is_virt:
            mask = ('primaryNetworkComponent[maxSpeed]')
            svc = self.client['Virtual_Guest']
            primary = svc.getObject(mask=mask, id=server_id)
            fwl_port_speed = primary['primaryNetworkComponent']['maxSpeed']
        else:
            mask = ('id,maxSpeed,networkComponentGroup.networkComponents')
            svc = self.client['Hardware_Server']
            network_components = svc.getFrontendNetworkComponents(
                mask=mask, id=server_id)
            grouped = [interface['networkComponentGroup']['networkComponents']
                       for interface in network_components
                       if 'networkComponentGroup' in interface]
            ungrouped = [interface
                         for interface in network_components
                         if 'networkComponentGroup' not in interface]

            # For each group, sum the maxSpeeds of each compoment in the
            # group. Put the sum for each in a new list
            group_speeds = []
            for group in grouped:
                group_speed = 0
                for interface in group:
                    group_speed += interface['maxSpeed']
                group_speeds.append(group_speed)

            # The max speed of all groups is the max of the list
            max_grouped_speed = max(group_speeds)

            max_ungrouped = 0
            for interface in ungrouped:
                max_ungrouped = max(max_ungrouped, interface['maxSpeed'])

            fwl_port_speed = max(max_grouped_speed, max_ungrouped)

        return fwl_port_speed

    def get_firewalls(self):
        """Returns a list of all firewalls on the account.

        :returns: A list of firewalls on the current account.
        """

        mask = ('firewallNetworkComponents,'
                'networkVlanFirewall,'
                'dedicatedFirewallFlag,'
                'firewallGuestNetworkComponents,'
                'firewallInterfaces,'
                'firewallRules,'
                'highAvailabilityFirewallFlag')

        return [firewall
                for firewall in self.account.getNetworkVlans(mask=mask)
                if has_firewall(firewall)]

    def get_standard_fwl_rules(self, firewall_id):
        """Get the rules of a standard firewall.

        :param integer firewall_id: the instance ID of the standard firewall
        :returns: A list of the rules.
        """

        svc = self.client['Network_Component_Firewall']
        return svc.getRules(id=firewall_id, mask=RULE_MASK)

    def get_dedicated_fwl_rules(self, firewall_id):
        """Get the rules of a dedicated firewall.

        :param integer firewall_id: the instance ID of the dedicated firewall
        :returns: A list of the rules.
        """

        svc = self.client['Network_Vlan_Firewall']
        return svc.getRules(id=firewall_id, mask=RULE_MASK)

    def edit_dedicated_fwl_rules(self, firewall_id, rules):
        """Edit the rules for dedicated firewall.

        :param integer firewall_id: the instance ID of the dedicated firewall
        :param list rules: the rules to be pushed on the firewall as defined by
                           SoftLayer_Network_Firewall_Update_Request_Rule
        """

        mask = ('mask[networkVlan[firewallInterfaces'
                '[firewallContextAccessControlLists]]]')
        svc = self.client['Network_Vlan_Firewall']
        fwl = svc.getObject(id=firewall_id, mask=mask)
        network_vlan = fwl['networkVlan']

        for fwl1 in network_vlan['firewallInterfaces']:
            if fwl1['name'] == 'inside':
                continue

            for control_list in fwl1['firewallContextAccessControlLists']:
                if control_list['direction'] == 'out':
                    continue
                fwl_ctx_acl_id = control_list['id']

        template = {'firewallContextAccessControlListId': fwl_ctx_acl_id,
                    'rules': rules}

        svc = self.client['Network_Firewall_Update_Request']
        return svc.createObject(template)

    def edit_standard_fwl_rules(self, firewall_id, rules):
        """Edit the rules for standard firewall.

        :param integer firewall_id: the instance ID of the standard firewall
        :param list rules: the rules to be pushed on the firewall as defined by
                           SoftLayer_Network_Firewall_Update_Request_Rule
        """

        rule_svc = self.client['Network_Firewall_Update_Request']
        template = {'networkComponentFirewallId': firewall_id, 'rules': rules}

        return rule_svc.createObject(template)

    def get_instance(self, firewall_id, mask=None):
        """Get the firewall information

        :param integer firewall_id: the instance ID of the standard firewall
        """
        if not mask:
            mask = 'mask[firewallType,datacenter,managementCredentials,networkVlan,' \
                   'metricTrackingObject[data,type],networkGateway[insideVlans,members,privateIpAddress,' \
                   'publicIpAddress,publicIpv6Address,privateVlan,publicVlan,status]]'

        svc = self.client['Network_Vlan_Firewall']

        return svc.getObject(id=firewall_id, mask=mask)

    def get_firewalls_gatewalls(self):
        """Returns a list of all gateway firewalls (gatewalls) on the account.

        returns: A list of gateway firewalls (gatewalls) on the current account.
        """
        mask = 'mask[id,networkSpace,name,' \
               'networkFirewall[id,firewallType,datacenter[name]],' \
               'status[keyName],' \
               'insideVlans[id],' \
               'privateIpAddress[ipAddress],' \
               'publicVlan[id,primaryRouter[hostname]],' \
               'publicIpAddress[ipAddress],members[id,hardware[hostname]]]'
        _filter = {"networkGateways": {"networkFirewall": {"operation": "not null"}}}

        return self.account.getNetworkGateways(mask=mask, filter=_filter)

    def get_summary(self, identifier, start_date, end_date):
        """Returns the metric data for the date range provided

        :param integer metric_tracking_id
        """
        body = [{
            "keyName": "PUBLICIN",
            "summaryType": "sum"

        }, {
            "keyName": "PUBLICOUT",
            "summaryType": "sum"
        }]

        return self.client['Metric_Tracking_Object'].getSummaryData(start_date,
                                                                    end_date, body, 86400, id=identifier)
