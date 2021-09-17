# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: AERPAW Sink
# GNU Radio version: v3.8.2.0-80-g40c04cae

from gnuradio import gr
from gnuradio.filter import firdes
import sys
import signal
from gnuradio import uhd
import time
from gnuradio import zeromq





class AERPAW_Sink(gr.hier_block2):
    def __init__(self, args="", center_freq=2.6e9, samp_rate=30.72e6, source='ZMQ', tx_gain=70, zmq_tx_address='tcp://*:5002'):
        gr.hier_block2.__init__(
            self, "AERPAW Sink",
                gr.io_signature(1, 1, gr.sizeof_gr_complex*1),
                gr.io_signature(0, 0, 0),
        )

        ##################################################
        # Parameters
        ##################################################
        self.args = args
        self.center_freq = center_freq
        self.samp_rate = samp_rate
        self.source = source
        self.tx_gain = tx_gain
        self.zmq_tx_address = zmq_tx_address

        ##################################################
        # Blocks
        ##################################################
 
        if self.source == "uhd" or self.source == "UHD":
            self.uhd_usrp_sink_0 = uhd.usrp_sink(
                ",".join(("", args)),
                uhd.stream_args(
                    cpu_format="fc32",
                    args='',
                    channels=list(range(0,1)),
                ),
                '',
            )
            self.uhd_usrp_sink_0.set_center_freq(center_freq, 0)
            self.uhd_usrp_sink_0.set_gain(tx_gain, 0)
            self.uhd_usrp_sink_0.set_antenna('TX/RX', 0)
            self.uhd_usrp_sink_0.set_samp_rate(samp_rate)
            self.uhd_usrp_sink_0.set_time_unknown_pps(uhd.time_spec())


        ##################################################
        # Connections
        ##################################################
            self.connect((self, 0), (self.uhd_usrp_sink_0, 0))
        

        if self.source == "zmq" or self.source == "ZMQ":
            self.zeromq_rep_sink_0 = zeromq.rep_sink(gr.sizeof_gr_complex, 1, zmq_tx_address, 100, False, -1)
            self.connect((self, 0), (self.zeromq_rep_sink_0, 0))


    def get_args(self):
        return self.args

    def set_args(self, args):
        self.args = args

    def get_center_freq(self):
        return self.center_freq

    def set_center_freq(self, center_freq):
        self.center_freq = center_freq
        self.uhd_usrp_sink_0.set_center_freq(self.center_freq, 0)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.uhd_usrp_sink_0.set_samp_rate(self.samp_rate)

    def get_source(self):
        return self.source

    def set_source(self, source):
        self.source = source

    def get_tx_gain(self):
        return self.tx_gain

    def set_tx_gain(self, tx_gain):
        self.tx_gain = tx_gain
        self.uhd_usrp_sink_0.set_gain(self.tx_gain, 0)

    def get_zmq_tx_address(self):
        return self.zmq_tx_address

    def set_zmq_tx_address(self, zmq_tx_address):
        self.zmq_tx_address = zmq_tx_address


