from select import POLLIN, POLLRDHUP, POLLERR
import collections
import pprint
import socket
import select
import time


def poll_indefinitely(sockfd, timeout=100):
    srv_poll = select.poll()
    srv_poll.register(sockfd, POLLIN)

    last_info_dump = time.time()
    clients = {}
    client_netstat = collections.defaultdict(lambda: {
        "nreq": 0,
        "nbytes": 0,
        "errors": 0,
        })

    while True:
        if time.time() - last_info_dump >= 5:
            pprint.pprint(client_netstat)
            last_info_dump = time.time()

        if (srv_event := srv_poll.poll(timeout)):
            conn, addr = sockfd.accept()
            print(f"(poll_indefinitely) received client {addr[0]!r}")
            client_poll = select.poll()
            client_poll.register(conn, POLLIN | POLLRDHUP | POLLERR)
            clients[addr] = [conn, client_poll]
            continue

        for client, _ in clients.copy().items():
            cl_sockfd, cl_poll = _
            if (cl_events := cl_poll.poll(timeout)):
                for cl_event in cl_events:
                    fd, event = cl_event
                    if event & POLLRDHUP or event & POLLERR:
                        print(f"(poll_indefinitely) closing client {client!r}")
                        cl_sockfd.close()
                        del clients[client]
                        continue
                    elif event & POLLIN:
                        recv_buf = cl_sockfd.recv(1536)
                        if recv_buf != b"\xaa"*1536:
                            print(len(recv_buf))
                            client_netstat[client]['errors'] += 1
                        client_netstat[client]['nreq'] += 1
                        client_netstat[client]['nbytes'] += len(recv_buf)
                        cl_sockfd.send(recv_buf)


def create_server_socket(host, port, reuse_addr=True):
    sockfd = socket.socket()
    sockfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, reuse_addr)
    sockfd.bind((host, port))
    sockfd.listen(10)
    sockfd.setblocking(False)
    return sockfd


if __name__ == "__main__":
    sockfd = create_server_socket("localhost", 6969)
    poll_indefinitely(sockfd)
