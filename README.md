# request-performance-analytics

Simple non-blocking TCP `send()`/`recv()` performance statistics invoked on each processing core to measure (estimated) net throughput, margin of deviation, etc.. On average, packets sent are 100% reliable (as TCP mandates), but varying from NIC-to-NIC, it is my hypothesis that due to how receive buffers work, that there may not be a data integrity guarantee.

I don't really understand why, but when experimenting at a network layer interface (socket-socket), I found
that, on average, about ten packets more were sent than originally intended, likely from early truncation,
though in total the calculated data length amounted to the total expected, but of course with higher layer
protocols (e.g. HTTP) delimitation is done using CRLFs and `Content-Length` headers, so data integrity
is expected.
