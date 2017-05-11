
log_file = open('simulation.log', 'r')

log = log_file.readlines()

message_generator = list()
packet_processor = list()
rx_module = list()
mac_module = list()


for line in log:
    if 'Message_Generator' in line:
        line = line[49:]
        message_generator.append(line)
    elif 'Packet_Processor' in line:
        line = line[48:]
        packet_processor.append(line)
    elif 'RX_Module' in line:
        rx_module.append(line)
    elif 'Mac_Module' in line:
        line=line[42:]
        mac_module.append(line)

f = open('Message_generator.log', 'w')
f.writelines(message_generator)
f.close()

f = open('Packet_Processor.log', 'w')
f.writelines(packet_processor)
f.close()

f = open('RX_Module.log', 'w')
f.writelines(rx_module)
f.close()

f = open('Mac_Module.log', 'w')
f.writelines(mac_module)
f.close()
