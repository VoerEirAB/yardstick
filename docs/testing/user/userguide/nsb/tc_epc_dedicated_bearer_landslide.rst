.. This work is licensed under a Creative Commons Attribution 4.0 International
.. License.
.. http://creativecommons.org/licenses/by/4.0
.. (c) OPNFV, 2018 Intel Corporation.

*********************************************************
Yardstick Test Case Description: NSB EPC DEDICATED BEARER
*********************************************************

+-----------------------------------------------------------------------------+
|NSB EPC dedicated bearer test case                                           |
|                                                                             |
+--------------+--------------------------------------------------------------+
|test case id  | tc_epc_{initiator}_dedicated_bearer_landslide                |
|              |                                                              |
|              | * initiator: dedicated bearer creation initiator side could  |
|              |   be UE (ue) or Network (network).                           |
|              |                                                              |
+--------------+--------------------------------------------------------------+
|metric        | All metrics provided by Spirent Landslide traffic generator  |
|              |                                                              |
+--------------+--------------------------------------------------------------+
|test purpose  | The Spirent Landslide product provides one box solution which|
|              | allows to fully emulate all EPC network nodes including      |
|              | mobile users, network host and generate control and data     |
|              | plane traffic.                                               |
|              |                                                              |
|              | This test allows to check processing capability under        |
|              | different levels of load (number of subscriber, generated    |
|              | traffic throughput, etc.) for case when default and dedicated|
|              | bearers are creating and using for traffic transferring.     |
|              |                                                              |
|              | It's easy to replace emulated node or multiple nodes in test |
|              | topology with real node or corresponding vEPC VNF as DUT and |
|              | check it's processing capabilities under specific test case  |
|              | load conditions.                                             |
|              |                                                              |
+--------------+--------------------------------------------------------------+
|configuration | The EPC dedicated bearer test cases are listed below:        |
|              |                                                              |
|              | * tc_epc_ue_dedicated_bearer_create_landslide.yaml           |
|              | * tc_epc_network_dedicated_bearer_create_landslide.yaml      |
|              |                                                              |
|              | Test duration:                                               |
|              |                                                              |
|              | * is set as 60sec (specified in test session profile);       |
|              |                                                              |
|              | Traffic type:                                                |
|              |                                                              |
|              | * UDP;                                                       |
|              |                                                              |
|              | Packet sizes:                                                |
|              |                                                              |
|              | * 512 bytes;                                                 |
|              |                                                              |
|              | Traffic transaction rate:                                    |
|              |                                                              |
|              | * 5 trans/s.;                                                |
|              |                                                              |
|              | Number of mobile subscribers:                                |
|              |                                                              |
|              | * 20000;                                                     |
|              |                                                              |
|              | Number of default bearers per subscriber:                    |
|              |                                                              |
|              | * 1;                                                         |
|              |                                                              |
|              | Number of dedicated bearers per default bearer:              |
|              |                                                              |
|              | * 1.                                                         |
|              |                                                              |
|              | The above fields and values are the main options used for the|
|              | test case. Other configurable options could be found in test |
|              | session profile yaml file. All these options have default    |
|              | values which can be overwritten in test case file.           |
|              |                                                              |
+--------------+--------------------------------------------------------------+
|test tool     | Spirent Landslide                                            |
|              |                                                              |
|              | The Spirent Landslide is a tool for functional and           |
|              | performance testing of different types of mobile networks.   |
|              | It emulates real-world control and data traffic of mobile    |
|              | subscribers moving through virtualized EPC network.          |
|              | Detailed description of Spirent Landslide product could be   |
|              | found here: https://www.spirent.com/Products/Landslide       |
|              |                                                              |
+--------------+--------------------------------------------------------------+
|applicability | This EPC DEDICATED BEARER test cases can be configured with  |
|              | different:                                                   |
|              |                                                              |
|              |  * packet sizes;                                             |
|              |  * traffic transaction rate;                                 |
|              |  * number of subscribers sessions;                           |
|              |  * number of default bearers per subscriber;                 |
|              |  * number of dedicated bearers per default;                  |
|              |  * subscribers connection rate;                              |
|              |  * subscribers disconnection rate;                           |
|              |  * dedicated bearers activation timeout;                     |
|              |  * DMF (traffic profile);                                    |
|              |  * enable/disable Fireball DMF threading model that provides |
|              |    optimized performance;                                    |
|              |                                                              |
|              | Default values exist.                                        |
|              |                                                              |
+--------------+--------------------------------------------------------------+
|references    | ETSI-NFV-TST001                                              |
|              |                                                              |
|              | 3GPP TS 32.455                                               |
|              |                                                              |
+--------------+--------------------------------------------------------------+
| pre-test     | * All Spirent Landslide dependencies need to be installed.   |
| conditions   |   The steps are described in NSB installation chapter for the|
|              |   Spirent Landslide vEPC tests;                              |
|              |                                                              |
|              | * The pod.yaml file contains all necessary information (TAS  |
|              |   VM IP address, NICs, emulated SUTs and Test Nodes          |
|              |   parameters (names, types, ip addresses, etc.).             |
|              |                                                              |
+--------------+--------------------------------------------------------------+
|test sequence | description and expected result                              |
|              |                                                              |
+--------------+--------------------------------------------------------------+
|step 1        | Spirent Landslide components are running on the hosts        |
|              | specified in the pod file.                                   |
|              |                                                              |
+--------------+--------------------------------------------------------------+
|step 2        | Yardstick is connected with Spirent Landslide Test           |
|              | Administrator Server (TAS) by TCL and REST API. The test     |
|              | will resolve the topology and instantiate all emulated EPC   |
|              | network nodes.                                               |
|              |                                                              |
+--------------+--------------------------------------------------------------+
|step 3        | Test scenarios run, which performs the following steps:      |
|              |                                                              |
|              | * Start the emulated EPC network nodes;                      |
|              | * Establish the subscribers connections to EPC network       |
|              |   (default bearers);                                         |
|              | * Establish the number of dedicated bearers as per per       |
|              |   default bearer for each subscriber;                        |
|              | * Create the sessions and transmit traffic through EPC       |
|              |   network nodes during the specified traffic duration time;  |
|              | * Disconnect dedicated bearers;                              |
|              | * Disconnect subscribers at the end of the test.             |
|              |                                                              |
+--------------+--------------------------------------------------------------+
|step 4        | During test run, all the metrics provided by Spirent         |
|              | Landslide are stored in the yardstick dispatcher.            |
|              |                                                              |
+--------------+--------------------------------------------------------------+
|test verdict  | The test case will create the test session in Spirent        |
|              | Landslide with the test case parameters and store the results|
|              | in the database for benchmarking purposes. The aim is only   |
|              | to collect all the metrics that are provided by Spirent      |
|              | Landslide product for each test specific scenario.           |
|              |                                                              |
+--------------+--------------------------------------------------------------+
