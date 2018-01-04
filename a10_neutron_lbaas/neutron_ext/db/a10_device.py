# Copyright 2015,  A10 Networks
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

import logging
import uuid

from a10_openstack_lib.resources import a10_device as a10_device_resources
from neutron.db import common_db_mixin
from neutron.api.v2.base import Controller
from sqlalchemy.orm.exc import NoResultFound

from a10_neutron_lbaas import a10_config
from a10_neutron_lbaas.db import models
from a10_neutron_lbaas.neutron_ext.common import resources
from a10_neutron_lbaas.neutron_ext.extensions import a10Device
from neutron.api.v2 import resource_helper

from a10_neutron_lbaas.neutron_ext.common import attributes
from a10_neutron_lbaas.neutron_ext.common import constants


LOG = logging.getLogger(__name__)


def _uuid_str():
    return str(uuid.uuid4())


class A10DeviceDbMixin(common_db_mixin.CommonDbMixin,
                       a10Device.A10DevicePluginBase):

    def __init__(self, *args, **kwargs):
        super(A10DeviceDbMixin, self).__init__(*args, **kwargs)
        self.config = a10_config.A10Config()

    def _get_device_body(self, a10_device):
        body = a10_device[a10_device_resources.DEVICE]
        return resources.remove_attributes_not_specified(body)

    def _get_a10_device(self, context, a10_device_id):
        with context.session.begin(subtransactions=True):
            try:
                device_value_object_list = context.session.query(models.A10Device).filter_by(
                    id=a10_device_id).one()
            except NoResultFound:
                raise a10Device.A10DeviceNotFoundError(a10_device_id)
            return device_value_object_list

    def _rebuild_resources(self, resource_map):
        my_plurals = resource_helper.build_plural_mappings(
            {}, resource_map)
        attributes.PLURALS.update(my_plurals)
        resources = resource_helper.build_resource_info(my_plurals,
                                                        resource_map,
                                                        constants.A10_DEVICE)
        return resources

    def _make_a10_device_dict(self, a10_device_db, fields=None):
        res = {'id': a10_device_db.id,
               'name': a10_device_db.name,
               'description': a10_device_db.description,
               'tenant_id': a10_device_db.tenant_id,
               'username': a10_device_db.username,
               'password': a10_device_db.password,
               'api_version': a10_device_db.api_version,
               'protocol': a10_device_db.protocol,
               'port': a10_device_db.port,
               'autosnat': a10_device_db.autosnat,
               'v_method': a10_device_db.v_method,
               'shared_partition': a10_device_db.shared_partition,
               'use_float': a10_device_db.use_float,
               'default_virtual_server_vrid': a10_device_db.default_virtual_server_vrid,
               'ipinip': a10_device_db.ipinip,
               # Not all device records are nova instances
               'nova_instance_id': a10_device_db.nova_instance_id,
               'host': a10_device_db.host,
               'write_memory': a10_device_db.write_memory,
               'extra_resources': []
              }

        for device_value in a10_device_db.config:
            key = device_value.associated_key.name
            value = device_value.value
            mapped_resource = {
                'allow_post': True,
                'allow_put': True,
                'validate': {
                    'type:string': None,
                },
                'is_visible': True,
                'default': str(value)
            }
            res[str(key)] = str(value)
            res['extra_resources'].append({str(key): mapped_resource})
        return self._fields(res, fields)

    def create_a10_device(self, context, a10_device):
        body = self._get_device_body(a10_device)
        with context.session.begin(subtransactions=True):
            device_record = models.A10Device(
                id=_uuid_str(),
                tenant_id=context.tenant_id,
                name=body.get('name', ''),
                description=body.get('description', ''),
                username=body['username'],
                password=body['password'],
                api_version=body['api_version'],
                protocol=body['protocol'],
                port=body['port'],
                autosnat=body['autosnat'],
                v_method=body['v_method'],
                shared_partition=body['shared_partition'],
                use_float=body['use_float'],
                default_virtual_server_vrid=body['default_virtual_server_vrid'],
                ipinip=body['ipinip'],
                # Not all device records are nova instances
                nova_instance_id=body.get('nova_instance_id'),
                write_memory=body.get('write_memory', False),
                host=body['host'])
            context.session.add(device_record)

        return self._make_a10_device_dict(device_record)

    def get_a10_device(self, context, a10_device_id, fields=None):
        device = self._get_a10_device(context, a10_device_id)
        return self._make_a10_device_dict(device, fields)

    def get_a10_devices(self, context, filters=None, fields=None,
                        sorts=None, limit=None, marker=None,
                        page_reverse=False):
        LOG.debug("A10DeviceDbMixin:get_a10_devices() tenant_id=%s" %
                  (context.tenant_id))
        return self._get_collection(context, models.A10Device,
                                    self._make_a10_device_dict, filters=filters,
                                    fields=fields, sorts=sorts, limit=limit,
                                    marker_obj=marker, page_reverse=page_reverse)

    def delete_a10_device(self, context, id):
        with context.session.begin(subtransactions=True):
            LOG.debug("A10DeviceDbMixin:delete_a10_device() id=%s" %
                      (id))
            device = self._get_by_id(context, models.A10Device, id)
            context.session.delete(device)

    def update_a10_device(self, context, id, a10_device):
        with context.session.begin(subtransactions=True):
            device = self._get_by_id(context, models.A10Device,
                                       id)
            device.update(**a10_device.get("a10_device"))

            return self._make_a10_device_dict(device)

    def _get_device_key_body(self, a10_device_key):
        body = a10_device_key[a10_device_resources.DEVICE_KEY]
        return resources.remove_attributes_not_specified(body)
         
    def _get_a10_device_key(self, context, key_id):
        try:
            return self._get_by_id(context, models.A10DeviceKey, key_id)
        except Exception:
            raise a10Device.A10DeviceNotFoundError(key_id)

    def _make_a10_device_key_dict(self, a10_device_key_db, fields=None):
        res = {'id': a10_device_key_db.id,
               'tenant_id': a10_device_key_db.tenant_id,
               'name': a10_device_key_db.name,
               'description': a10_device_key_db.description}

        return self._fields(res, fields)

    def create_a10_device_key(self, context, a10_device_key):
        body = self._get_device_key_body(a10_device_key)
        with context.session.begin(subtransactions=True):
            device_key_record = models.A10DeviceKey(
                id=_uuid_str(),
                tenant_id=context.tenant_id,
                name=body.get('name', ''),
                description=body.get('description', ''))
            context.session.add(device_key_record)

        return self._make_a10_device_key_dict(device_key_record)

    def update_a10_device_key(self, context, id, a10_device_key):
        with context.session.begin(subtransactions=True):
            device_key_record = self._get_by_id(context, models.A10DeviceKey, id)
            device_key_record.update(**a10_device_key.get("a10_device_key"))

            return self._make_a10_device_key_dict(device_key_record)

    def delete_a10_device_key(self, context, id):
        with context.session.begin(subtransactions=True): 
            LOG.debug("A10DeviceDbMixin:delete_a10_device_key() id={}".format(id))
            device_key = self._get_a10_device_key(context, id)

            context.session.delete(device_key)

    def get_a10_device_key(self, context, key_id, fields=None):
        device_key = self._get_a10_device_key(context, key_id)
        return self._make_a10_device_key_dict(device_key, fields)

    def get_a10_device_keys(self, context, filters=None, fields=None,
                                 sorts=None, limit=None, marker=None,
                                 page_reverse=False):
        LOG.debug("A10DeviceDbMixin:get_a10_device_key()")
        return self._get_collection(context, models.A10DeviceKey,
                                    self._make_a10_device_key_dict, filters=filters,
                                    fields=fields, sorts=sorts, limit=limit,
                                    marker_obj=marker, page_reverse=page_reverse)

    def _get_device_value_body(self, a10_device_value):
        body = a10_device_value[a10_device_resources.DEVICE_VALUE]
        return resources.remove_attributes_not_specified(body)

    def _get_a10_device_value(self, context, value_id):
        try:
            return self._get_by_id(context, models.A10DeviceValue, value_id)
        except Exception:
            raise a10Device.A10DeviceNotFoundError(value_id)

    def _make_a10_device_value_dict(self, a10_device_value_db, fields=None):
        res = {'id': a10_device_value_db.id,
               'tenant_id': a10_device_value_db.tenant_id,
               'key_id': a10_device_value_db.key_id,
               'associated_obj_id': a10_device_value_db.associated_obj_id,
               'value': a10_device_value_db.value}

        return self._fields(res, fields)

    def _get_associated_value_list(self, context, device_id):
        with context.session.begin(subtransactions=True):
            device_value_object_list = context.session.query(models.A10DeviceValue).filter_by(
                device_id = device_id).all()
            device_value_list = []
            for value in device_value_object_list:
                device_value_list.append(self._make_a10_device_value_dict(value))
        return device_value_list

    def create_a10_device_value(self, context, a10_device_value):
        body = self._get_device_value_body(a10_device_value)
        with context.session.begin(subtransactions=True):
            device_value_record = models.A10DeviceValue(
                id=_uuid_str(),
                tenant_id=context.tenant_id,
                key_id=body.get('key_id'),
                associated_obj_id=body.get('associated_obj_id'),
                value=body.get('value', ''))
            context.session.add(device_value_record)

        return self._make_a10_device_value_dict(device_value_record)

    def update_a10_device_value(self, context, id, a10_device_value):
        with context.session.begin(subtransactions=True):
            device_value_record = self._get_by_id(context, models.A10DeviceValue, id)
            device_value_record.update(**a10_device_value.get("a10_device_value"))

            return self._make_a10_device_value_dict(device_value_record)

    def delete_a10_device_value(self, context, id):
        with context.session.begin(subtransactions=True):
            LOG.debug("A10DeviceDbMixin:delete_a10_device_value() id={}".format(id))
            device_value = self._get_a10_device_value(context, id)

            context.session.delete(device_value)

    def get_a10_device_value(self, context, value_id, fields=None):
        device_value = self._get_a10_device_value(context, value_id)
        return self._make_a10_device_value_dict(device_value, fields)

    def get_a10_device_values(self, context, filters=None, fields=None,
                                 sorts=None, limit=None, marker=None,
                                 page_reverse=False):
        LOG.debug("A10DeviceDbMixin:get_a10_device_value()")
        return self._get_collection(context, models.A10DeviceValue,
                                    self._make_a10_device_value_dict, filters=filters,
                                    fields=fields, sorts=sorts, limit=limit,
                                    marker_obj=marker, page_reverse=page_reverse)
