import time
import threading
import os
import logging
import random
import numpy as np


# ------------Logging---------------------- #
log_file = "simulation.log"
try:
    os.remove("simulation.log")
except OSError:
    print("File not present")
    pass


logging.basicConfig(
    filename=log_file, level=logging.INFO, format='[%(asctime)-15s %(levelname)s %(thread_name)s] %(message)s')
# logging.basicConfig(level=logging.INFO, format='[%(asctime)-15s %(levelname)s %(thread_name)s] %(message)s' )

# -----------Logging End------------------ #

# -----------Global Variable Declaration---------- #
# Mean_Poisson = int(raw_input('Enter Mean of Number of messages per second(Between 100 to 7000): '))
Mean_Poisson = 1500

Eth_Packt_Size = 1500
Eth_header_size = 26
Eth_frame_size = Eth_header_size + Eth_Packt_Size

Media_Busy_Probability = 0.5
Self_Packet_Probability = 0.5

Bandwidth = 1e9
TG_74_delay = 74 * (1 / Bandwidth) * 8              # Time required to send 74 Bytes

buff_size = 64
# buff_size = int(raw_input("Enter the Packet Queue Size (between 64 to 448): "))

Total_Buffer_Size = 512 * 1024
Packet_Q_size = buff_size * 1024
Transmit_Buffer_Size = Total_Buffer_Size - Packet_Q_size

Packet_Q = list()
Transmit_Buffer = list()
Recv_Buffer = list()

Packet_Q_use = 0
Transmit_Buffer_use = 0
Recv_Buffer_use = 0

Recv_Buffer_size = 1024 * 1024
Recv_Buffer_Qlen = 5

T = time.time()

events = 0
total_count = 0

lock = threading.Lock()
# --------------Global Variable Declaration End---------- #

# ----------------- Module Definitions --------------- #


def message_generator():
    name = 'Message_Generator'
    global Packet_Q_size
    global Packet_Q
    global Packet_Q_use
    global T
    global events
    global total_count

    start = time.time()
    overflow = False
    dropped = 0
    written = 0
    # while time.time() - start <= T:
    while events <= 100000:
        start_time = time.time()
        Num_Messages = np.random.poisson(Mean_Poisson)
        Len_Message = np.random.exponential(32768, Num_Messages)
        events += Num_Messages

        processed_msg_count = 0
        processed_msg_len = 0

        for Len in Len_Message:
            Len = int(Len)
            if Len > 64 * 1024:
                Len = 64 * 1024
            else:
                pass

            while Packet_Q_use + Len >= Packet_Q_size - Eth_frame_size:
                if (time.time() - start_time) > 1:
                    # print("Overflow")
                    overflow = True
                    break

            if not overflow:

                lock.acquire()
                Packet_Q.append(Len)
                Packet_Q_use += Len
                # print("Packet_Q_use added: ", Len)
                lock.release()

                processed_msg_count += 1
                processed_msg_len += Len

                # print("processed_msg_count: ", processed_msg_count)

            else:
                # logging.warning(
                #     "Packet Queue Full. Packet_Q_use:%d | Packet Q Msg Count:%d " % (Packet_Q_use, len(Packet_Q)),
                #     extra={'thread_name': name})
                overflow = False
                break

        dropped += Num_Messages - processed_msg_count
        written += processed_msg_count
        logging.info("Messages Written:%d | Dropped Message:%d | Data Length:%d | TotalSize:%s" % \
                     (processed_msg_count, Num_Messages - processed_msg_count, processed_msg_len,
                      Packet_Q_size), extra={'thread_name': name})

        wait_time = (1 - (time.time() - start_time))
        if wait_time > 0:
            time.sleep(wait_time)
    # print("Total Messages written: {} Total Messages dropped: {}".format(written, dropped))
    total = written + dropped
    percent = (float (written)/total)
    print("% of messages written:  ", percent)
    print("Time taken: ", time.time() - T)
    print("Inserted %d Packets into TX Buffer", total_count)
    os._exit(os.EX_OK)


def Packet_Processor():
    name = 'Packet_Processor'
    global Packet_Q_size
    global Packet_Q
    global Packet_Q_use
    global Transmit_Buffer
    global Transmit_Buffer_Size
    global Transmit_Buffer_use
    global Total_Buffer_Size
    global total_count

    processed_msg_count = 0
    start = time.time()
    log_time = time.time()
    start_time = time.time()

    # while time.time() - start <= T:
    while 1:

        if len(Packet_Q) == 0:
            pass
        else:
            lock.acquire()
            PP_input = Packet_Q[0]
            Packet_Q.remove(PP_input)
            Packet_Q_use -= PP_input
            # print("Packet_Q_use removed: ", PP_input)
            lock.release()

            Ip_Packet_Count = int(PP_input/Eth_Packt_Size)
            if PP_input % Eth_Packt_Size > 0:
                Ip_Packet_Count += 1

            Packet_Data_Size = Ip_Packet_Count * (Eth_Packt_Size + Eth_header_size)
            Packet_Processor_delay = Packet_Data_Size * 2e-9 * 8
            time.sleep(Packet_Processor_delay)

            for i in range(Ip_Packet_Count):
                while Transmit_Buffer_use > Transmit_Buffer_use:
                    if (time.time() - start_time) > 1:
                        logging.warning(
                            "Transmit Buffer Full, Pending Msg Count:%d | Buffer Msg Count: %d | Buffer Remaining:%d | Tx Buf Used:%d" % (
                                Ip_Packet_Count - i, len(Transmit_Buffer), Transmit_Buffer_Size - Transmit_Buffer_use,
                                Transmit_Buffer_use), extra={'thread_name': name})
                        start_time = time.time()

                lock.acquire()
                Transmit_Buffer_use += (Eth_Packt_Size + Eth_header_size)
                Transmit_Buffer.append(Eth_Packt_Size + Eth_header_size)
                lock.release()

            processed_msg_count += Ip_Packet_Count
            total_count += Ip_Packet_Count
            if time.time() - log_time > 1:
                logging.info(
                    "Inserted %d Packets into TX Buffer in %d sec" % (processed_msg_count, time.time() - log_time),
                    extra={'thread_name': name})
                log_time = time.time()
                processed_msg_count = 0


def TX_module():
    name = 'TX_Module'
    global TG_74_delay
    global Transmit_Buffer
    global Transmit_Buffer_Size
    global Transmit_Buffer_use

    time.sleep(TG_74_delay)

    lock.acquire()
    if len(Transmit_Buffer) == 0:
        pass
    else:
        Transmit_Buffer_use -= (Eth_Packt_Size + Eth_header_size)
        Transmit_Buffer.remove(Eth_Packt_Size + Eth_header_size)
    lock.release()


def received_msg_processor():
    name = 'RX_Module'
    global Recv_Buffer_use
    global Recv_Buffer_size
    global Recv_Buffer
    global Eth_Packt_Size

    time.sleep(0.3e-9 * 8 * Eth_frame_size)
    Recv_Buffer_use -= (len(Recv_Buffer) * Eth_header_size)
    for i in range(len(Recv_Buffer)):
        Recv_Buffer.remove(Eth_frame_size)

    logging.info("Extracted Message:%d bytes " % Recv_Buffer_use, extra={'thread_name': name})
    Recv_Buffer_use = 0


def RX_Module():
    name = 'RX_Module'
    global Self_Packet_Probability
    global Recv_Buffer_use
    global Recv_Buffer_size
    global Recv_Buffer
    global Eth_frame_size

    time.sleep(1.5e-6 * 8 * Eth_frame_size)

    if random.random() < Self_Packet_Probability:
        Recv_Buffer_use += Eth_frame_size
        Recv_Buffer.append(Eth_frame_size)

    if len(Recv_Buffer) >= Recv_Buffer_Qlen:
        received_msg_processor()


def Mac_Module():
    global T
    name = 'Mac_Module'
    start = time.time()
    log_time = time.time()
    messages_sent = 0
    messages_received = 0

    # Run for 10 sec
    # while time.time() - start <= T:
    while 1:
        if random.random() < Media_Busy_Probability:
            TX_module()
            messages_sent += 1
        else:
            RX_Module()
            messages_received += 1
            pass

        time.sleep(0.3e-9 * 8 * Eth_Packt_Size)

        if time.time() - log_time > 1:
            logging.info("Mac Module Message Sent:%d" % messages_sent, extra={'thread_name': name})
            logging.info("Mac Module Message Received:%d" % messages_received, extra={'thread_name': name})
            messages_sent = 0
            messages_received = 0
            log_time = time.time()

# ------------------Module Definitions End------------------ #

# ------------------Main------------------#

if __name__ == '__main__':
    logging.info("---------------Packet Q Size::%d KB ---------------" % buff_size, extra={'thread_name': "Main"})
    thread_Tx = threading.Thread(target=message_generator, name="Message Generator")
    thread_Tx.start()
    print("Thread 1 started")
    thread_pp = threading.Thread(target=Packet_Processor, name="Packet Processor")
    thread_pp.start()
    print ("Thread 2 started")
    thread_txp = threading.Thread(target=Mac_Module, name="Mac Module")
    thread_txp.start()
    print("Thread 3 started")
