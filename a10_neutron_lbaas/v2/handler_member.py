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


import binascii
import logging
import re

from acos_client import errors as acos_errors

from a10_neutron_lbaas.v2 import handler_base_v2
from a10_neutron_lbaas.v2 import v2_context as a10

# tenant names allow some funky characters; we do not, as of 4.1.0
non_alpha = re.compile('[^0-9a-zA-Z_-]')

LOG = logging.getLogger(__name__)


class MemberHandler(handler_base_v2.HandlerBaseV2):

    def _get_name(self, member, ip_address):
        if self.a10_driver.config.get('member_name_use_uuid'):
            return member.id

        tenant_label = member.tenant_id[:5]
        if non_alpha.search(tenant_label) is not None:
            # This corner-case likely only occurs with silly unit tests
            tenant_label = binascii.hexlify(tenant_label)
        addr_label = str(ip_address).replace(".", "_", 4)
        server_name = "_%s_%s_neutron" % (tenant_label, addr_label)
        return server_name

    def _meta_name(self, member, ip_address):
        return self.meta(member, 'name', self._get_name(member, ip_address))

    def _create(self, c, context, member):
        server_ip = self.neutron.member_get_ip(context, member,
                                               c.device_cfg['use_float'])
        server_name = self._meta_name(member, server_ip)
        conn_limit = c.device_cfg.get('conn-limit')
        conn_resume = c.device_cfg.get('conn-resume')
        status = c.client.slb.UP
        if not member.admin_state_up:
            status = c.client.slb.DOWN
        os_name = member.name

        try:
            server_args = self.meta(member, 'server', {})
            if conn_limit is not None:
                server_args['conn-limit'] = conn_limit

            if conn_resume is not None:
                server_args['conn-resume'] = conn_resume

            server_args = {'server': server_args}

            conf_templates = c.device_cfg.get('templates')
            if conf_templates:
                server_templates = conf_templates.get("server", None)
            else:
                server_templates = None

            c.client.slb.server.create(server_name, server_ip,
                                       status=status,
                                       server_templates=server_templates,
                                       config_defaults=self._get_config_defaults(c, os_name),
                                       axapi_args=server_args)

        except (acos_errors.Exists, acos_errors.AddressSpecifiedIsInUse):
            pass

        try:
            member_args = {'member': self.meta(member, 'member', {})}
            c.client.slb.service_group.member.create(
                self._pool_name(context, pool=member.pool),
                server_name,
                member.protocol_port,
                status=status,
                axapi_args=member_args)
        except acos_errors.Exists:
            pass

    def create(self, context, member):
        with a10.A10WriteStatusContext(self, context, member) as c:
            self._create(c, context, member)
            self.hooks.after_member_create(c, context, member)

    def update(self, context, old_member, member):
        with a10.A10WriteStatusContext(self, context, member) as c:
            server_ip = self.neutron.member_get_ip(context, member,
                                                   c.device_cfg['use_float'])
            server_name = self._meta_name(member, server_ip)

            status = c.client.slb.UP
            if not member.admin_state_up:
                status = c.client.slb.DOWN

            try:
                member_args = {'member': self.meta(member, 'member', {})}
                c.client.slb.service_group.member.update(
                    self._pool_name(context, pool=member.pool),
                    server_name,
                    member.protocol_port,
                    status,
                    axapi_args=member_args)
            except acos_errors.NotFound:
                # Adding db relation after the fact
                self._create(c, context, member)

            self.hooks.after_member_update(c, context, member)

    def _delete(self, c, context, member):
        server_ip = self.neutron.member_get_ip(
            context, member, c.device_cfg['use_float'])
        server_name = self._meta_name(member, server_ip)

        try:
            c.client.slb.server.port.delete(server_name, member.protocol_port, 'TCP')
            if self.neutron.member_count(context, member) > 1:
                c.client.slb.service_group.member.delete(
                    self._pool_name(context, pool_id=member.pool_id, pool=member.pool),
                    server_name,
                    member.protocol_port)
            else:
                c.client.slb.server.delete(server_name)
        except acos_errors.NotFound:
            pass

        self.hooks.after_member_delete(c, context, member)

    def delete(self, context, member):
        with a10.A10DeleteContext(self, context, member) as c:
            self._delete(c, context, member)

    def stats(self, context, member):
        retval = {
            "servers_up": 0,
            "servers_down": 0,
            "servers_disable": 0,
            "servers_total": 0
        }

        try:
            with a10.A10Context(self, context, member) as c:
                server_ip = self.neutron.member_get_ip(context, member,
                                                       c.device_cfg['use_float'])
                server_name = self._meta_name(member, server_ip)

                stats = c.client.slb.service_group.member.stats(name=server_name)
                retval = stats

        except Exception as ex:
            LOG.exception(ex)
        finally:
            pass

        return retval

    def _get_expressions(self, c):
        rv = {}
        rv = c.a10_driver.config.get_member_expressions()
        return rv
