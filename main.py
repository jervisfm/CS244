#!/usr/bin/python
"CS244 Spring 2017 Assignment 3"

# Mininet
from mininet.topo import Topo
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.clean import cleanup
from mininet.log import lg, info
from mininet.util import dumpNodeConnections
from mininet.cli import CLI

import numpy as np
import matplotlib as mpl
mpl.use('Agg') # Headless mode
import matplotlib.pyplot as plt

# Process
from subprocess import Popen, PIPE
from time import sleep, time
from multiprocessing import Process
from argparse import ArgumentParser

# General
import sys
import os
import math


class SimpleDCTopo(Topo):
    "Simple topology for initial congestion control experiment."

    def build(self, bandwidth=100, delay=100):
        # Create two hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')

        # Connecting switch
        switch = self.addSwitch('s0')

        # Add links with appropriate characteristics
        print "Bandwidth =", bandwidth * 1000.0, "Kbps"
        print "RTT =", 4 * delay, "ms"
        self.addLink(h1, switch,
                     bw=bandwidth,
                     delay="{}ms".format(delay))

        self.addLink(h2, switch,
                     bw=bandwidth,
                     delay="{}ms".format(delay))


def start_webserver(net):
    print "Starting webserver..."
    h1 = net.get('h1')
    proc = h1.popen("python http/webserver.py", shell=True)
    sleep(1)
    return [proc]


def setup(bandwidth=100, rtt=100):
    # Clean up existing mininet
    print "Cleaning up mininet..."
    cleanup()

    # Set congestion control to cubic (should be default)
    os.system("sysctl -w net.ipv4.tcp_congestion_control=cubic > /dev/null")

    # Timeout modifiers
    os.system("sysctl -w net.ipv4.tcp_retries1=100 > /dev/null")
    os.system("sysctl -w net.ipv4.tcp_retries2=100 > /dev/null")
    os.system("sysctl -w net.ipv4.tcp_frto=100 > /dev/null")
    os.system("sysctl -w net.ipv4.tcp_frto_response=100 > /dev/null")

    # Setup network topology
    print "Starting network..."
    topo = SimpleDCTopo(bandwidth=bandwidth, delay=rtt / 4.0)
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink)
    net.start()
    return net


def clean(net):
    print "Stopping network..."
    if net is not None:
        net.stop()

    # Ensure that all processes you create within Mininet are killed.
    # Sometimes they require manual killing.
    Popen("pgrep -f webserver.py | xargs kill -9", shell=True).wait()
    Popen("killall -9 iperf", shell=True).wait()
    Popen("killall -9 ping", shell=True).wait()


def modify_route(host, initcwnd, initrwnd, mtu):
    rto_min = 1000

    # Change congestion window
    route = host.cmd("ip route show").strip()
    print "route 1", route
    cmd = "sudo ip route change {} initcwnd {} initrwnd {} mtu {} rto_min {}".format(
        route, initcwnd, initrwnd, mtu, rto_min)
    print "cmd", cmd
    print "initcwnd", host.cmd(cmd)


def experiment(bandwidth, rtt, initcwnd, initrwnd, file=[
        "search/index.html", "search/1", "search/2", "search/3", "search/4"]):
    R = 3       # Number of concurrent curl experiments
    S = 0       # Time to sleep waiting for curl
    T = 30      # Time to run experiment
    mtu = 1500  # Max transmission unit

    # Setup
    net = setup(bandwidth=bandwidth, rtt=rtt)

    # Configuration
    h1 = net.get('h1')
    h2 = net.get('h2')
    times = []

    # Configure congestion window (only on the second experiment)
    modify_route(h1, initcwnd, initrwnd, mtu)
    modify_route(h2, initcwnd, initrwnd, mtu)

    # Check results
    print "H1 route:", h1.cmd("ip route show").strip()
    print "H2 route:", h2.cmd("ip route show").strip()

    # Experiment
    start_webserver(net)

    # Measure latency
    start_time = time()
    while True:
        for i in range(R):
            etime = 0
            for q in file:
                cmd = "curl -o /dev/null -s -w %{time_total} " + \
                    h1.IP() + "/http/" + q
                result = h2.cmd(cmd)
                print result
                etime += float(result)
            times += [etime]

        # do the measurement (say) 3 times.
        sleep(S)
        now = time()
        delta = now - start_time
        if delta > T:
            break
        print "%.1fs left..." % (T - delta)

    # Clean up
    clean(net)
    return np.mean(times)


def generate_figures(name, xaxis, xlabels, title, results):
    N, M = np.shape(results)
    abs_im = []
    per_im = []
    for i in range(N):
        a, b = results[i, :]
        abs_im += [(a - b) * 1000.0]
        per_im += [(a / b - 1) * 100]

    ind = np.arange(N)  # the x locations for the groups
    width = 0.35       # the width of the bars

    fig, ax = plt.subplots()
    rects1 = ax.bar(ind, abs_im, width, color='r')
    for r in rects1:
        r.set_color('#FF8A87')

    # add some text for labels, title and axes ticks
    ax.set_ylim([1, 10000])
    ax.set_yscale('log')
    ax.set_ylabel('Improvement (ms)')
    ax.set_xlabel(xaxis)
    ax.set_title(title)
    ax.set_xticks(ind + width / 2)
    ax.set_xticklabels(xlabels)

    ax2 = ax.twinx()
    ax2.set_ylim([0, 50.0])
    rects2 = ax2.bar(ind + width, per_im, width, color='y')
    for r in rects2:
        r.set_color('#052CFF')

    ax.legend((rects1[0], rects2[0]),
              ('Absolute Improvement', 'Percentage Improvement'))

    def autolabel(rects):
        """
        Attach a text label above each bar displaying its height
        """
        for rect in rects:
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2., 1.05 * height,
                    '%d' % int(height),
                    ha='center', va='bottom')

    #autolabel(rects1)
    #autolabel(rects2)

    fig.savefig('results/' + name + '.png')
    plt.close(fig)


def bw_experiment():
    BW = (256, 512, 1000, 2000, 3000, 5000, 10000, 20000, 50000, 100000, 200000)
    MODE = (
        (3, 100),
        (10, 100)
    )

    # Number of samples
    N = len(BW)
    M = len(MODE)
    RTT = 70

    # Sample bandwidth N times
    results = np.zeros((N, 2))
    for r in range(N):
        for i in range(M):
            initcwnd, initrwnd = MODE[i]
            results[r, i] = experiment(BW[r] / 1000.0,
                                       RTT,
                                       initcwnd,
                                       initrwnd)
            print results

    # Debugging
    print "Final results"
    print results

    # Save result
    generate_figures("Figure5_BW",
                     'Bandwidth (Kbps)',
                     BW,
                     'Average response latency for Web search bucketed by BW',
                     results)


def bdp_experiment():
    BW = (1000, 5000, 10000, 50000, 100000, 200000)
    MODE = (
        (3, 100),
        (10, 100)
    )

    # Number of samples
    N = len(BW)
    M = len(MODE)
    RTT = 70
    RTT_sec = (RTT / 1000.0)

    # Sample bandwidth N times
    results = np.zeros((N, 2))
    for r in range(N):
        for i in range(M):
            initcwnd, initrwnd = MODE[i]

            bandwidth = ((BW[r] * 8) / RTT_sec) / 1000.0
            results[r, i] = experiment(bandwidth / 1000.0,
                                       RTT,
                                       initcwnd,
                                       initrwnd)
            print results

    # Debugging
    print "Final results"
    print results

    # Save result
    generate_figures("Figure5_BDP",
                     'BDP (Bytes)',
                     BW,
                     'Average response latency for Web search bucketed by BDP',
                     results)


def rtt_experiment():
    RTT = (20, 50, 100, 200, 500, 1000)
    MODE = (
        (3, 100),
        (10, 100)
    )

    M = len(MODE)
    N = len(RTT)
    bandwidth = 1.2

    results = np.zeros((N, 2))

    # Run experiment
    for r in range(N):
        for i in range(M):
            initcwnd, initrwnd = MODE[i]
            results[r, i] = experiment(bandwidth, RTT[r], initcwnd, initrwnd)
            print results

    # Debugging
    print "Final results"
    print results

    # Save result
    generate_figures("Figure5_RTT",
                     'RTT (msec)',
                     RTT,
                     'Average response latency for Web search bucketed by RTT',
                     results)


def segment_experiment():
    SEG = (3, 4, 7, 10, 15, 30, 50)
    MODE = (
        (3, 100),
        (10, 100)
    )

    M = len(MODE)
    N = len(SEG)
    bandwidth = 1.2
    rtt = 70
    results = np.zeros((N, 2))

    # Run experiment
    for r in range(N):
        for i in range(M):
            initcwnd, initrwnd = MODE[i]
            results[r, i] = experiment(bandwidth,
                                       rtt,
                                       initcwnd,
                                       initrwnd,
                                       file=[str(SEG[r]) + ".html"])
            print results

    # Debugging
    print "Final results"
    print results

    # Save result
    generate_figures("Figure5_SEG",
                     'Number of segments',
                     SEG,
                     'Average response latency at AvgDC for Web search bucketed by number of segments',
                     results)


def init_cwnd_experiment():
    MODE = (
        (3, 100),
        (6, 100),
        (10, 100),
        (16, 100),
        (26, 100),
        (46, 100)
    )

    M = len(MODE)
    bandwidth = 1.2
    rtt = 70
    results = np.zeros(M)

    # Run experiment
    for i in range(M):
        initcwnd, initrwnd = MODE[i]
        results[i] = experiment(bandwidth,
                                rtt,
                                initcwnd,
                                initrwnd)
        print results

    # Debugging
    print "Final results"
    print results


if __name__ == "__main__":

    # Setup
    if not os.path.exists("results"):
        os.makedirs("results")

    # Experiments
    init_cwnd_experiment()
    segment_experiment()
    bw_experiment()
    bdp_experiment()
    rtt_experiment()
