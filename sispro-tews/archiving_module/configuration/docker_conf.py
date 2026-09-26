from docker import APIClient 
import os
import re

def get_replica_id():
    # Only get replica id if HOSTNAME is not None
    HOSTNAME = os.environ.get("HOSTNAME")
    if HOSTNAME:
        # Get all container in this docker engine
        cli = APIClient(base_url='unix://var/run/docker.sock')
        all_containers = cli.containers()

        # Filter out this container by HOSTNAME
        this_container = [c for c in all_containers if c['Id'][:12] == HOSTNAME[:12]][0]

        # Get replica id from container name
        matches = re.findall(r'[-_](\d+)$', this_container['Names'][0])

        if matches:
            return matches[-1]