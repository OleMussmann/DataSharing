# -*- coding: utf-8 -*-
""" AES 256 symmetric block encryption cipher.

Uses 256 bits key length for increased security against Grover's algorithm,
thus safe against known quantum computer attacks. Wrapper around the Crypto
package.

class AES256 provides a cipher object for en- and decryption. Without
instantiation you can use key_gen() to generate keys.

class AES256Key provides key objects. The raw key can be found in KEYNAME.key.
Without instantiation, calling import_key() reads a keyfile and returns a key
object.
"""

from __future__ import print_function  # make print python3 compatible

import nacl.encoding
import gc  # garbage collector
from Crypto import Random
from Crypto.Cipher import AES
from .Key import _Key
from .sha512 import hash512
from .salsa20 import Salsa20, Salsa20Key
from .utilities import _get_password

key_length = 32
key_name = "SECRET_AES_256_Key"
key_description = key_name + " for AES 256 symmetric block encryption"

class AES256(object):
    """ Cipher object for en- and decryption.

    Attributes:
        block_size: AES block size.
        key: The raw key.

    Methods:
        encrypt: Encrypt plaintext with AES 256 cipher.
        decrypt: Encrypt ciphertext with AES 256 cipher.
        key_gen: Generate a key object, containing a symmetric AES 256 key. Can
                be called without instantiation.
        _pad: Pad plaintext to fill the last AES block.
        _unpad: Unpad padded string.
    """
    def __init__(self, key_object):
        key = bytes(key_object.key)
        self.block_size = AES.block_size
        self.key = key

    def encrypt(self, message_unencoded):
        """ Encrypts cleartext with an AES 256 symmetric cipher.

        Args:
            message_unencoded: Plain text string.

        Returns:
            Base64 encoded ciphertext.
        """
        initialization_vector = Random.new().read(AES.block_size)
        message_unencoded = self._pad(message_unencoded, self.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, initialization_vector)
        return nacl.encoding.Base64Encoder.encode(
                initialization_vector \
                        + cipher.encrypt(message_unencoded)).decode("utf-8")

    def decrypt(self, encrypted_message_base64):
        """ Decrypts ciphertext with an AES 256 symmetric cipher.

        WARNING! Decrypting invalid ciphertext might return an emtpy string
        instead of raising an error. Code defensively to account for this.

        Args:
            encrypted_message_base64: Base64 encoded ciphertext.

        Returns:
            Cleartext message string if decryption is successful.
        """
        enc = nacl.encoding.Base64Encoder.decode(encrypted_message_base64)
        initialization_vector = enc[:self.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, initialization_vector)
        return self._unpad(cipher.decrypt(enc[self.block_size:])).decode('utf-8')

    def _pad(self, s, block_size):  # using PKCS#7 style padding
        return s + (block_size - len(s) % block_size) \
                * chr(block_size - len(s) % block_size)

    def _unpad(self, s):  # using PKCS#7 style padding
        return s[:-ord(s[len(s)-1:])]

    @staticmethod
    def key_gen(size=32):
        """ Key generation for symmetric AES 256 encryption.

        Args:
            Size (int): size/length of the key.
        Returns:
            Symmetric key object.
        """
        key = Random.new().read(size)
        return AES256Key(bytearray(key))

class AES256Key(_Key):
    """ Key object for en- and decryption.

    Attributes:
        key: The raw key.
        name: The key name.
        description: Verbose description of key type.
        header: Header for exporting to a file, also contains the description.
        footer: Footer for exporting to a file.
        security_level: String, "SECRET" if encrypted storage is needed,
                        "Private" if not.

    Methods:
        export_key: Export the raw key to a key file.
        import _key: Creates a key object from the content of a key file. Can
                     be called without instantiation.
        _check_length: Verify the length of the raw key.
        _is_valid: Self check for validity.
    """
    def __init__(self, key):
        super(AES256Key, self).__init__(key, key_name, key_description)
        self.key = key
        self.key_length = key_length
        self._check_length(self.key_length)
        self.security_level = "SECRET"

    def _is_valid(self):
        if type(self.key) != bytearray:
            return False
        elif len(self.key) != self.key_length:
            return False
        else:
            return True

    @staticmethod
    def import_key(file_name_with_path, silent=False):
        """ Creates a key object from a key file.

        Attributes:
            file_name_with_path: Key_file.
            silent: Don't print password requirements if set True.

        Returns:
            AES256Key object.

        Raises:
            IOError: When opening a wrong file.
            TypeError: When key in file is invalid.
            ValueError: When decryption passwords do not match requirements.
            nacl.exceptions.CryptoError: When key decryption fails.
        """
        with open(file_name_with_path) as f:
            header = f.readline().rstrip()
            encrypted_key_base64 = f.readline().rstrip()
            footer = f.readline().rstrip()
        if not key_description in header:
            raise TypeError("Key is not a AES 256 symmetric key.")
        if not footer == _Key.footer:
            raise TypeError("Key is not a valid key.")
        if silent:
            user_password = _get_password(validate=False,
                    print_requirements=False)
        else:
            user_password = _get_password(validate=False)
        storage_password = \
                nacl.encoding.Base64Encoder.decode(hash512(user_password))[:32]
        storage_key = Salsa20Key(storage_password)
        symmetric_cipher = Salsa20(storage_key)
        decrypted_key_base64 = symmetric_cipher.decrypt(encrypted_key_base64)
        decrypted_key = nacl.encoding.Base64Encoder.decode(
                decrypted_key_base64)
        return AES256Key(bytearray(decrypted_key))