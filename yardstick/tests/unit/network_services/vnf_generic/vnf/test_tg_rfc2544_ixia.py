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

import os

import mock
import six
import unittest

from yardstick.common import utils
from yardstick.benchmark import contexts
from yardstick.benchmark.contexts import base as ctx_base
from yardstick.network_services.libs.ixia_libs.ixnet import ixnet_api
from yardstick.network_services.traffic_profile import base as tp_base
from yardstick.network_services.vnf_generic.vnf import tg_rfc2544_ixia


TEST_FILE_YAML = 'nsb_test_case.yaml'

NAME = "tg__1"


class TestIxiaResourceHelper(unittest.TestCase):

    def setUp(self):
        self._mock_IxNextgen = mock.patch.object(ixnet_api, 'IxNextgen')
        self.mock_IxNextgen = self._mock_IxNextgen.start()
        self.addCleanup(self._stop_mocks)

    def _stop_mocks(self):
        self._mock_IxNextgen.stop()

    def test___init___with_custom_rfc_helper(self):
        class MyRfcHelper(tg_rfc2544_ixia.IxiaRfc2544Helper):
            pass

        ixia_resource_helper = tg_rfc2544_ixia.IxiaResourceHelper(
            mock.Mock(), MyRfcHelper)
        self.assertIsInstance(ixia_resource_helper.rfc_helper, MyRfcHelper)

    def test_stop_collect_with_client(self):
        mock_client = mock.Mock()
        ixia_resource_helper = tg_rfc2544_ixia.IxiaResourceHelper(mock.Mock())
        ixia_resource_helper.client = mock_client
        ixia_resource_helper.stop_collect()
        self.assertEqual(1, ixia_resource_helper._terminated.value)

    def test_run_traffic(self):
        mock_tprofile = mock.Mock()
        mock_tprofile.config.duration = 10
        mock_tprofile.get_drop_percentage.return_value = True, 'fake_samples'
        ixia_rhelper = tg_rfc2544_ixia.IxiaResourceHelper(mock.Mock())
        ixia_rhelper.rfc_helper = mock.Mock()
        ixia_rhelper.vnfd_helper = mock.Mock()
        ixia_rhelper.vnfd_helper.port_pairs.all_ports = []
        with mock.patch.object(ixia_rhelper, 'generate_samples'), \
                mock.patch.object(ixia_rhelper, '_build_ports'), \
                mock.patch.object(ixia_rhelper, '_initialize_client'), \
                mock.patch.object(utils, 'wait_until_true'):
            ixia_rhelper.run_traffic(mock_tprofile)

        self.assertEqual('fake_samples', ixia_rhelper._queue.get())


@mock.patch.object(tg_rfc2544_ixia, 'ixnet_api')
class TestIXIATrafficGen(unittest.TestCase):
    VNFD = {'vnfd:vnfd-catalog':
            {'vnfd':
             [{'short-name': 'VpeVnf',
               'vdu':
               [{'routing_table':
                             [{'network': '152.16.100.20',
                               'netmask': '255.255.255.0',
                               'gateway': '152.16.100.20',
                               'if': 'xe0'},
                              {'network': '152.16.40.20',
                               'netmask': '255.255.255.0',
                               'gateway': '152.16.40.20',
                               'if': 'xe1'}],
                             'description': 'VPE approximation using DPDK',
                             'name': 'vpevnf-baremetal',
                             'nd_route_tbl':
                                 [{'network': '0064:ff9b:0:0:0:0:9810:6414',
                                   'netmask': '112',
                                   'gateway': '0064:ff9b:0:0:0:0:9810:6414',
                                   'if': 'xe0'},
                                  {'network': '0064:ff9b:0:0:0:0:9810:2814',
                                   'netmask': '112',
                                   'gateway': '0064:ff9b:0:0:0:0:9810:2814',
                                   'if': 'xe1'}],
                             'id': 'vpevnf-baremetal',
                             'external-interface':
                                 [{'virtual-interface':
                                   {'dst_mac': '00:00:00:00:00:04',
                                    'vpci': '0000:05:00.0',
                                    'local_ip': '152.16.100.19',
                                    'type': 'PCI-PASSTHROUGH',
                                    'netmask': '255.255.255.0',
                                    'dpdk_port_num': 0,
                                    'bandwidth': '10 Gbps',
                                    'driver': "i40e",
                                    'dst_ip': '152.16.100.20',
                                    'local_iface_name': 'xe0',
                                    'local_mac': '00:00:00:00:00:02'},
                                   'vnfd-connection-point-ref': 'xe0',
                                   'name': 'xe0'},
                                  {'virtual-interface':
                                   {'dst_mac': '00:00:00:00:00:03',
                                    'vpci': '0000:05:00.1',
                                    'local_ip': '152.16.40.19',
                                    'type': 'PCI-PASSTHROUGH',
                                    'driver': "i40e",
                                    'netmask': '255.255.255.0',
                                    'dpdk_port_num': 1,
                                    'bandwidth': '10 Gbps',
                                    'dst_ip': '152.16.40.20',
                                    'local_iface_name': 'xe1',
                                    'local_mac': '00:00:00:00:00:01'},
                                   'vnfd-connection-point-ref': 'xe1',
                                   'name': 'xe1'}]}],
               'description': 'Vpe approximation using DPDK',
               'mgmt-interface':
               {'vdu-id': 'vpevnf-baremetal',
                'host': '1.1.1.1',
                'password': 'r00t',
                            'user': 'root',
                            'ip': '1.1.1.1'},
               'benchmark':
               {'kpi': ['packets_in', 'packets_fwd',
                        'packets_dropped']},
               'connection-point': [{'type': 'VPORT', 'name': 'xe0'},
                                    {'type': 'VPORT', 'name': 'xe1'}],
               'id': 'VpeApproxVnf', 'name': 'VPEVnfSsh'}]}}

    TRAFFIC_PROFILE = {
        "schema": "isb:traffic_profile:0.1",
        "name": "fixed",
        "description": "Fixed traffic profile to run UDP traffic",
        "traffic_profile": {
            "traffic_type": "FixedTraffic",
            "frame_rate": 100,  # pps
            "flow_number": 10,
            "frame_size": 64}}

    TC_YAML = {'scenarios': [{'tc_options':
                              {'rfc2544': {'allowed_drop_rate': '0.8 - 1'}},
                              'runner': {'duration': 400,
                                         'interval': 35, 'type': 'Duration'},
                              'traffic_options':
                                  {'flow': 'ipv4_1flow_Packets_vpe.yaml',
                                   'imix': 'imix_voice.yaml'},
                              'vnf_options': {'vpe': {'cfg': 'vpe_config'}},
                              'traffic_profile': 'ipv4_throughput_vpe.yaml',
                              'type': 'NSPerf',
                              'nodes': {'tg__1': 'trafficgen_1.yardstick',
                                        'vnf__1': 'vnf.yardstick'},
                              'topology': 'vpe_vnf_topology.yaml'}],
               'context': {'nfvi_type': 'baremetal',
                           'type': contexts.CONTEXT_NODE,
                           'name': 'yardstick',
                           'file': '/etc/yardstick/nodes/pod.yaml'},
               'schema': 'yardstick:task:0.1'}

    def test___init__(self, *args):
        with mock.patch("yardstick.ssh.SSH") as ssh:
            ssh_mock = mock.Mock(autospec=ssh.SSH)
            ssh_mock.execute = \
                mock.Mock(return_value=(0, "", ""))
            ssh.from_node.return_value = ssh_mock
            vnfd = self.VNFD['vnfd:vnfd-catalog']['vnfd'][0]
            # NOTE(ralonsoh): check the object returned.
            tg_rfc2544_ixia.IxiaTrafficGen(NAME, vnfd, 'task_id')

    def test_listen_traffic(self, *args):
        with mock.patch("yardstick.ssh.SSH") as ssh:
            ssh_mock = mock.Mock(autospec=ssh.SSH)
            ssh_mock.execute = \
                mock.Mock(return_value=(0, "", ""))
            ssh.from_node.return_value = ssh_mock
            vnfd = self.VNFD['vnfd:vnfd-catalog']['vnfd'][0]
            ixnet_traffic_gen = tg_rfc2544_ixia.IxiaTrafficGen(NAME, vnfd,
                                                               'task_id')
            self.assertIsNone(ixnet_traffic_gen.listen_traffic({}))

    @mock.patch.object(ctx_base.Context, 'get_context_from_server', return_value='fake_context')
    def test_instantiate(self, *args):
        with mock.patch("yardstick.ssh.SSH") as ssh:
            ssh_mock = mock.Mock(autospec=ssh.SSH)
            ssh_mock.execute = \
                mock.Mock(return_value=(0, "", ""))
            ssh_mock.run = \
                mock.Mock(return_value=(0, "", ""))
            ssh.from_node.return_value = ssh_mock
            vnfd = self.VNFD['vnfd:vnfd-catalog']['vnfd'][0]
            ixnet_traffic_gen = tg_rfc2544_ixia.IxiaTrafficGen(NAME, vnfd,
                                                               'task_id')
            scenario_cfg = {'tc': "nsb_test_case",
                            "topology": ""}
            scenario_cfg.update(
                {
                    'options': {
                        'packetsize': 64,
                        'traffic_type': 4,
                        'rfc2544': {
                            'allowed_drop_rate': '0.8 - 1'},
                        'vnf__1': {
                            'rules': 'acl_1rule.yaml',
                            'vnf_config': {
                                'lb_config': 'SW',
                                'lb_count': 1,
                                'worker_config': '1C/1T',
                                'worker_threads': 1}}}})
            scenario_cfg.update({
                'nodes': {ixnet_traffic_gen.name: "mock"}
            })
            ixnet_traffic_gen.topology = ""
            ixnet_traffic_gen.get_ixobj = mock.MagicMock()
            ixnet_traffic_gen._ixia_traffic_gen = mock.MagicMock()
            ixnet_traffic_gen._ixia_traffic_gen._connect = mock.Mock()
            self.assertRaises(
                IOError,
                ixnet_traffic_gen.instantiate(scenario_cfg, {}))

    @mock.patch.object(ctx_base.Context, 'get_physical_node_from_server', return_value='mock_node')
    def test_collect_kpi(self, *args):
        with mock.patch("yardstick.ssh.SSH") as ssh:
            ssh_mock = mock.Mock(autospec=ssh.SSH)
            ssh_mock.execute = \
                mock.Mock(return_value=(0, "", ""))
            ssh.from_node.return_value = ssh_mock

            vnfd = self.VNFD['vnfd:vnfd-catalog']['vnfd'][0]
            ixnet_traffic_gen = tg_rfc2544_ixia.IxiaTrafficGen(NAME, vnfd,
                                                               'task_id')
            ixnet_traffic_gen.scenario_helper.scenario_cfg = {
                'nodes': {ixnet_traffic_gen.name: "mock"}
            }
            ixnet_traffic_gen.data = {}
            restult = ixnet_traffic_gen.collect_kpi()

            expected = {'collect_stats': {},
                        'physical_node': 'mock_node'}

            self.assertEqual(expected, restult)

    def test_terminate(self, *args):
        with mock.patch("yardstick.ssh.SSH") as ssh:
            vnfd = self.VNFD['vnfd:vnfd-catalog']['vnfd'][0]
            ssh_mock = mock.Mock(autospec=ssh.SSH)
            ssh_mock.execute = \
                mock.Mock(return_value=(0, "", ""))
            ssh.from_node.return_value = ssh_mock
            ixnet_traffic_gen = tg_rfc2544_ixia.IxiaTrafficGen(NAME, vnfd,
                                                               'task_id')
            ixnet_traffic_gen._terminated = mock.MagicMock()
            ixnet_traffic_gen._terminated.value = 0
            ixnet_traffic_gen._ixia_traffic_gen = mock.MagicMock()
            ixnet_traffic_gen._ixia_traffic_gen.ix_stop_traffic = mock.Mock()
            ixnet_traffic_gen._traffic_process = mock.MagicMock()
            ixnet_traffic_gen._traffic_process.terminate = mock.Mock()
            self.assertIsNone(ixnet_traffic_gen.terminate())

    def _get_file_abspath(self, filename):
        curr_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(curr_path, filename)
        return file_path

    def test__check_status(self, *args):
        vnfd = self.VNFD['vnfd:vnfd-catalog']['vnfd'][0]
        sut = tg_rfc2544_ixia.IxiaTrafficGen('vnf1', vnfd, 'task_id')
        sut._check_status()

    @mock.patch("yardstick.ssh.SSH")
    def test_traffic_runner(self, mock_ssh, *args):
        mock_traffic_profile = mock.Mock(autospec=tp_base.TrafficProfile)
        mock_traffic_profile.get_traffic_definition.return_value = "64"
        mock_traffic_profile.params = self.TRAFFIC_PROFILE
        # traffic_profile.ports is standardized on port_num
        mock_traffic_profile.ports = [0, 1]

        mock_ssh_instance = mock.Mock(autospec=mock_ssh.SSH)
        mock_ssh_instance.execute.return_value = 0, "", ""
        mock_ssh_instance.run.return_value = 0, "", ""

        mock_ssh.from_node.return_value = mock_ssh_instance

        vnfd = self.VNFD['vnfd:vnfd-catalog']['vnfd'][0]
        vnfd["mgmt-interface"].update({
            'tg-config': {
                "ixchassis": "1.1.1.1",
                "py_bin_path": "/root",
            }
        })

        samples = {}
        name = ''
        for ifname in range(1):
            name = "xe{}".format(ifname)
            samples[name] = {
                "Rx_Rate_Kbps": 20,
                "Tx_Rate_Kbps": 20,
                "Rx_Rate_Mbps": 10,
                "Tx_Rate_Mbps": 10,
                "RxThroughput": 10,
                "TxThroughput": 10,
                "Valid_Frames_Rx": 1000,
                "Frames_Tx": 1000,
                "in_packets": 1000,
                "out_packets": 1000,
            }

        samples.update({"CurrentDropPercentage": 0.0})

        last_res = [
            0,
            {
                "Rx_Rate_Kbps": [20, 20],
                "Tx_Rate_Kbps": [20, 20],
                "Rx_Rate_Mbps": [10, 10],
                "Tx_Rate_Mbps": [10, 10],
                "CurrentDropPercentage": [0, 0],
                "RxThroughput": [10, 10],
                "TxThroughput": [10, 10],
                "Frames_Tx": [1000, 1000],
                "in_packets": [1000, 1000],
                "Valid_Frames_Rx": [1000, 1000],
                "out_packets": [1000, 1000],
            },
        ]

        mock_traffic_profile.execute_traffic.return_value = [
            'Completed', samples]
        mock_traffic_profile.get_drop_percentage.return_value = [
            'Completed', samples]

        sut = tg_rfc2544_ixia.IxiaTrafficGen(name, vnfd, 'task_id')
        sut.vnf_port_pairs = [[[0], [1]]]
        sut.tc_file_name = self._get_file_abspath(TEST_FILE_YAML)
        sut.topology = ""

        sut.ssh_helper = mock.Mock()
        sut._traffic_process = mock.MagicMock()
        sut.generate_port_pairs = mock.Mock()

        sut._ixia_traffic_gen = mock.MagicMock()
        sut._ixia_traffic_gen.ix_get_statistics.return_value = last_res

        sut.resource_helper.client = mock.MagicMock()
        sut.resource_helper.client_started = mock.MagicMock()
        sut.resource_helper.client_started.value = 1
        sut.resource_helper.rfc_helper.iteration.value = 11

        sut.scenario_helper.scenario_cfg = {
            'options': {
                'packetsize': 64,
                'traffic_type': 4,
                'rfc2544': {
                    'allowed_drop_rate': '0.8 - 1',
                    'latency': True
                },
                'vnf__1': {
                    'rules': 'acl_1rule.yaml',
                    'vnf_config': {
                        'lb_config': 'SW',
                        'lb_count': 1,
                        'worker_config': '1C/1T',
                        'worker_threads': 1,
                    },
                },
            },
            'task_path': '/path/to/task'
        }

        @mock.patch.object(six.moves.builtins, 'open', create=True)
        @mock.patch('yardstick.network_services.vnf_generic.vnf.tg_rfc2544_ixia.open',
                    mock.mock_open(), create=True)
        @mock.patch('yardstick.network_services.vnf_generic.vnf.tg_rfc2544_ixia.LOG.exception')
        def _traffic_runner(*args):
            sut._setup_mq_producer = mock.Mock(return_value='mq_producer')
            result = sut._traffic_runner(mock_traffic_profile, mock.ANY)
            self.assertIsNone(result)

        _traffic_runner()
