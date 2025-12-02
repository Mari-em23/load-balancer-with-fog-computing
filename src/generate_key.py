from cryptography.hazmat.primitives.ciphers.aead import AESGCM
key = AESGCM.generate_key(bit_length=128)
print("Clé de chiffrement générée:"+key.hex())