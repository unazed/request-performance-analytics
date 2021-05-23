from typing import Callable, Optional
import multiprocessing
import threading
import os
import numpy
import socket
import time
import random
import psutil


REQUEST_SAMPLE_COUNT = 512


def mock_request():
    pass


def connect_socket(url: str, port: int) -> socket.socket:
    sockfd = socket.socket()
    sockfd.connect((url, port))
    return sockfd


def worker(master: multiprocessing.Pipe, request_method: Callable,
            affinity: int, addr_tup: tuple[str, int], data: bytes,
            *, is_blocking: bool=False):
    times = []
    norm_times = []

    os.sched_setaffinity(0, {affinity})
    
    sockfd = connect_socket(*addr_tup)
    sockfd.setblocking(is_blocking)
    
    nsent = 0

    while nsent < REQUEST_SAMPLE_COUNT:
        start = time.time_ns()
        try:
            sockfd.send(data)
            nsent += 1
            times.append(time.time_ns() - start)
        except (EOFError, BrokenPipeError, ConnectionResetError):
            sockfd = connect_socket(*addr_tup)

    recv_times = []
    norm_recv_times = []

    data = b""
    sockfd.setblocking(False)
    last = time.time()
    while 1:
        try:
            start = time.time_ns()
            recv = sockfd.recv(1024)
            recv_times.append(time.time_ns() - start)
            last = time.time()    
        except BlockingIOError:
            if time.time() - last > 0.5:
                break
            continue
        if not recv:
            break
        data += recv
    sockfd.close()

    std = numpy.std(times)
    std_recv = numpy.std(recv_times)

    mean = sum(times) / len(times)
    mean_recv = sum(recv_times) / len(recv_times)

    for time_ in times:
        if mean - 2 * std <= time_ <= mean + 2 * std:
            norm_times.append(time_)

    for recv_time in recv_times:
        if mean_recv - 2 * std_recv <= recv_time <= mean_recv + 2 * std_recv:
            norm_recv_times.append(recv_time)

    master.send({
        "send": {
            "mean": (sum(norm_times) / len(norm_times)) / 1e3,  # us
            "std": numpy.std(norm_times) / 1e3,
            "min": min(norm_times) / 1e3,
            "max": max(norm_times) / 1e3,
            },
        "recv": {
            "mean": (sum(norm_recv_times) / len(norm_recv_times)) / 1e3,  # us
            "std": numpy.std(norm_recv_times) / 1e3,
            "min": min(norm_recv_times) / 1e3,
            "max": max(norm_recv_times) / 1e3,
            "nbytes": len(data),
            },
        "cpu_core": psutil.Process().cpu_num()
        })


def create_process_pool(amount: int) \
        -> list[multiprocessing.Process]:
    pool = {}
    affinity = multiprocessing.cpu_count() - 1

    for id_ in range(amount):
        master, slave = multiprocessing.Pipe()
        pool[id_] = {
            "pipe": master,
            "proc": multiprocessing.Process(
                target=worker, args=(
                    slave, mock_request, affinity,
                    ("127.0.0.1", 8080),
                    b"GET / HTTP/1.1\r\n\r\n"
                    )
                )
            }
        affinity += 1
        affinity %= multiprocessing.cpu_count()

    return pool


def timestamp():
    return time.strftime("%H:%M:%S")


def is_event(pool: list) -> Optional[int]:
    for id_, proc in pool.items():
        if proc['pipe'].poll() is None:
            continue
        return id_


def start_polling(pool: list) -> None:
    for id_, proc_info in pool.items():
        print(f"({timestamp()}) starting proc. id: {id_}")
        proc_info['proc'].start()
    print(f"({timestamp()}) beginning polling for events")
    
    total_recv_rps = 0
    total_send_rps = 0

    while pool:
        if (id_ := is_event(pool)) is None:
            continue

        result = pool[id_]['pipe'].recv()
        send = result['send']
        recv = result['recv']
        core_num = result['cpu_core']

        rps = 1 / (send['mean'] / 1e6)
        recv_rps = 1 / (recv['mean'] / 1e6)

        print(  f"({timestamp()}) proc. id: {id_}, CPU core #{core_num} finished:\n"
                f"send:\tmean: {send['mean']:.4f} us, min.: {send['min']:.4f} us, max.: {send['max']:.4f} us\n"
                f"\t\tstd. dev.: {send['std']:.4f} us, req. p/s: {rps:.2f}\n"
                f"recv:\tmean: {recv['mean']:.4f} us, min.: {recv['min']:.4f} us, max.: {recv['max']:.4f} us\n"
                f"\t\tstd. dev.: {recv['std']:.4f} us, recv. p/s: {recv_rps:.2f}, # bytes: {recv['nbytes']}\n")

        total_recv_rps += recv_rps
        total_send_rps += rps

        del pool[id_]

    print(f"in total: req. p/s: {total_send_rps:.2f}, recv. p/s: {total_recv_rps:.2f}, send/recv. ratio: "
            f"{total_send_rps/total_recv_rps:.2f}:1")


if __name__ == "__main__":
    proc_pool = create_process_pool(
            amount=multiprocessing.cpu_count()
            )
    start_polling(proc_pool)
