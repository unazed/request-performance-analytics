# request-performance-analytics

Simple non-blocking TCP `send()`/`recv()` performance statistics invoked on each processing core to measure (estimated) net throughput, margin of deviation, etc.. On average, packets sent are 100% reliable (as TCP mandates), but varying from NIC-to-NIC, it is my hypothesis that due to how receive buffers work, that there may not be a data integrity guarantee.

I don't really understand why, but when experimenting at a network layer interface (socket-socket), I found
that, on average, about ten packets more were sent than originally intended, likely from early truncation,
though in total the calculated data length amounted to the total expected, but of course with higher layer
protocols (e.g. HTTP) delimitation is done using CRLFs and `Content-Length` headers, so data integrity
is expected.

Additionally, CPU affinity masks are set for each process as to attempt to run individually on each core, as to whether or not this increases performance is contentious; as it appears without CPU affinity masking, receiving
tends to be faster, but sending slower, though I can't reason as to why this is true.

In a hopeful attempt to optimize the `send()`/`recv()` calls, the program will attempt to set its own scheduler policy to Round Robin with the maximum priority on each spawned process, and then dependent on whichever process finishes whichever I/O intensive part first, will relinquish itself to other processes and maximize their throughput, and finally set its own priority to the lowest past the point where all intensive code is finished.
I've noticed that `recv()` tends to be upwards of 200,000 calls quicker with this optimization, though it fluctuates.

# Run

Tested on CPython 3.9.0/GCC 10.2.0, Linux 5.10.15, the only proprietary module needed is `numpy` (for standard deviation, though not entirely necessary.) As is, the code couples with `http_netstat.py`, so run `http_netstat.py` first, and then separately `proc_main.py`, momentarily upon which a result like such will be displayed:

## `http_netstat.py`

```
======== Running on http://0.0.0.0:8080 ========
(Press CTRL+C to quit)
2048 requests
```

## `proc_main.py`

```
(21:35:54) starting proc. id: 0
(21:35:54) starting proc. id: 1
(21:35:54) starting proc. id: 2
(21:35:54) starting proc. id: 3
(21:35:54) beginning polling for events
(21:35:56) proc. id: 0, CPU core #3 finished:
send:	mean: 1.5712 us, min.: 1.4070 us, max.: 5.4210 us
		std. dev.: 0.3619 us, req. p/s: 636436.37
recv:	mean: 6.8867 us, min.: 1.7420 us, max.: 21.8410 us
		std. dev.: 3.4356 us, recv. p/s: 145206.53, # bytes: 1654272

(21:35:56) proc. id: 1, CPU core #0 finished:
send:	mean: 1.5351 us, min.: 1.3840 us, max.: 4.4420 us
		std. dev.: 0.2065 us, req. p/s: 651410.82
recv:	mean: 8.0715 us, min.: 1.6030 us, max.: 70.5410 us
		std. dev.: 6.4461 us, recv. p/s: 123892.43, # bytes: 1654272

(21:35:56) proc. id: 2, CPU core #1 finished:
send:	mean: 1.5096 us, min.: 1.4020 us, max.: 3.0650 us
		std. dev.: 0.1390 us, req. p/s: 662427.31
recv:	mean: 7.3783 us, min.: 1.6820 us, max.: 60.3470 us
		std. dev.: 5.5217 us, recv. p/s: 135533.04, # bytes: 1654272

(21:35:56) proc. id: 3, CPU core #2 finished:
send:	mean: 1.5269 us, min.: 1.4230 us, max.: 4.2720 us
		std. dev.: 0.2025 us, req. p/s: 654911.04
recv:	mean: 6.6806 us, min.: 1.7450 us, max.: 20.1840 us
		std. dev.: 3.3611 us, recv. p/s: 149687.29, # bytes: 1654272

in total: req. p/s: 2605185.53, recv. p/s: 554319.29, send/recv. ratio: 4.70:1
```
