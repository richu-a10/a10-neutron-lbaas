# Copyright 2014, Omkar Telee (omkartelee01), A10 Networks
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

import acos_client.errors as acos_errors
import handler_base_v2
import logging
import v2_context as a10

from a10_neutron_lbaas.acos import openstack_mappings
from policy import PolicyUtil

LOG = logging.getLogger(__name__)

class L7RuleHandler(handler_base_v2.HandlerBaseV2):

    def _set(self, set_method,c, context, l7policy, **kwargs):
        set_method(l7policy)

    def create(self, context, l7rule, **kwargs):
        import pdb; pdb.set_trace()
        with a10.A10WriteStatusContext(self, context, l7rule) as c:
            policyID = l7rule.l7policy_id
            
            try:
                # hardcoded for dev!!change!! policyID 
                policyTCL = c.client.slb.aflex_policy.get("custom1") 
            
            except acos_errors.Exists:
                pass

            p = PolicyUtil()
            #p.addRule(l7rule, policyTCL)
            ans = p.ruleParser(l7rule)
 
            try:
                self._set(c.client.slb.aflex_policy.create,
                          c, context, l7policy)
            except acos_errors.Exists:
                pass


