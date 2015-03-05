# -*- coding: utf-8 -*-

""" OneLogin_Saml2_Utils class

Copyright (c) 2014, OneLogin, Inc.
All rights reserved.

Auxiliary class of OneLogin's Python Toolkit.

"""

import base64
from datetime import datetime
import calendar
from hashlib import sha1
from isodate import parse_duration as duration_parser
import re
from textwrap import wrap
from uuid import uuid4

import zlib
import xmlsec

from onelogin.saml2 import compat
from onelogin.saml2.constants import OneLogin_Saml2_Constants
from onelogin.saml2.errors import OneLogin_Saml2_Error
from onelogin.saml2.xml_utils import OneLogin_Saml2_XML


try:
    from urllib.parse import quote_plus  # py3
except ImportError:
    from urllib import quote_plus  # py2


class OneLogin_Saml2_Utils(object):
    """

    Auxiliary class that contains several utility methods to parse time,
    urls, add sign, encrypt, decrypt, sign validation, handle xml ...

    """
    @staticmethod
    def escape_url(url):
        """
        escape the non-safe symbols in url
        :param url: the url to escape
        :type url: str
        :return: the escaped url
        :rtype str
        """
        return quote_plus(url)

    @staticmethod
    def b64encode(s):
        """base64 encode"""
        return compat.to_string(base64.b64encode(compat.to_bytes(s)))

    @staticmethod
    def b64decode(s):
        """base64 decode"""
        return base64.b64decode(s)

    @staticmethod
    def decode_base64_and_inflate(value, ignore_zip=False):
        """
        base64 decodes and then inflates according to RFC1951
        :param value: a deflated and encoded string
        :type value: string
        :param ignore_zip: ignore zip errors
        :returns: the string after decoding and inflating
        :rtype: string
        """
        encoded = OneLogin_Saml2_Utils.b64decode(value)
        try:
            return zlib.decompress(encoded, -15)
        except zlib.error:
            if not ignore_zip:
                raise
        return encoded

    @staticmethod
    def deflate_and_base64_encode(value):
        """
        Deflates and the base64 encodes a string
        :param value: The string to deflate and encode
        :type value: string
        :returns: The deflated and encoded string
        :rtype: string
        """
        return OneLogin_Saml2_Utils.b64encode(zlib.compress(compat.to_bytes(value))[2:-4])

    @staticmethod
    def format_cert(cert, heads=True):
        """
        Returns a x509 cert (adding header & footer if required).

        :param cert: A x509 unformated cert
        :type: string

        :param heads: True if we want to include head and footer
        :type: boolean

        :returns: Formated cert
        :rtype: string
        """

        cert = compat.to_string(cert)
        x509_cert = cert.replace('\x0D', '')
        x509_cert = x509_cert.replace('\r', '')
        x509_cert = x509_cert.replace('\n', '')
        if len(x509_cert) > 0:
            x509_cert = x509_cert.replace('-----BEGIN CERTIFICATE-----', '')
            x509_cert = x509_cert.replace('-----END CERTIFICATE-----', '')
            x509_cert = x509_cert.replace(' ', '')

            if heads:
                x509_cert = "-----BEGIN CERTIFICATE-----\n" + "\n".join(wrap(x509_cert, 64)) + "\n-----END CERTIFICATE-----\n"

        return x509_cert

    @staticmethod
    def format_private_key(key, heads=True):
        """
        Returns a private key (adding header & footer if required).

        :param key A private key
        :type: string

        :param heads: True if we want to include head and footer
        :type: boolean

        :returns: Formated private key
        :rtype: string
        """

        key = compat.to_string(key)
        private_key = key.replace('\x0D', '')
        private_key = private_key.replace('\r', '')
        private_key = private_key.replace('\n', '')
        if len(private_key) > 0:
            if private_key.find('-----BEGIN PRIVATE KEY-----') != -1:
                private_key = private_key.replace('-----BEGIN PRIVATE KEY-----', '')
                private_key = private_key.replace('-----END PRIVATE KEY-----', '')
                private_key = private_key.replace(' ', '')
                if heads:
                    private_key = "-----BEGIN PRIVATE KEY-----\n" + "\n".join(wrap(private_key, 64)) + "\n-----END PRIVATE KEY-----\n"
            else:
                private_key = private_key.replace('-----BEGIN RSA PRIVATE KEY-----', '')
                private_key = private_key.replace('-----END RSA PRIVATE KEY-----', '')
                private_key = private_key.replace(' ', '')
                if heads:
                    private_key = "-----BEGIN RSA PRIVATE KEY-----\n" + "\n".join(wrap(private_key, 64)) + "\n-----END RSA PRIVATE KEY-----\n"
        return private_key

    @staticmethod
    def redirect(url, parameters={}, request_data={}):
        """
        Executes a redirection to the provided url (or return the target url).

        :param url: The target url
        :type: string

        :param parameters: Extra parameters to be passed as part of the url
        :type: dict

        :param request_data: The request as a dict
        :type: dict

        :returns: Url
        :rtype: string
        """
        assert isinstance(url, compat.str_type)
        assert isinstance(parameters, dict)

        if url.startswith('/'):
            url = '%s%s' % (OneLogin_Saml2_Utils.get_self_url_host(request_data), url)

        # Verify that the URL is to a http or https site.
        if re.search('^https?://', url) is None:
            raise OneLogin_Saml2_Error(
                'Redirect to invalid URL: ' + url,
                OneLogin_Saml2_Error.REDIRECT_INVALID_URL
            )

        # Add encoded parameters
        if url.find('?') < 0:
            param_prefix = '?'
        else:
            param_prefix = '&'

        for name, value in parameters.items():

            if value is None:
                param = OneLogin_Saml2_Utils.escape_url(name)
            elif isinstance(value, list):
                param = ''
                for val in value:
                    param += OneLogin_Saml2_Utils.escape_url(name) + '[]=' + OneLogin_Saml2_Utils.escape_url(val) + '&'
                if len(param) > 0:
                    param = param[0:-1]
            else:
                param = OneLogin_Saml2_Utils.escape_url(name) + '=' + OneLogin_Saml2_Utils.escape_url(value)

            if param:
                url += param_prefix + param
                param_prefix = '&'

        return url

    @staticmethod
    def abs_url(uri, request_data=None):
        """
        get absolute url by local uri
        :param uri: the uri
        :param request_data: the request data
        :return: the absolute url for resource
        """
        if uri.startswith('/'):
            if request_data is None:
                request_data = dict()
            uri = '%s%s' % (OneLogin_Saml2_Utils.get_self_url_host(request_data), uri)

        return uri

    @staticmethod
    def get_self_url_host(request_data):
        """
        Returns the protocol + the current host + the port (if different than
        common ports).

        :param request_data: The request as a dict
        :type: dict

        :return: Url
        :rtype: string
        """
        current_host = OneLogin_Saml2_Utils.get_self_host(request_data)
        port = ''
        if OneLogin_Saml2_Utils.is_https(request_data):
            protocol = 'https'
        else:
            protocol = 'http'

        if 'server_port' in request_data:
            port_number = str(request_data['server_port'])
            port = ':' + port_number

            if protocol == 'http' and port_number == '80':
                port = ''
            elif protocol == 'https' and port_number == '443':
                port = ''

        return '%s://%s%s' % (protocol, current_host, port)

    @staticmethod
    def get_self_host(request_data):
        """
        Returns the current host.

        :param request_data: The request as a dict
        :type: dict

        :return: The current host
        :rtype: string
        """
        if 'http_host' in request_data:
            current_host = request_data['http_host']
        elif 'server_name' in request_data:
            current_host = request_data['server_name']
        else:
            raise Exception('No hostname defined')

        if ':' in current_host:
            current_host_data = current_host.split(':')
            possible_port = current_host_data[-1]
            try:
                int(possible_port)
                current_host = current_host_data[0]
            except ValueError:
                current_host = ':'.join(current_host_data)

        return current_host

    @staticmethod
    def is_https(request_data):
        """
        Checks if https or http.

        :param request_data: The request as a dict
        :type: dict

        :return: False if https is not active
        :rtype: boolean
        """
        is_https = 'https' in request_data and request_data['https'] != 'off'
        is_https = is_https or ('server_port' in request_data and str(request_data['server_port']) == '443')
        return is_https

    @staticmethod
    def get_self_url_no_query(request_data):
        """
        Returns the URL of the current host + current view.

        :param request_data: The request as a dict
        :type: dict

        :return: The url of current host + current view
        :rtype: string
        """
        self_url_host = OneLogin_Saml2_Utils.get_self_url_host(request_data)
        script_name = request_data['script_name']
        if script_name:
            if script_name[0] != '/':
                script_name = '/' + script_name
        else:
            script_name = ''
        self_url_no_query = self_url_host + script_name
        if 'path_info' in request_data:
            self_url_no_query += request_data['path_info']

        return self_url_no_query

    @staticmethod
    def get_self_routed_url_no_query(request_data):
        """
        Returns the routed URL of the current host + current view.

        :param request_data: The request as a dict
        :type: dict

        :return: The url of current host + current view
        :rtype: string
        """
        self_url_host = OneLogin_Saml2_Utils.get_self_url_host(request_data)
        route = ''
        if 'request_uri' in request_data and request_data['request_uri']:
            route = request_data['request_uri']
            if 'query_string' in request_data and request_data['query_string']:
                route = route.replace(request_data['query_string'], '')

        return self_url_host + route

    @staticmethod
    def get_self_url(request_data):
        """
        Returns the URL of the current host + current view + query.

        :param request_data: The request as a dict
        :type: dict

        :return: The url of current host + current view + query
        :rtype: string
        """
        self_url_host = OneLogin_Saml2_Utils.get_self_url_host(request_data)

        request_uri = ''
        if 'request_uri' in request_data:
            request_uri = request_data['request_uri']
            if not request_uri.startswith('/'):
                match = re.search('^https?://[^/]*(/.*)', request_uri)
                if match is not None:
                    request_uri = match.groups()[0]

        return self_url_host + request_uri

    @staticmethod
    def generate_unique_id():
        """
        Generates an unique string (used for example as ID for assertions).

        :return: A unique string
        :rtype: string
        """
        return 'ONELOGIN_%s' % sha1(compat.to_bytes(uuid4().hex)).hexdigest()

    @staticmethod
    def parse_time_to_SAML(time):
        """
        Converts a UNIX timestamp to SAML2 timestamp on the form
        yyyy-mm-ddThh:mm:ss(\.s+)?Z.

        :param time: The time we should convert (DateTime).
        :type: string

        :return: SAML2 timestamp.
        :rtype: string
        """
        data = datetime.utcfromtimestamp(float(time))
        return data.strftime('%Y-%m-%dT%H:%M:%SZ')

    @staticmethod
    def parse_SAML_to_time(timestr):
        """
        Converts a SAML2 timestamp on the form yyyy-mm-ddThh:mm:ss(\.s+)?Z
        to a UNIX timestamp. The sub-second part is ignored.

        :param timestr: The time we should convert (SAML Timestamp).
        :type: string

        :return: Converted to a unix timestamp.
        :rtype: int
        """
        try:
            data = datetime.strptime(timestr, '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            data = datetime.strptime(timestr, '%Y-%m-%dT%H:%M:%S.%fZ')
        return calendar.timegm(data.utctimetuple())

    @staticmethod
    def now():
        """
        :return: unix timestamp of actual time.
        :rtype: int
        """
        return calendar.timegm(datetime.utcnow().utctimetuple())

    @staticmethod
    def parse_duration(duration, timestamp=None):
        """
        Interprets a ISO8601 duration value relative to a given timestamp.

        :param duration: The duration, as a string.
        :type: string

        :param timestamp: The unix timestamp we should apply the duration to.
                          Optional, default to the current time.
        :type: string

        :return: The new timestamp, after the duration is applied.
        :rtype: int
        """
        assert isinstance(duration, compat.str_type)
        assert timestamp is None or isinstance(timestamp, int)

        timedelta = duration_parser(duration)
        if timestamp is None:
            data = datetime.utcnow() + timedelta
        else:
            data = datetime.utcfromtimestamp(timestamp) + timedelta
        return calendar.timegm(data.utctimetuple())

    @staticmethod
    def get_expire_time(cache_duration=None, valid_until=None):
        """
        Compares 2 dates and returns the earliest.

        :param cache_duration: The duration, as a string.
        :type: string

        :param valid_until: The valid until date, as a string or as a timestamp
        :type: string

        :return: The expiration time.
        :rtype: int
        """
        expire_time = None

        if cache_duration is not None:
            expire_time = OneLogin_Saml2_Utils.parse_duration(cache_duration)

        if valid_until is not None:
            if isinstance(valid_until, int):
                valid_until_time = valid_until
            else:
                valid_until_time = OneLogin_Saml2_Utils.parse_SAML_to_time(valid_until)
            if expire_time is None or expire_time > valid_until_time:
                expire_time = valid_until_time

        if expire_time is not None:
            return '%d' % expire_time
        return None

    @staticmethod
    def delete_local_session(callback=None):
        """
        Deletes the local session.
        """

        if callback is not None:
            callback()

    @staticmethod
    def calculate_x509_fingerprint(x509_cert):
        """
        Calculates the fingerprint of a x509cert.

        :param x509_cert: x509 cert
        :type: string

        :returns: Formated fingerprint
        :rtype: string
        """
        assert isinstance(x509_cert, compat.str_type)

        lines = x509_cert.split('\n')
        data = ''

        for line in lines:
            # Remove '\r' from end of line if present.
            line = line.rstrip()
            if line == '-----BEGIN CERTIFICATE-----':
                # Delete junk from before the certificate.
                data = ''
            elif line == '-----END CERTIFICATE-----':
                # Ignore data after the certificate.
                break
            elif line == '-----BEGIN PUBLIC KEY-----' or line == '-----BEGIN RSA PRIVATE KEY-----':
                # This isn't an X509 certificate.
                return None
            else:
                # Append the current line to the certificate data.
                data += line
        # "data" now contains the certificate as a base64-encoded string. The
        # fingerprint of the certificate is the sha1-hash of the certificate.
        return sha1(base64.b64decode(compat.to_bytes(data))).hexdigest().lower()

    @staticmethod
    def format_finger_print(fingerprint):
        """
        Formates a fingerprint.

        :param fingerprint: fingerprint
        :type: string

        :returns: Formated fingerprint
        :rtype: string
        """
        formated_fingerprint = fingerprint.replace(':', '')
        return formated_fingerprint.lower()

    @staticmethod
    def generate_name_id(value, sp_nq, sp_format, cert=None, debug=False):
        """
        Generates a nameID.

        :param value: fingerprint
        :type: string

        :param sp_nq: SP Name Qualifier
        :type: string

        :param sp_format: SP Format
        :type: string

        :param cert: IdP Public Cert to encrypt the nameID
        :type: string

        :param debug: Activate the xmlsec debug
        :type: bool

        :returns: DOMElement | XMLSec nameID
        :rtype: string
        """

        root = OneLogin_Saml2_XML.make_root("{%s}container" % OneLogin_Saml2_Constants.NS_SAML)
        name_id = OneLogin_Saml2_XML.make_child(root, '{%s}NameID' % OneLogin_Saml2_Constants.NS_SAML)
        name_id.set('SPNameQualifier', sp_nq)
        name_id.set('Format', sp_format)
        name_id.text = value

        if cert is not None:
            xmlsec.enable_debug_trace(debug)

            # Load the public cert
            manager = xmlsec.KeysManager()
            manager.add_key(xmlsec.Key.from_memory(cert, xmlsec.KeyFormat.CERT_PEM, None))

            # Prepare for encryption
            enc_data = xmlsec.template.encrypted_data_create(
                root, xmlsec.Transform.AES128, type=xmlsec.EncryptionType.ELEMENT)

            xmlsec.template.encrypted_data_ensure_cipher_value(enc_data)
            key_info = xmlsec.template.encrypted_data_ensure_key_info(enc_data)
            enc_key = xmlsec.template.add_encrypted_key(key_info, xmlsec.Transform.RSA_OAEP)
            xmlsec.template.encrypted_data_ensure_cipher_value(enc_key)

            # Encrypt!
            enc_ctx = xmlsec.EncryptionContext(manager)
            enc_ctx.key = xmlsec.Key.generate(xmlsec.KeyData.AES, 128, xmlsec.KeyDataType.SESSION)
            enc_ctx.encrypt_xml(enc_data, name_id)
            new_root = OneLogin_Saml2_XML.make_root(root.tag, nsmap={"dsig": OneLogin_Saml2_Constants.NS_DS, "xenc": OneLogin_Saml2_Constants.NS_XENC})
            new_root[:] = root[:]
            return '<saml:EncryptedID>' + compat.to_string(OneLogin_Saml2_XML.to_string(new_root[0])) + '</saml:EncryptedID>'
        else:
            return OneLogin_Saml2_XML.extract_tag_text(root, "saml:NameID")

    @staticmethod
    def get_status(dom):
        """
        Gets Status from a Response.

        :param dom: The Response as XML
        :type: Document

        :returns: The Status, an array with the code and a message.
        :rtype: dict
        """
        status = {}

        status_entry = OneLogin_Saml2_XML.query(dom, '/samlp:Response/samlp:Status')
        if len(status_entry) == 0:
            raise Exception('Missing Status on response')

        code_entry = OneLogin_Saml2_XML.query(dom, '/samlp:Response/samlp:Status/samlp:StatusCode', status_entry[0])
        if len(code_entry) == 0:
            raise Exception('Missing Status Code on response')
        code = code_entry[0].values()[0]
        status['code'] = code

        message_entry = OneLogin_Saml2_XML.query(dom, '/samlp:Response/samlp:Status/samlp:StatusMessage', status_entry[0])
        if len(message_entry) == 0:
            subcode_entry = OneLogin_Saml2_XML.query(dom, '/samlp:Response/samlp:Status/samlp:StatusCode/samlp:StatusCode', status_entry[0])
            if len(subcode_entry) > 0:
                status['msg'] = subcode_entry[0].values()[0]
            else:
                status['msg'] = ''
        else:
            status['msg'] = message_entry[0].text

        return status

    @staticmethod
    def decrypt_element(encrypted_data, key, debug=False):
        """
        Decrypts an encrypted element.

        :param encrypted_data: The encrypted data.
        :type: lxml.etree.Element | DOMElement | basestring

        :param key: The key.
        :type: string

        :param debug: Activate the xmlsec debug
        :type: bool

        :returns: The decrypted element.
        :rtype: lxml.etree.Element
        """
        encrypted_data = OneLogin_Saml2_XML.to_etree(encrypted_data)
        xmlsec.enable_debug_trace(debug)
        manager = xmlsec.KeysManager()

        manager.add_key(xmlsec.Key.from_memory(key, xmlsec.KeyFormat.PEM, None))
        enc_ctx = xmlsec.EncryptionContext(manager)
        return enc_ctx.decrypt(encrypted_data)

    @staticmethod
    def add_sign(xml, key, cert, debug=False):
        """
        Adds signature key and senders certificate to an element (Message or
        Assertion).

        :param xml: The element we should sign
        :type: string | Document

        :param key: The private key
        :type: string

        :param debug: Activate the xmlsec debug
        :type: bool

        :param cert: The public
        :type: string
        """
        if xml is None or xml == '':
            raise Exception('Empty string supplied as input')

        elem = OneLogin_Saml2_XML.to_etree(xml)
        xmlsec.enable_debug_trace(debug)
        xmlsec.tree.add_ids(elem, ["ID"])
        # Sign the metadacta with our private key.
        signature = xmlsec.template.create(elem, xmlsec.Transform.EXCL_C14N, xmlsec.Transform.RSA_SHA1, ns='ds')

        issuer = OneLogin_Saml2_XML.query(elem, '//saml:Issuer')
        if len(issuer) > 0:
            issuer = issuer[0]
            issuer.addnext(signature)
        else:
            elem[0].insert(0, signature)

        elem_id = elem.get('ID', None)
        if elem_id:
            elem_id = '#' + elem_id

        ref = xmlsec.template.add_reference(signature, xmlsec.Transform.SHA1, uri=elem_id)
        xmlsec.template.add_transform(ref, xmlsec.Transform.ENVELOPED)
        xmlsec.template.add_transform(ref, xmlsec.Transform.EXCL_C14N)
        key_info = xmlsec.template.ensure_key_info(signature)
        xmlsec.template.add_x509_data(key_info)

        dsig_ctx = xmlsec.SignatureContext()
        sign_key = xmlsec.Key.from_memory(key, xmlsec.KeyFormat.PEM, None)
        sign_key.load_cert_from_memory(cert, xmlsec.KeyFormat.PEM)

        dsig_ctx.key = sign_key
        dsig_ctx.sign(signature)

        return OneLogin_Saml2_XML.to_string(elem)

    @staticmethod
    def validate_sign(xml, cert=None, fingerprint=None, validatecert=False, debug=False):
        """
        Validates a signature (Message or Assertion).

        :param xml: The element we should validate
        :type: string | Document

        :param cert: The pubic cert
        :type: string

        :param fingerprint: The fingerprint of the public cert
        :type: string

        :param validatecert: If true, will verify the signature and if the cert is valid.
        :type: bool

        :param debug: Activate the xmlsec debug
        :type: bool
        """
        try:
            if xml is None or xml == '':
                raise Exception('Empty string supplied as input')

            elem = OneLogin_Saml2_XML.to_etree(xml)
            xmlsec.enable_debug_trace(debug)
            xmlsec.tree.add_ids(elem, ["ID"])

            signature_nodes = OneLogin_Saml2_XML.query(elem, '//ds:Signature')

            if len(signature_nodes) > 0:
                signature_node = signature_nodes[0]

                if (cert is None or cert == '') and fingerprint:
                    x509_certificate_nodes = OneLogin_Saml2_XML.query(signature_node, '//ds:Signature/ds:KeyInfo/ds:X509Data/ds:X509Certificate')
                    if len(x509_certificate_nodes) > 0:
                        x509_certificate_node = x509_certificate_nodes[0]
                        x509_cert_value = x509_certificate_node.text
                        x509_fingerprint_value = OneLogin_Saml2_Utils.calculate_x509_fingerprint(x509_cert_value)
                        if fingerprint == x509_fingerprint_value:
                            cert = OneLogin_Saml2_Utils.format_cert(x509_cert_value)

                if cert is None or cert == '':
                    return False

                if validatecert:
                    manager = xmlsec.KeysManager()
                    manager.load_cert_from_memory(cert, xmlsec.KeyFormat.CERT_PEM, xmlsec.KeyDataType.TRUSTED)
                    dsig_ctx = xmlsec.SignatureContext(manager)
                else:
                    dsig_ctx = xmlsec.SignatureContext()
                    dsig_ctx.key = xmlsec.Key.from_memory(cert, xmlsec.KeyFormat.CERT_PEM, None)

                dsig_ctx.set_enabled_key_data([xmlsec.KeyData.X509])
                dsig_ctx.verify(signature_node)
                return True
            else:
                return False
        except xmlsec.Error as e:
            if debug:
                print(e)

            return False

    @staticmethod
    def sign_binary(msg, key, algorithm=xmlsec.Transform.RSA_SHA1, debug=False):
        """
        Sign binary message

        :param msg: The element we should validate
        :type: bytes

        :param key: The private key
        :type: string

        :param debug: Activate the xmlsec debug
        :type: bool

        :return signed message
        :rtype str
        """

        if isinstance(msg, str):
            msg = msg.encode('utf8')

        xmlsec.enable_debug_trace(debug)
        dsig_ctx = xmlsec.SignatureContext()
        dsig_ctx.key = xmlsec.Key.from_memory(key, xmlsec.KeyFormat.PEM, None)
        return dsig_ctx.sign_binary(compat.to_bytes(msg), algorithm)

    @staticmethod
    def validate_binary_sign(signed_query, signature, cert=None, algorithm=xmlsec.Transform.RSA_SHA1, debug=False):
        """
        Validates signed bynary data (Used to validate GET Signature).

        :param signed_query: The element we should validate
        :type: string


        :param signature: The signature that will be validate
        :type: string

        :param cert: The pubic cert
        :type: string

        :param algorithm: Signature algorithm
        :type: string

        :param debug: Activate the xmlsec debug
        :type: bool
        """
        try:
            xmlsec.enable_debug_trace(debug)
            dsig_ctx = xmlsec.SignatureContext()
            dsig_ctx.key = xmlsec.Key.from_memory(cert, xmlsec.KeyFormat.CERT_PEM, None)
            dsig_ctx.verify_binary(compat.to_bytes(signed_query),
                                   algorithm,
                                   compat.to_bytes(signature))
            return True
        except xmlsec.Error as e:
            if debug:
                print(e)
            return False
