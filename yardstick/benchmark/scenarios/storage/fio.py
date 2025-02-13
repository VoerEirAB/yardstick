##############################################################################
# Copyright (c) 2015 Huawei Technologies Co.,Ltd.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
from __future__ import absolute_import
from __future__ import print_function

import logging

import pkg_resources
from oslo_serialization import jsonutils

import yardstick.ssh as ssh
from yardstick.benchmark.scenarios import base

LOG = logging.getLogger(__name__)


class Fio(base.Scenario):
    """Execute fio benchmark in a host

  Parameters
    filename - file name for fio workload
        type:    string
        unit:    na
        default: /home/ubuntu/data.raw
    job_file - fio job configuration file
        type:    string
        unit:    na
        default: None
    job_file_config - content of job configuration file
        type:    list
        unit:    na
        default: None
    directory - mount directoey for test volume
        type:    string
        unit:    na
        default: None
    bs - block size used for the io units
        type:    int
        unit:    bytes
        default: 4k
    iodepth - number of iobuffers to keep in flight
        type:    int
        unit:    na
        default: 1
    rw - type of io pattern [read, write, randwrite, randread, rw, randrw]
        type:    string
        unit:    na
        default: write
    rwmixwrite - percentage of a mixed workload that should be writes
        type: int
        unit: percentage
        default: 50
    ramp_time - run time before logging any performance
        type:    int
        unit:    seconds
        default: 20
    direct - whether use non-buffered I/O or not
        type:    boolean
        unit:    na
        default: 1
    size - total size of I/O for this job.
        type:    string
        unit:    na
        default: 1g
    numjobs - number of clones (processes/threads performing the same workload) of this job
        type:    int
        unit:    na
        default: 1

    Read link below for more fio args description:
        http://www.bluestop.org/fio/HOWTO.txt
    """
    __scenario_type__ = "Fio"

    TARGET_SCRIPT = "fio_benchmark.bash"

    def __init__(self, scenario_cfg, context_cfg):
        self.scenario_cfg = scenario_cfg
        self.context_cfg = context_cfg
        self.options = self.scenario_cfg["options"]
        self.setup_done = False

    def setup(self):
        """scenario setup"""
        host = self.context_cfg["host"]

        self.client = ssh.SSH.from_node(host, defaults={"user": "root"})
        self.client.wait(timeout=600)

        self.job_file = self.options.get("job_file", None)
        config_lines = self.options.get("job_file_config", None)

        if self.job_file:
            self.job_file_script = pkg_resources.resource_filename(
                "yardstick.resources", 'files/' + self.job_file)

            # copy job file to host
            self.client._put_file_shell(self.job_file_script, '~/job_file.ini')
        elif config_lines:
            LOG.debug("Job file configuration received, Fio job file will be created.")
            self.job_file = 'tmp_job_file.ini'
            self.job_file_script = pkg_resources.resource_filename(
                "yardstick.resources", 'files/' + self.job_file)
            with open(self.job_file_script, 'w') as f:
                f.write('\n'.join(str(line) for line in config_lines))

            # copy job file to host
            self.client._put_file_shell(self.job_file_script, '~/job_file.ini')
        else:
            LOG.debug("No job file configuration received, Fio will use parameters.")
            self.target_script = pkg_resources.resource_filename(
                "yardstick.benchmark.scenarios.storage", Fio.TARGET_SCRIPT)

            # copy script to host
            self.client._put_file_shell(self.target_script, '~/fio.sh')

        mount_dir = self.options.get("directory", None)

        if mount_dir:
            LOG.debug("Formating volume...")
            _, stdout, _ = self.client.execute(
                "lsblk -dps | grep -m 1 disk | awk '{print $1}'")
            block_device = stdout.strip()
            if block_device:
                 self.client.execute("sudo mkfs.ext4 %s" % block_device)
                 cmd = "sudo mkdir %s" % mount_dir
                 self.client.execute(cmd)
                 LOG.debug("Mounting volume at: %s", mount_dir)
                 cmd = "sudo mount %s %s" % (block_device, mount_dir)
                 self.client.execute(cmd)

        self.setup_done = True

    def run(self, result):
        """execute the benchmark"""
        default_args = "-ioengine=libaio -group_reporting -time_based -time_based " \
            "--output-format=json"
        timeout = 3600

        if not self.setup_done:
            self.setup()

        if self.job_file:
            cmd = "sudo fio job_file.ini --output-format=json"
        else:
            filename = self.options.get("filename", "/home/ubuntu/data.raw")
            bs = self.options.get("bs", "4k")
            iodepth = self.options.get("iodepth", "1")
            rw = self.options.get("rw", "write")
            ramp_time = self.options.get("ramp_time", 20)
            size = self.options.get("size", "1g")
            direct = self.options.get("direct", "1")
            numjobs = self.options.get("numjobs", "1")
            rwmixwrite = self.options.get("rwmixwrite", 50)
            name = "yardstick-fio"
            # if run by a duration runner
            duration_time = self.scenario_cfg["runner"].get("duration", None) \
                if "runner" in self.scenario_cfg else None
            # if run by an arithmetic runner
            arithmetic_time = self.options.get("duration", None)
            if duration_time:
                runtime = duration_time
            elif arithmetic_time:
                runtime = arithmetic_time
            else:
                runtime = 30
            # Set timeout, so that the cmd execution does not exit incorrectly
            # when the test run time is last long
            timeout = int(ramp_time) + int(runtime) + 600

            cmd_args = "-filename=%s -direct=%s -bs=%s -iodepth=%s -rw=%s -rwmixwrite=%s " \
                       "-size=%s -ramp_time=%s -numjobs=%s -runtime=%s -name=%s %s" \
                       % (filename, direct, bs, iodepth, rw, rwmixwrite, size, ramp_time, numjobs,
                          runtime, name, default_args)
            cmd = "sudo bash fio.sh %s %s" % (filename, cmd_args)

        LOG.debug("Executing command: %s", cmd)
        status, stdout, stderr = self.client.execute(cmd, timeout=timeout)
        if status:
            raise RuntimeError(stderr)

        raw_data = jsonutils.loads(stdout)
        # Key "lat" in fio-2.2.10.
        # Key "lat_ns" in fio-3.XX.
        read_lat_key = "lat" if "lat" in raw_data["jobs"][0]["read"] else "lat_ns"
        write_lat_key = "lat" if "lat" in raw_data["jobs"][0]["write"] else "lat_ns"
        if self.job_file:
            result["read_bw"] = raw_data["jobs"][0]["read"]["bw"]
            result["read_iops"] = raw_data["jobs"][0]["read"]["iops"]
            result["read_lat"] = raw_data["jobs"][0]["read"][read_lat_key]["mean"]
            result["write_bw"] = raw_data["jobs"][0]["write"]["bw"]
            result["write_iops"] = raw_data["jobs"][0]["write"]["iops"]
            result["write_lat"] = raw_data["jobs"][0]["write"][write_lat_key]["mean"]
            # converting read_lat and write_lat in ns to us
            if read_lat_key == 'lat_ns':
                result['read_lat'] = result['read_lat'] / 1000
            if write_lat_key == 'lat_ns':
                result['write_lat'] = result['write_lat'] / 1000
        else:
            # The bandwidth unit is KB/s, and latency unit is us
            if rw in ["read", "randread", "rw", "randrw"]:
                result["read_bw"] = raw_data["jobs"][0]["read"]["bw"]
                result["read_iops"] = raw_data["jobs"][0]["read"]["iops"]
                result["read_lat"] = raw_data["jobs"][0]["read"][read_lat_key]["mean"]
                # converting read_lat in ns to us
                if read_lat_key == 'lat_ns':
                    result['read_lat'] = result['read_lat'] / 1000
            if rw in ["write", "randwrite", "rw", "randrw"]:
                result["write_bw"] = raw_data["jobs"][0]["write"]["bw"]
                result["write_iops"] = raw_data["jobs"][0]["write"]["iops"]
                result["write_lat"] = raw_data["jobs"][0]["write"][write_lat_key]["mean"]
                # converting read_lat and write_lat in ns to us
                if write_lat_key == 'lat_ns':
                    result['write_lat'] = result['write_lat'] / 1000

        if "sla" in self.scenario_cfg:
            sla_error = ""
            for k, v in result.items():
                if k not in self.scenario_cfg['sla']:
                    continue

                if "lat" in k:
                    # For lattency small value is better
                    max_v = float(self.scenario_cfg['sla'][k])
                    if v > max_v:
                        sla_error += "%s %f > sla:%s(%f); " % (k, v, k, max_v)
                else:
                    # For bandwidth and iops big value is better
                    min_v = int(self.scenario_cfg['sla'][k])
                    if v < min_v:
                        sla_error += "%s %d < " \
                            "sla:%s(%d); " % (k, v, k, min_v)

            self.verify_SLA(sla_error == "", sla_error)


def _test():
    """internal test function"""
    key_filename = pkg_resources.resource_filename("yardstick.resources",
                                                   "files/yardstick_key")
    ctx = {
        "host": {
            "ip": "10.229.47.137",
            "user": "root",
            "key_filename": key_filename
        }
    }

    logger = logging.getLogger("yardstick")
    logger.setLevel(logging.DEBUG)

    options = {
        "filename": "/home/ubuntu/data.raw",
        "bs": "4k",
        "iodepth": "1",
        "rw": "rw",
        "ramp_time": 1,
        "duration": 10
    }
    result = {}
    args = {"options": options}

    fio = Fio(args, ctx)
    fio.run(result)
    print(result)


if __name__ == '__main__':
    _test()
