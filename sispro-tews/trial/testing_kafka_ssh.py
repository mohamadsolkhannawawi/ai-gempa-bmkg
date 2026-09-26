import paramiko
import socket
from kafka import KafkaProducer

ssh_host = "152.118.31.54"
ssh_port = 36022
ssh_username = 'user01'
ssh_password = 'pass2024'
local_port = 9092  # Port on local machine to forward traffic to
remote_kafka_host = "152.118.31.54"
remote_kafka_port = 9092  # Kafka's port

# Initialize paramiko SSH client
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    # Connect to the SSH server
    print("Connecting to SSH...")
    client.connect(ssh_host, port=ssh_port, username=ssh_username, password=ssh_password)
    print("SSH connection established.")

    # Create the tunnel
    transport = client.get_transport()
    if not transport.is_active():
        raise Exception("Transport not active")

    local_socket = ('localhost', local_port)
    remote_socket = (remote_kafka_host, remote_kafka_port)

    # Open the channel for TCP forwarding
    print("Opening SSH tunnel...")
    forward_channel = transport.open_channel('direct-tcpip', remote_socket, local_socket)
    print("SSH tunnel established.")

    # Now connect to Kafka using 'localhost:9092'
    print(f"Connecting to Kafka on localhost:{local_port}...")
    kafka_producer = KafkaProducer(bootstrap_servers=f'localhost:{local_port}')

    # Send a message to Kafka
    kafka_producer.send('testing_ssh', b'Message via SSH tunnel')
    kafka_producer.flush()
    print("Message sent via SSH tunnel")

    # Close the producer connection
    kafka_producer.close()

except Exception as e:
    print(f"Error: {e}")
finally:
    # Close the channel and the SSH connection
    if 'forward_channel' in locals() and forward_channel:
        forward_channel.close()
    if client:
        client.close()
    print("SSH connection closed.")
