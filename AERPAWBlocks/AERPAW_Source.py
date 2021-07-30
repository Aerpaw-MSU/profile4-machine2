# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: AERPAW Source
# Author: keith
# GNU Radio version: v3.8.2.0-80-g40c04cae

from gnuradio import gr
from gnuradio.filter import firdes
import sys
import signal
from gnuradio import uhd
import time
from gnuradio import zeromq





class AERPAW_Source(gr.hier_block2):
    def __init__(self, center_freq=2.6e9, rx_gain=40, samp_rate=32e3, source='uhd', zmq_address='tcp://localhost:5001'):
        gr.hier_block2.__init__(
            self, "AERPAW Source",
                gr.io_signature(0, 0, 0),
                gr.io_signature(1, 1, gr.sizeof_gr_complex*1),
        )

        ##################################################
        # Parameters
        ##################################################
        self.center_freq = center_freq
        self.rx_gain = rx_gain
        self.samp_rate = samp_rate
        self.source = source
        self.zmq_address = zmq_address

        ##################################################
        # Blocks
        ##################################################
        
        if self.source == "uhd" or self.source == "UHD":
            self.uhd_usrp_source_0 = uhd.usrp_source(
                ",".join(("", "")),
                uhd.stream_args(
                    cpu_format="fc32",
                    args='',
                    channels=list(range(0,1)),
                ),
            )
            self.uhd_usrp_source_0.set_center_freq(center_freq, 0)
            self.uhd_usrp_source_0.set_gain(rx_gain, 0)
            self.uhd_usrp_source_0.set_antenna('RX2', 0)
            self.uhd_usrp_source_0.set_samp_rate(samp_rate)
            self.uhd_usrp_source_0.set_time_unknown_pps(uhd.time_spec())


        ##################################################
        # Connections
        ##################################################
            self.connect((self.uhd_usrp_source_0, 0), (self, 0))

        ##################################################
        # Blocks
        ##################################################
        if self.source == "zmq" or self.source == "ZMQ":
            self.zeromq_req_source_0 = zeromq.req_source(gr.sizeof_gr_complex, 1, zmq_address, 100, False, -1)


        ##################################################
        # Connections
        ##################################################
            self.connect((self.zeromq_req_source_0, 0), (self, 0))


    def get_center_freq(self):
        return self.center_freq

    def set_center_freq(self, center_freq):
        self.center_freq = center_freq
        self.uhd_usrp_source_0.set_center_freq(self.center_freq, 0)

    def get_rx_gain(self):
        return self.rx_gain

    def set_rx_gain(self, rx_gain):
        self.rx_gain = rx_gain
        self.uhd_usrp_source_0.set_gain(self.rx_gain, 0)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)

    def get_source(self):
        return self.source

    def set_source(self, source):
        self.source = source

    def get_zmq_address(self):
        return self.zmq_address

    def set_zmq_address(self, zmq_address):
        self.zmq_address = zmq_address


