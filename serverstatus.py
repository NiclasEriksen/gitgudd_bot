import os
from proxmoxer import ProxmoxAPI


proxmox = ProxmoxAPI(
    os.environ["PROXMOX_SERVER"],
    user=os.environ["PROXMOX_USER"],
    password=os.environ["PROXMOX_PW"], verify_ssl=False
)
