# Copyright 2014, Doug Wiegley (dougwig), A10 Networks
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import mock

from a10_neutron_lbaas.tests.unit import test_base

from a10_neutron_lbaas.plumbing import portbinding_vlan

from neutron.db.models.segment import NetworkSegment, SegmentHostMapping                                  
from neutron.db.models_v2 import IPAllocation, IPAllocationPool, Route, SubnetRoute, Port, Subnet, Network
from neutron.plugins.ml2.models import PortBinding, PortBindingLevel                                      

class FakeConfig(object):
    def __init__(self, *args, **kwargs):
        self._dict = kwargs

    def get(self, key):
        return self._dict.get(key)

class TestVlanPortBindingPlumbing(test_base.UnitTestBase):
    version = "v2"

    def setUp(self, *args, **kwargs):
        super(TestVlanPortBindingPlumbing, self).setUp(*args, **kwargs)
        self._subnet_id = "mysubnet"
        self._port_id = "portid"
        self._segment_id = "mysegment" 
        self._vlan_id = 2000
        self._network_id = "mynetwork"
        self._level = 1

        self._binding_level = mock.Mock(level=1, segment_id=self._segment_id)
        self._segment = mock.Mock(id=self._segment_id, segmentation_id=self._vlan_id)
        self._build_mocks()
        self.target = portbinding_vlan.VlanPortBindingPlumbingHooks(self._driver, self._devices)

    def test_select_device(self):
        a = self.target.select_device("first-token")
        self.target.select_device("second-token")
        self.assertEqual(a, self.target.select_device("first-token"))

    def test_after_vip_create(self):
        self.target.after_vip_create(self.a10_context, self.os_context, self._vip)

    def _build_mocks(self):
        # a10_context dependencies
        self._vip = mock.Mock(vip_subnet_id="mysubnet", vip_port=mock.Mock(id=self._port_id, network_id=self._network_id))
        self._devices = {"a": {"host": "1.2.3.4", "api_version": "3.0"}}
        self._driver=mock.Mock()
        self._client = self._build_client() 
        self._config = FakeConfig(
            use_database=False,
            interfaces = {
                "tagged_trunks": [1,2],
            },
            use_dhcp = False,
            vlan_binding_level=self._level
        ) 
        self._a10_driver = mock.Mock(config=self._config)
        self.a10_context = mock.Mock(a10_driver=self._a10_driver,client=self._client)
        self._session = self._build_session() 
        self.os_context = mock.Mock(session=self._session,tenant_id="tenant")

    def _build_session(self, **kwargs):
        rv = mock.Mock()
        # rv.query(PortBindingLevel).filter_by(port_id=self._port_id, level=self._level).first().return_value = self._binding_level
        # rv.query(NetworkSegment).filter_by(id=self._segment_id).first().return_value = self._segment
        # rv.configure_mock(**mock_cfg)
        rv.session.query.filter.first.return_value = self._binding_level
        return rv

    def _build_client(self):
        rval = mock.Mock()
        ve_json = '{"ve":{"oper":{"state":"DOWN","line_protocol":"DOWN","link_type":"VirtualEthernet","mac":"ffff.ffff.78de"},"a10-url":"/axapi/v3/interface/ve/255/oper","ifnum":5}}'
        rval.interface.ve.get_oper = lambda x: json.loads(ve_json)
        rval.interface.ve.get = lambda : {}
    
        return rval

