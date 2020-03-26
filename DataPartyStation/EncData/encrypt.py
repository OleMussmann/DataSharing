#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This script is to read the new data file which was generated by prepare.py (hashed linking features + actual data). 
Then, sign-encrypt (symmetric key) -sign the data file and sign-encrypt (public-private key)-sign on the key file.

"""

import time
start_time = time.time()
import base64
import nacl.encoding
import PQencryption as cr
import requests, json, yaml, uuid
import redacted_logging as rlog


def load_yaml_file(file_name, logger):
    """loads a yaml file, logs to logger if errors occur

    Args:
        file_name (str): File name of the YAML file to be loaded.
        logger (logging.Logger): Logger class handling log messages.

    Raises:
        FileNotFoundError: If the yaml file can not be found.

    Returns:
        dict: yaml file content as a dictionary.
    """
    try:
        with open(file_name) as file:
            inputYAML = yaml.load(file, Loader=yaml.FullLoader)
            logger.debug("Reading encrypt_input.yaml file...")
    except yaml.parser.ParserError:
        logger.error(f"File {file} is not valid YAML.")
        raise
    except FileNotFoundError:
        logger.error(f"Trying to read file '{file}', but it does not exist.")
        raise

    return inputYAML


def import_keys_from_yaml(inputYAML):
    """loads a yaml file, logs to logger if errors occur

    Args:
        inputYAML (dict): a dictionay from reading the yaml file.

    Raises:
        KeyError: If the key is not in the yaml file.

    Returns:
        four keys - signing_key, quantum_safe_public_key, 
        classic_public_key_tse, classic_secret_key.
    """

    try:
        ### create and reading keys ###
        # read values from yaml file 
        signing_key_yaml = inputYAML['signing_key']
        quantum_safe_public_key_yaml = inputYAML['quantum_safe_public_key']
        classic_public_key_tse_yaml = inputYAML['classic_public_key_tse']
        classic_private_key_yaml = inputYAML['classic_private_key']


        # symmetric_encryption_key 
        encryption_key = cr.Salsa20.key_gen()
        encryptionKeyBase64 = nacl.encoding.Base64Encoder.encode(bytes(encryption_key.key)).decode("utf-8")

        path = '/inputVolume/'
        # read signing key from itself
        signing_key = cr.import_key(path + signing_key_yaml, silent=False) 
        # read quantum safe public key from tse
        quantum_safe_public_key = cr.import_key(path + quantum_safe_public_key_yaml, silent=False) 
        # read quantum vulnerable public key from tse
        classic_public_key_tse = cr.import_key(path + classic_public_key_tse_yaml, silent=False) 
        # read quantum vulnerable private key from itself
        classic_secret_key = cr.import_key(path + classic_private_key_yaml, silent=False) 
    except KeyError:
        logger.error("YAML file not valid. Please consult the example " +
                        "'encrypt_input.yaml' file and edit in your settings.")
    except: 
        logger.error("Failed to create or import encryption keys !")
        raise

    return signing_key, quantum_safe_public_key, classic_public_key_tse, classic_secret_key


def save_encrypted_data_file(signed_encrypted_signed_message, local_save, receiver_address, fileStr):
    """send the signed_encrypted_signed_data file to TSE(URL)
        or save it locally 

    Args:
        signed_encrypted_signed_message (str): signed encrypted signed data file.

    Raises:
       errors in sending or saving file procedure

    Returns:
        Nothing
    """


    ### Send or save encrypted data file ###
    # Send file to TTP service
    if receiver_address != False:
        #save encrypted file temporarily
        text_file = open("/data/%s.enc" %(fileStr), "w")
        text_file.write(signed_encrypted_signed_message)
        text_file.close()

        # Send data file #
        try: 
            res = requests.post(url=receiver_address+'/addFile',
                files={"fileObj": open('/data/%s.enc' %(fileStr), 'r')})
            #get the uuid of the stored file at TTP
            resultJson = json.loads(res.text.encode("utf-8"))
            saved_status = resultJson["status"]
            saved_uuid = resultJson["uuid"]
        except:
            logger.error("Failed to send files to %s" %receiver_address)


    # Save data file locally
    if local_save:
        try:
            # Save encrypted data file locally #
            saved_uuid = str(uuid.uuid4())
            output_file = open("/output/%s.enc" %(saved_uuid), "w")
            output_file.write(signed_encrypted_signed_message)
            output_file.close()
            logger.info("Encrypted data is successfully saved at local machine.")
            logger.info("UUID: %s" % saved_uuid)
        except:
            logger.error("Failed to seve files locally")
            raise


def main():
    """main function

    The main function will import the four keys, sign-(symmetric)encrypt-sign the data file, and 
    sign-(public-priavte key)encrypt-sign for the key file. Then signed-encrypted-signed data and
    key files will be sent to TSE or saved locally.
    """

    logger = rlog.get_logger(__name__)
    input_yaml_file_name = r'/inputVolume/encrypt_input.yaml'
    inputYAML = load_yaml_file(input_yaml_file_name, logger)

    ### import encryption keys ###
    signing_key, quantum_safe_public_key, classic_public_key_tse, classic_secret_key = import_keys_from_yaml(inputYAML)

    try:
        party_name = inputYAML['party_name']
        receiver_address = inputYAML['receiver_address']
        local_save = inputYAML['local_save']
    except KeyError:
        logger.error("YAML file not valid. Please consult the example " +
                        "'encrypt_input.

    # read the new data file (hashed linking features + actual data)generated by prepare.py
    fileStr = party_name
    myStr = open("/data/encrypted_%s.csv" %(fileStr), 'r').read()

    try:
        #sign->encrypt->sign procedure
        signed_encrypted_signed_message = cr.sign_encrypt_sign_symmetric(signing_key,encryption_key, myStr)
    except:
        logger.error("Procedure of Sign-encrypt-sign failed!")
        raise
            

    ### send or save encrypted data file ###
    save_encrypted_data_file(signed_encrypted_signed_message, local_save, receiver_address, fileStr)
        

    ### sign-encrypt-sign on the keys file ###
    try:
        result = {
            "%sfileUUID" %(fileStr): saved_uuid,
            "%sencryptKey" %(fileStr): cr.sign_encrypt_sign_pubkey(signing_key, quantum_safe_public_key, classic_secret_key, classic_public_key_tse, encryptionKeyBase64)
        }
    except:
        logger.error("Sign-encrypt-sign procedure on the key file is failed!!")
            raise

    ### Save keys files in output folder ###
    with open('output/%s_data_keys.json' %(fileStr), 'w') as fp:
        json.dump(result, fp)
    logger.info("Your data keys are stored in output folder")

    logger.info("Data encryption program took {runtime:.4f}s to run".format(runtime=time.time() - start_time))