import os, tarfile
from cryptography.fernet import Fernet
from base64 import urlsafe_b64encode

def _validate_and_decode_encryption_key(encryption_key):
    encryption_bytes = bytes.fromhex(encryption_key)
    if len(encryption_bytes) != 32:
        raise ValueError("encryption key must be 32 bytes long")
    return encryption_bytes

def encrypt(encryption_key, input_file, output_file):
    encryption_bytes = _validate_and_decode_encryption_key(encryption_key)
    fernet = Fernet(urlsafe_b64encode(encryption_bytes))
    with open(input_file, 'rb') as f:
        original = f.read()
    encrypted  = fernet.encrypt(original)

    with open(output_file, 'wb') as f:
        f.write(encrypted)

def decrypt(encryption_key, input_file, output_file):
    encryption_bytes = _validate_and_decode_encryption_key(encryption_key)
    fernet = Fernet(urlsafe_b64encode(encryption_bytes))
    with open(input_file, 'rb') as f:
        encrypted = f.read()
    original  = fernet.decrypt(encrypted)

    with open(output_file, 'wb') as f:
        f.write(original)

def tar(input_path, output_file):
    input_path = os.path.abspath(input_path)
    if not os.path.exists(input_path):
        raise FileNotFoundError(input_path)
    current_dir = os.getcwd()
    try:
        working_dir = ''
        target = ''
        if os.path.isfile(input_path):
            working_dir = os.path.dirname(input_path)
            target = os.path.basename(input_path)
        else:
            working_dir = input_path
            target = '.'
        os.chdir(working_dir)
        with tarfile.open(output_file, "w:gz") as tar:
            tar.add(target)
    finally:
        os.chdir(current_dir)

def untar(input_file, output_dir):
    if not os.path.exists(input_file):
        raise FileNotFoundError(input_file)
    with tarfile.open(input_file, "r:gz") as tar:
        tar.extractall(output_dir)

