import os
import ssl
import logging
import hashlib
import hmac
import time
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from typing import Tuple, Optional

logger = logging.getLogger('Security')

class SecurityManager:
    def __init__(self):
        self.encryption_key = None
        self.cipher_suite = None
        self.private_key = None
        self.public_key = None
        self._initialize_security()

    def _initialize_security(self):
        """Initialize security components"""
        # Generate encryption key
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        self.encryption_key = base64.urlsafe_b64encode(kdf.derive(os.urandom(32)))
        self.cipher_suite = Fernet(self.encryption_key)

        # Generate RSA key pair
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()

    def create_ssl_context(self, is_server: bool = True) -> ssl.SSLContext:
        """Create SSL context for secure communication"""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER if is_server else ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        
        # Configure cipher suites
        context.set_ciphers('ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384')
        
        # Enable certificate verification
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
        
        return context

    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using Fernet symmetric encryption"""
        try:
            return self.cipher_suite.encrypt(data)
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            return b''

    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using Fernet symmetric encryption"""
        try:
            return self.cipher_suite.decrypt(encrypted_data)
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return b''

    def sign_data(self, data: bytes) -> bytes:
        """Sign data using RSA private key"""
        try:
            signature = self.private_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return signature
        except Exception as e:
            logger.error(f"Signing error: {e}")
            return b''

    def verify_signature(self, data: bytes, signature: bytes) -> bool:
        """Verify signature using RSA public key"""
        try:
            self.public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False

    def generate_challenge(self) -> Tuple[bytes, bytes]:
        """Generate challenge for mutual authentication"""
        challenge = os.urandom(32)
        timestamp = str(int(time.time())).encode()
        return challenge, timestamp

    def verify_challenge(self, challenge: bytes, response: bytes, timestamp: bytes) -> bool:
        """Verify challenge response"""
        try:
            # Verify timestamp is within acceptable range
            current_time = int(time.time())
            challenge_time = int(timestamp.decode())
            if abs(current_time - challenge_time) > 30:  # 30 seconds tolerance
                return False

            # Verify challenge response
            expected_response = hmac.new(
                self.encryption_key,
                challenge + timestamp,
                hashlib.sha256
            ).digest()
            
            return hmac.compare_digest(response, expected_response)
        except Exception as e:
            logger.error(f"Challenge verification error: {e}")
            return False

    def export_public_key(self) -> bytes:
        """Export public key in PEM format"""
        try:
            return self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        except Exception as e:
            logger.error(f"Public key export error: {e}")
            return b''

    def import_public_key(self, public_key_data: bytes) -> bool:
        """Import public key from PEM format"""
        try:
            self.public_key = serialization.load_pem_public_key(public_key_data)
            return True
        except Exception as e:
            logger.error(f"Public key import error: {e}")
            return False

    def generate_session_key(self) -> bytes:
        """Generate session key for secure communication"""
        return os.urandom(32)

    def hash_password(self, password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """Hash password using PBKDF2"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = kdf.derive(password.encode())
        return key, salt 