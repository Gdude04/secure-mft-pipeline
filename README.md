# Secure Managed File Transfer (MFT) Pipeline

## 1. Project Overview

This project is a secure systems architecture tool that I built to show how to set up a Secure File Transfer Protocol (SFTP). To do this, I created an OpenSSH chroot jail by enforcing strict UNIX directory permissions and isolating a dedicated service account on my Ubuntu ARM64 VM. This user was named `transfer_user` and its only purpose was to allow a user from another machine to send secure documents to itself, while also limiting what the user can do on the operating system. This project demonstrates enterprise-grade secure file transfer architecture by enforcing strict UNIX permissions and OpenSSH chroot jails to establish a zero-trust boundary.

## 2. Key Engineering Features

* **Automation Script:** Allows the sender to use a Python script that handles the commands they otherwise would have to type in manually to send the file. This eliminates the potential for human error.

* **Chroot Jail:** Locks the service account into a dedicated directory where they are forced to stay. This ensures that the user cannot interact with other files within the system, ensuring security.

* **Permissions Enforcement:** Created the directory tree's ownership and access limits to satisfy the OpenSSH daemon's strict security requirements and prevent privilege escalation.

* **Cross-Architecture Networking:** Created a stable connection between my Apple Silicon macOS environment and a virtualized Ubuntu ARM64 server running on the same device. Shows how different operating systems can be connected to each other.

## 3. Technical Stack

* **Tools:** VMware Fusion Professional 25H2

* **Operating Systems:** macOS 27.0.1, ubuntu-26.04.1-live-server-arm64

* **Language:** Python 3.13.11

* **Protocols:** SSH / SFTP (TCP Port 22)

* **Core Libraries:** `paramiko` (SSH/SFTP implementation), `python-dotenv` (environment configuration)

## 4. Prerequisites

* Python 3.13.11+ installed locally.

* Network line-of-sight to the target server (ICMP and TCP port 22 open).

* A valid SSH user account on the target infrastructure.

## 5. Setup

**1. Initialize the VM Environment**
First, set up the second machine that you want to send the files to. For this, I used VMware Fusion on my MacBook so I could easily install and run the Ubuntu server.

**2. Update Packages and Install SSH Service**

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install openssh-server -y
```

**3. Create the User Group and Restricted User**
Create the new group, add the user without an interactive shell, and set a password:

```bash
sudo groupadd sftp_users
sudo useradd -m -G sftp_users -s /usr/sbin/nologin transfer_user
sudo passwd transfer_user
```

**4. Create the Chroot Jail**
Create the isolated directory and strictly configure the POSIX permissions to satisfy OpenSSH daemon requirements:

```bash
sudo mkdir -p /var/sftp/uploads
sudo chown root:root /var/sftp
sudo chmod 755 /var/sftp
sudo chown transfer_user:sftp_users /var/sftp/uploads
```

**5. Configure the SSH Daemon (`sshd_config`)**
Open the SSH configuration file to enforce the chroot jail:

```bash
sudo nvim /etc/ssh/sshd_config
```

* Navigate to the `Subsystem` line and ensure it reads: `Subsystem sftp internal-sftp`.

* Delete any existing `Match User` or `Match Group` blocks at the bottom of the file. Save and quit.

**6. Apply the Zero-Trust Routing Rules**
Run the following command to append the new routing rules:

```bash
echo -e "\nMatch User transfer_user\n    ChrootDirectory /var/sftp\n    ForceCommand internal-sftp\n    AllowTcpForwarding no\n    X11Forwarding no" | sudo tee -a /etc/ssh/sshd_config
```

*Explanation of rules:* `Match User` targets the specific account. `ChrootDirectory` confines them to the jail. `ForceCommand internal-sftp` restricts activity to file transfers only. The forwarding rules prevent the user from tunneling or opening graphical apps.

**7. Restart the SSH Service**
Apply the new configuration:

```bash
sudo systemctl restart ssh
```

*(Note: Use `sshd` instead of `ssh` depending on your specific Linux distribution).*

**8. Verify the Manual Connection**
From your client machine (macOS), verify the connection:

```bash
sftp transfer_user@<YOUR_VM_IP>
```

Once authenticated, running `ls` should reveal that the user is successfully trapped and can only see the `uploads` directory. Type `exit` to close the session.

## 6. Execution

First, create a simple text file locally to act as the payload:

```bash
echo "Automated Server" > test_report.txt
```

### Without Automation (Manual Execution)

To send files without the Python automation script, establish the connection, drop the file, and exit:

```bash
sftp transfer_user@<YOUR_VM_IP>
sftp> put test_report.txt
sftp> exit
```

Verify on the remote server: `cat /var/sftp/uploads/test_report.txt`.

### With Automation (Python Pipeline)

Automating this process makes it scalable, allows it to be run with a cron job, and removes human error.

**Prerequisites:** Install `paramiko` and `python-dotenv`. Ensure your `.env` file is set up in the same directory as the `auto_sftp.py` file, otherwise it will throw an error.

**Automation Logic:**

* `ssh.connect(...)`: Establishes a TCP 3-way handshake over port 22. The `timeout=10` parameter is used to throw an exception if the handshake is not completed within 10 seconds. After the connection is solidified, `paramiko` initiates SSHv2.

* `ssh.open_sftp()`: Instructs the SSH server *not* to create a standard shell. Instead, it requests the SFTP Subsystem over the established TCP connection, eliminating standard overhead.

* `sftp.put(...)`: Bypasses terminal commands natively, securely handling the byte transfer.

Execute the script:

```bash
python auto_sftp.py
```

A "Transfer Successful!" log confirms execution. Verify on the remote server: `cat /var/sftp/uploads/test_report.txt`.

## 7. Future Enhancements

There are two limitations to this project that I would want to deal with in the future:

1. **Multi-Node Deployment:** Upgrading the script to concurrently send payloads to multiple VMs instead of just a single target.

2. **Automated Retry Logic:** Wrapping the connection in a retry block with exponential backoff to allow the program to survive temporary network drops.

## 8. Development Notes

AI tools were utilized for architecture consultation and generating boilerplate Python structures. The code was then manually refactored for enterprise security, including integrating the `dotenv` module to prevent hardcoded credentials and implementing custom exception handling.