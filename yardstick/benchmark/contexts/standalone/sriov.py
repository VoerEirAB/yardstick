# Copyright (c) 2016-2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
import os
import logging
import collections

from yardstick import ssh
from yardstick.benchmark import contexts
from yardstick.benchmark.contexts import base
from yardstick.benchmark.contexts.standalone import model
from yardstick.network_services.utils import get_nsb_option
from yardstick.network_services.utils import PciAddress

LOG = logging.getLogger(__name__)


class SriovContext(base.Context):
    """ This class handles SRIOV standalone nodes - VM running on Non-Managed NFVi
    Configuration: sr-iov
    """

    __context_type__ = contexts.CONTEXT_STANDALONESRIOV

    def __init__(self):
        self.file_path = None
        self.sriov = []
        self.first_run = True
        self.dpdk_devbind = os.path.join(get_nsb_option('bin_path'),
                                         'dpdk-devbind.py')
        self.vm_names = []
        self.nfvi_host = []
        self.nodes = []
        self.networks = {}
        self.attrs = {}
        self.vm_flavor = None
        self.servers = None
        self.helper = model.StandaloneContextHelper()
        self.vnf_node = model.Server()
        self.drivers = []
        super(SriovContext, self).__init__()

    def init(self, attrs):
        """initializes itself from the supplied arguments"""
        super(SriovContext, self).init(attrs)

        self.file_path = attrs.get("file", "pod.yaml")

        self.nodes, self.nfvi_host, self.host_mgmt = \
            self.helper.parse_pod_file(self.file_path, 'Sriov')

        self.attrs = attrs
        self.vm_flavor = attrs.get('flavor', {})
        self.servers = attrs.get('servers', {})
        self.vm_deploy = attrs.get("vm_deploy", True)
        # add optional static network definition
        self.networks = attrs.get("networks", {})

        LOG.debug("Nodes: %r", self.nodes)
        LOG.debug("NFVi Node: %r", self.nfvi_host)
        LOG.debug("Networks: %r", self.networks)

    def deploy(self):
        """don't need to deploy"""

        # Todo: NFVi deploy (sriov, vswitch, ovs etc) based on the config.
        if not self.vm_deploy:
            return

        self.connection = ssh.SSH.from_node(self.host_mgmt)

        #    Todo: NFVi deploy (sriov, vswitch, ovs etc) based on the config.
        model.StandaloneContextHelper.install_req_libs(self.connection)
        self.networks = model.StandaloneContextHelper.get_nic_details(
            self.connection, self.networks, self.dpdk_devbind)
        self.nodes = self.setup_sriov_context()

        LOG.debug("Waiting for VM to come up...")
        self.nodes = model.StandaloneContextHelper.wait_for_vnfs_to_start(
            self.connection, self.servers, self.nodes)

    def undeploy(self):
        """don't need to undeploy"""

        if not self.vm_deploy:
            return

        # Todo: NFVi undeploy (sriov, vswitch, ovs etc) based on the config.
        for vm in self.vm_names:
            model.Libvirt.check_if_vm_exists_and_delete(vm, self.connection)

        # Bind nics back to kernel
        for ports in self.networks.values():
            # enable VFs for given...
            build_vfs = "echo 0 > /sys/bus/pci/devices/{0}/sriov_numvfs"
            self.connection.execute(build_vfs.format(ports.get('phy_port')))

    def _get_physical_nodes(self):
        return self.nfvi_host

    def _get_physical_node_for_server(self, server_name):

        # self.nfvi_host always contain only one host.
        node_name, ctx_name = self.split_host_name(server_name)
        if ctx_name is None or self.name != ctx_name:
            return None

        matching_nodes = [s for s in self.servers if s == node_name]
        if len(matching_nodes) == 0:
            return None

        return "{}.{}".format(self.nfvi_host[0]["name"], self._name)

    def _get_server(self, attr_name):
        """lookup server info by name from context

        Keyword arguments:
        attr_name -- A name for a server listed in nodes config file
        """
        node_name, name = self.split_host_name(attr_name)
        if name is None or self.name != name:
            return None

        matching_nodes = (n for n in self.nodes if n["name"] == node_name)
        try:
            # A clone is created in order to avoid affecting the
            # original one.
            node = dict(next(matching_nodes))
        except StopIteration:
            return None

        try:
            duplicate = next(matching_nodes)
        except StopIteration:
            pass
        else:
            raise ValueError("Duplicate nodes!!! Nodes: %s %s"
                             % (node, duplicate))

        node["name"] = attr_name
        return node

    def _get_network(self, attr_name):
        if not isinstance(attr_name, collections.Mapping):
            network = self.networks.get(attr_name)

        else:
            # Don't generalize too much  Just support vld_id
            vld_id = attr_name.get('vld_id', {})
            # for standalone context networks are dicts
            iter1 = (n for n in self.networks.values() if n.get('vld_id') == vld_id)
            network = next(iter1, None)

        if network is None:
            return None

        result = {
            # name is required
            "name": network["name"],
            "vld_id": network.get("vld_id"),
            "segmentation_id": network.get("segmentation_id"),
            "network_type": network.get("network_type"),
            "physical_network": network.get("physical_network"),
        }
        return result

    def configure_nics_for_sriov(self):
        vf_cmd = "ip link set {0} vf 0 mac {1}"
        for ports in self.networks.values():
            host_driver = ports.get('driver')
            if host_driver not in self.drivers:
                self.connection.execute("rmmod %svf" % host_driver)
                self.drivers.append(host_driver)

            # enable VFs for given...
            build_vfs = "echo 1 > /sys/bus/pci/devices/{0}/sriov_numvfs"
            self.connection.execute(build_vfs.format(ports.get('phy_port')))

            # configure VFs...
            mac = model.StandaloneContextHelper.get_mac_address()
            interface = ports.get('interface')
            if interface is not None:
                self.connection.execute(vf_cmd.format(interface, mac))

            vf_pci = self._get_vf_data(ports.get('phy_port'), mac, interface)
            ports.update({
                'vf_pci': vf_pci,
                'mac': mac
            })

        LOG.info('Ports %s', self.networks)

    def _enable_interfaces(self, index, idx, vfs, cfg):
        vf_spoofchk = "ip link set {0} vf 0 spoofchk off"

        vf = self.networks[vfs[0]]
        vpci = PciAddress(vf['vpci'].strip())
        # Generate the vpci for the interfaces
        slot = index + idx + 10
        vf['vpci'] = \
            "{}:{}:{:02x}.{}".format(vpci.domain, vpci.bus, slot, vpci.function)
        self.connection.execute("ifconfig %s up" % vf['interface'])
        self.connection.execute(vf_spoofchk.format(vf['interface']))
        return model.Libvirt.add_sriov_interfaces(
            vf['vpci'], vf['vf_pci']['vf_pci'], vf['mac'], str(cfg))

    def setup_sriov_context(self):
        nodes = []

        #   1 : modprobe host_driver with num_vfs
        self.configure_nics_for_sriov()

        for index, (key, vnf) in enumerate(collections.OrderedDict(
                self.servers).items()):
            cfg = '/tmp/vm_sriov_%s.xml' % str(index)
            vm_name = "vm-%s" % str(index)
            cdrom_img = "/var/lib/libvirt/images/cdrom-%d.img" % index

            # 1. Check and delete VM if already exists
            model.Libvirt.check_if_vm_exists_and_delete(vm_name,
                                                        self.connection)
            xml_str, mac = model.Libvirt.build_vm_xml(
                self.connection, self.vm_flavor, vm_name, index, cdrom_img)

            # 2: Cleanup already available VMs
            network_ports = collections.OrderedDict(
                {k: v for k, v in vnf["network_ports"].items() if k != 'mgmt'})
            for idx, vfs in enumerate(network_ports.values()):
                xml_str = self._enable_interfaces(index, idx, vfs, xml_str)

            # copy xml to target...
            model.Libvirt.write_file(cfg, xml_str)
            self.connection.put(cfg, cfg)

            node = self.vnf_node.generate_vnf_instance(self.vm_flavor,
                                                       self.networks,
                                                       self.host_mgmt.get('ip'),
                                                       key, vnf, mac)
            # Generate public/private keys if password or private key file is not provided
            node = model.StandaloneContextHelper.check_update_key(self.connection,
                                                                  node,
                                                                  vm_name,
                                                                  self.name,
                                                                  cdrom_img,
                                                                  mac)

            # store vnf node details
            nodes.append(node)

            # NOTE: launch through libvirt
            LOG.info("virsh create ...")
            model.Libvirt.virsh_create_vm(self.connection, cfg)

            self.vm_names.append(vm_name)

        return nodes

    def _get_vf_data(self, value, vfmac, pfif):
        vf_data = {
            "mac": vfmac,
            "pf_if": pfif
        }
        vfs = model.StandaloneContextHelper.get_virtual_devices(
            self.connection, value)
        for k, v in vfs.items():
            m = PciAddress(k.strip())
            m1 = PciAddress(value.strip())
            if m.bus == m1.bus:
                vf_data.update({"vf_pci": str(v)})
                break

        return vf_data
