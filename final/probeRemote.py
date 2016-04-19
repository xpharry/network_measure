# -*- coding: utf-8 -*-
#!/usr/bin/python

import socket
import struct
import select 
import sys
import time
import struct

class Tracer:
    def __init__(self, dest_name):
        # Turn a hostname into an IP address.
        self.dest_name = dest_name
        self.dest_addr = socket.gethostbyname(self.dest_name)
        self.port = 33434
        self.ttl = 32
        self.max_hops = 30
        self.max_wait = 3.0
        self.nqueries = 3
        self.reached = 0
        self.build_probe_packet()
        self.open_sockets()

    def trace(self):
        self.reached = 0
        delta = 0
        for i in range(self.nqueries):
            if self.reached:
                break
            send_at = self.send_probe()
            reply, recv_at = self.get_reply()
        if reply:
            delta = recv_at - send_at
        else:
            print "Fail to reach the remote server! Give up."

        self.display_results(reply, delta)

    def open_sockets(self):
        # Create sockets for the connections.
        self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        # self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        # # Build the GNU timeval struct (seconds, microseconds)
        # timeout = struct.pack("ll", 5, 0)
        # # Set the receive timeout so we behave more like regular traceroute
        # self.recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, timeout)
        # Set the TTL field on the packets.
        self.send_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, self.ttl)

        # Bind the sockets and send some packets.
        self.recv_socket.bind(("", self.port))
        self.send_socket.sendto("", (self.dest_name, self.port))

    def build_probe_packet(self):
        # send_pkt = struct.pack('hhl', 1, 2, 3)
        header = struct.pack('cchhhcc',
            chr((4 & 0x0f) << 4 
            | (5 & 0x0f)),    # 4bits each
            chr(0x00 & 0xff),
            20,
            0,
            0,     # what about flags?
            chr(32 & 0xff),
            chr(0 & 0xff))
        # _dest_addr = dotted_to_int(self.dest_addr)
        # _src_addr = dotted_to_int(os.uname()[1])
        self.send_pkt = header + '\000\000' + "192.168.1.77" + self.dest_addr
        self.send_pkt = self.send_pkt + "python "*3
        self.packlen = len(self.send_pkt)


    def send_probe(self):
        start_time = time.time()

        self.send_socket.sendto(self.send_pkt, (self.dest_name, self.port))
        return start_time

    def get_reply(self):
        start = time.time()
        timeout = self.max_wait

        while True:
            # use select() to check the availability of the site
            inputready, outputready, exceptready = select.select([self.recv_socket], [], [], timeout)

            # Test for timeout
            if inputready:
                try:
                    reply, curr_addr = self.recv_socket.recvfrom(4096)
                    self.reached = 1
                    curr_addr = curr_addr[0] # intermediate hosts' IP address
                    try:
                        curr_name = socket.gethostbyaddr(curr_addr)[0]
                    except socket.error:
                        curr_name = curr_addr
                except socket.error as (errno, errmsg):
                    sys.stdout.write("* ")
                arrive_time = time.time()
                if self.reached == 1:
                    return reply, arrive_time
            timeout = (start + self.max_wait) - time.time()
            if timeout < 0:
                return None, None

    def display_results(self, reply, delta):
        if not reply:
            print "timeout!"
            return

        data = reply[0:20]
        ip_header_data = struct.unpack('!BBHHHBBH4s4s', data)

        print ip_header_data
        print len(ip_header_data)
        #To the the ip version we have to shift 
        #the first element 4 bits right. Because in the first element
        #is stored the ip version and the header lenght in this way
        #first four bits are ip version and the last 4 bites are
        #the header lenghth  
        ip_version = ip_header_data[0] >> 4

        #Now to get the header lenght we use "and" operation to make the
        #Ip versional bits equal to zero, in order to the the desired data
        IHL = ip_header_data[0] & 0x0F

        #Diferentiated services doesn't need any magic opperations,
        #so we jus grab it from the tuple
        diff_services = ip_header_data[1]

        #Total lenght is also easy to extract
        total_length = ip_header_data[2]

        #The same goes for identification 
        id_ = ip_header_data[3]

        #The "Flags" and Fragment Offset are situated in a sinle
        #element from the forth element of the tuple.
        #Flag is 3 bits (Most significant), so we make "and" with 1110 0000 0000 0000(=0xE000)
        #to leave 3 most significant bits and then shift them right 13 positions
        flags = ip_header_data[4] & 0xE000 >> 13

        #The next elements are easy to get
        TTL      = ip_header_data[5]
        protocol = ip_header_data[6]
        checksum = ip_header_data[7]
        source   = ip_header_data[8]
        destinat = ip_header_data[9]     
        
        #and the rest data from the "packet" variable is the payload so we
        #extract it also
        payload = reply[20:]

        print "__________________NEW_PACKET__________________"
        print "Version: %s  \n\rHeader lenght: %s"  %(ip_version,IHL)
        print "Diferentiated services: %s \n\rID: %s" %(diff_services, id_)
        print "Flags: %s \n\rTTL: %s \n\rProtocol: %s" %(flags,TTL,protocol)
        print "Checksum: %s \n\rSource: %s \n\rDestination: %s" %(checksum, socket.inet_ntoa(source),socket.inet_ntoa(destinat))
        print "Payload: %8s" %(payload)
        print

        icmpHeader = reply[20:28]
        type, code, checksum, packetID, sequence = struct.unpack(
            "bbHHh", icmpHeader
        )
        print "type: %d" % type
        print "code: %d" % code
        print "checksum: %d" % checksum
        print "packetID: %d" % packetID
        print "sequence: %d" % sequence

def importServers():
    # Open a file
    file = open("targets.txt", "r")

    # read a file by line
    temp = file.read()
    ip_list = temp.split('\n')
    ip_list = ip_list[1:]

    # Close opend file
    file.close()

    # # check data stored in ip_list
    # for ip in ip_list:
    #   print ip

    return ip_list

def main():
    ip_list = importServers()
    for dest_name in ip_list:
        dest_name = dest_name.strip()
        print "======== destination ip: %s =========" % dest_name
        dest_name = u'%s' %dest_name
        tracer = Tracer(dest_name)
        tracer.trace()
        print "======== this ip probing ends here ========="

if __name__ == '__main__':
    main()


