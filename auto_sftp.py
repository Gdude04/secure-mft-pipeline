import os
import sys
import logging
import paramiko
from dotenv import load_dotenv

# Load environment variables from the .env file into os.environ
load_dotenv()

# Configure console logging to display severity level and message
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def run_transfer(local_path: str, remote_path: str, host: str, port: int = 22) -> bool:
    """
    Connects to a remote server via SSH and uploads a single file over SFTP.
    Returns True if the transfer succeeds, or False if any step fails.
    """
    username = os.getenv('SFTP_USERNAME')
    password = os.getenv('SFTP_PASSWORD')

    # Fail fast if credentials are missing from the environment
    if not username or not password:
        logging.error("Need SFTP_USERNAME and SFTP_PASSWORD to be set")
        return False

    # Verify the local file exists before opening a network connection
    if not os.path.isfile(local_path):
        logging.error(f"The local file was not found: {local_path}")
        return False

    logging.info(f"Connecting to {host}:{port}")

    ssh = paramiko.SSHClient()
    # Automatically accept unknown SSH host keys (convenient for testing, insecure for production)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(host, port=port, username=username, password=password, timeout=10)

        # Use a context manager so the SFTP session closes automatically after the upload
        with ssh.open_sftp() as sftp:
            logging.info(f"Uploading {local_path} -> {remote_path}...")
            sftp.put(local_path, remote_path)

        logging.info("Transfer successful!")
        return True
    except paramiko.AuthenticationException:
        logging.error("Authentication failed. Check credentials.")
    except FileNotFoundError:
        logging.error(f"Remote directory does not exist for path: {remote_path}")
    except Exception as e:
        logging.error(f"Transfer failed due to unexpected error: {e}")
    finally:
        # Always close the underlying SSH transport connection, even if an error occurred
        ssh.close()

    # Execution only reaches this line if an exception was caught above
    return False


if __name__ == '__main__':
    # Read transfer parameters from .env, falling back to default test values if unset
    TARGET_HOST = os.getenv('SFTP_HOST', '192.168.152.129')
    TARGET_PORT = int(os.getenv('SFTP_PORT', 22))
    LOCAL_FILE = os.getenv('SFTP_LOCAL_FILE', 'test_report.txt')
    REMOTE_DESTINATION = os.getenv('SFTP_REMOTE_DESTINATION', '/uploads/test_report.txt')

    # Single exit point: terminate with exit code 1 if the transfer failed for any reason
    if not run_transfer(LOCAL_FILE, REMOTE_DESTINATION, TARGET_HOST, TARGET_PORT):
        sys.exit(1)
