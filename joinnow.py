#!/usr/bin/python

import os
import re
import sys
import dbus
import uuid
import urllib2
import httplib
import getpass
import subprocess
import xml.etree.ElementTree as ET
from time import sleep
from StringIO import StringIO
from subprocess import Popen, PIPE, STDOUT
from textwrap import wrap
from hashlib import sha1
from base64 import b64decode
from locale import getdefaultlocale


VERSION = '112'
NAME    = 'JoinNow for Linux'

SW2_PALADIN_REPORT_HANDLER_CLOUD = 0

SW2_PALADIN_WLAN_CONNECTION_TIMEOUT = 20    # Increased since NetworkManager/dhcpcd can be a bit slow

BUILDIN_STRINGS = {

    6:  'Please enter your credentials',
    7:  'Enter your Username:',
    8:  'Enter your Password:',
    9:  'false',
    10: 'Re-Enter your Password:',
    11: 'Enter your domain:',
    12: 'true',
    23: 'Passwords do not match',
    24: 'The username is not correctly formatted for this network.',
    65: 'Connecting...',
    67: 'Joined...',
    103: 'Configuration succeeded. Configured Network is however not in range.\r\n\r\nClick on the wireless tray icon to validate if your network is available. If you are seeing intermittent issues or low signal strength please move your device to re-establish a better connection and retry.',
    104: 'Configuration succeeded. Configured Network is however not in range.\r\n\r\nClick on the wireless tray icon to validate if your network is available. If you are seeing intermittent issues or low signal strength please move your device to re-establish a better connection and retry.'
}

class PaladinCloudReporter(object):

    OPTIONS = ['enable', 'useSSL', 'server', 'port', 'service', 'reportUserIdentity', 'reportIP']
    ORGANIZATION_DATA = ['name', 'UID']

    REQUEST_TYPE_REPORT = 4
    REQUEST_TYPE_CONFIGURATION = 7

    ERROR_CONNECTION_TIMED_OUT = 5
    ERROR_CONNECTION_FAILED_OTHER = 13

    def __init__(self, config, devicecfg, organization=None):

        self.adapters = []
        self.deviceid = None
        self.devicedata = {}
        self.devicecfgdata = {'id': 0}
        self.identity = None
        self.ipaddress = None

        self.devicecfgdata['id'] = devicecfg.get('id')

        try:
            self.devicecfgdata['name'] = devicecfg.find('name').text
        except AttributeError:
            pass

        self.organizationdata = dict((k, d.text) for k, d in filter(lambda e: e[1] != None, [(k, organization.find(k)) for k in self.ORGANIZATION_DATA])) if organization != None else {}

        try:
            self.config = dict((k, config.find(k).text) for k in self.OPTIONS)
        except AttributeError:
            print 'No or invalid cloud reporting configuration'
            self.config = {'enable': 'false'}

        self.enabled = self.config['enable'] == 'true'
        self.senddeviceinfo = True

    def collect_from_uname(self, key, uname_opt):
        try:
            p = Popen('uname -' + uname_opt, stdout=PIPE, shell=True)
            self.devicedata[key] = p.communicate()[0].split('\n')[0]
        except:
            pass

    def gendeviceid(self):
        # Try to obtain unprivileged system specific data:
        try:
            f = open('/sys/class/dmi/id/modalias', 'r')
            hashdata = f.read().replace('\n', '')
            f.close()
        except:
            hashdata = ''

        for k in self.devicedata:
            hashdata += str(self.devicedata[k])

        for a in self.adapters:
            for v in a:
                hashdata += str(v)

        if not len(self.adapters):
            hashdata += os.urandom(8)

        h = sha1()
        h.update(hashdata)
        self.deviceid = h.hexdigest()

    def collect_attributes(self):
        self.collect_from_uname('buildModel', 'o')
        self.collect_from_uname('buildVersion', 'r')
        self.collect_from_uname('OSArchitecture', 'm')

        try:
            self.devicedata['OSArchitecture'] = '32-bit' if not '64' in self.devicedata['OSArchitecture'] else '64-bit'
        except KeyError:
            pass

        try:
            nm = NetworkManagerProxy()
            for device in nm.get_wireless_devices():
                try:
                    self.adapters += [(nm.dev_get_name(device), nm.dev_get_macaddress(device))]
                except:
                    pass
        except:
            pass

        self.gendeviceid()

    def set_identity(self, identity):
        self.identity = identity

    def set_ipaddress(self, ipaddress):
        self.ipaddress = ipaddress

    def create_xml(self, reporttype, deviceinfo=True, deviceconfig=True, error=(0, None), ipaddress=None, identity=None):
        xml = ET.Element('paladinRequest')
        xml.set('xmlns', 'http://schemas.securew2.com/paladinRequest')
        xml.set('type', str(reporttype))

        organization = ET.SubElement(xml, 'organization')
        for k in self.organizationdata:
            e = ET.SubElement(organization, k)
            e.text = self.organizationdata[k]

        device = ET.SubElement(xml, 'device')

        if self.deviceid:
            device.set('id', self.deviceid)

        if deviceinfo:
            devicedata = {'applicationVersionName': NAME, 'applicationVersionCode': VERSION}
            for k in self.devicedata: devicedata[k] = self.devicedata[k]

            for k in devicedata:
                e = ET.SubElement(device, k)
                e.text = devicedata[k]

            adapters = ET.SubElement(device, 'adapters')

            for a in self.adapters:
                adapter = ET.SubElement(adapters, 'adapter')
                e = ET.SubElement(adapter, 'description')
                e.text = a[0]
                e = ET.SubElement(adapter, 'MACAddress')
                e.text = a[1]

        if deviceconfig:
            devicecfgdata = {'errorCode': str(error[0])}
            for k in self.devicecfgdata: devicecfgdata[k] = self.devicecfgdata[k]

            if error[1]:
                devicecfgdata['errorMessage'] = error[1]

            if ipaddress and self.config['reportIP'] == 'true':
                devicecfgdata['IPAddress'] = ipaddress

            devicecfg = ET.SubElement(xml, 'deviceConfiguration')
            for k in devicecfgdata:
                e = ET.SubElement(devicecfg, k)
                e.text = devicecfgdata[k]

            if identity and self.config['reportUserIdentity'] == 'true':
                user = ET.SubElement(devicecfg, 'user')
                userid = ET.SubElement(user, 'identity')
                userid.text = identity

        return ET.tostring(xml)

    def connect(self):
        connclass = httplib.HTTPSConnection if self.config['useSSL'] == 'true' else httplib.HTTPConnection
        return connclass(self.config['server'], int(self.config['port']))

    def send_report(self, data):
        try:
            conn = self.connect()
            conn.request('POST', '/' + self.config['service'], data, {'Content-Type:': 'application/xml'})
            return conn.getresponse().status
        except:
            return None

    def report(self):
        if not self.enabled:
            return None

        if not self.deviceid:
            self.collect_attributes()

        xml = self.create_xml(self.REQUEST_TYPE_REPORT, deviceconfig=False)
        result = self.send_report(xml)

        if result and int(result) == 200:
            self.senddeviceinfo = False

        return result

    def sendconfiguration(self, errorcode, errormsg=None, ipaddress=None, identity=None):
        if not self.enabled:
            return None

        if not identity and self.identity:
            identity = self.identity

        if not ipaddress and self.ipaddress:
            ipaddress = self.ipaddress

        xml = self.create_xml(self.REQUEST_TYPE_CONFIGURATION, deviceinfo=self.senddeviceinfo, error=(errorcode, errormsg), ipaddress=ipaddress, identity=identity)
        return self.send_report(xml)

class ActionFactory(object):
    SW2_PALADIN_ACTION_TYPE_NONE                    = 0
    SW2_PALADIN_ACTION_TYPE_REPORT                  = 1
    SW2_PALADIN_ACTION_TYPE_LOCKSCREEN              = 2
    SW2_PALADIN_ACTION_TYPE_SETNEWPASSWORD          = 3
    SW2_PALADIN_ACTION_TYPE_ENABLEWLAN              = 4
    SW2_PALADIN_ACTION_TYPE_ADDWLAN                 = 5
    SW2_PALADIN_ACTION_TYPE_BACKUP                  = 6
    SW2_PALADIN_ACTION_TYPE_RESTORE                 = 7
    SW2_PALADIN_ACTION_TYPE_ADDCERTIFICATE          = 8
    SW2_PALADIN_ACTION_TYPE_CAMERA                  = 9
    SW2_PALADIN_ACTION_TYPE_WIPEDATA                = 10
    SW2_PALADIN_ACTION_TYPE_INSTALLSOFTWARE         = 11
    SW2_PALADIN_ACTION_TYPE_CONNECT                 = 12
    SW2_PALADIN_ACTION_TYPE_SETPROXYCONFIGURATION   = 13
    SW2_PALADIN_ACTION_TYPE_DISABLEWIRELESSONWIRED  = 14
    SW2_PALADIN_ACTION_TYPE_REBOOT                  = 15
    SW2_PALADIN_ACTION_TYPE_REMOVESSID              = 16
    SW2_PALADIN_ACTION_TYPE_GROUPACTION             = 17
    SW2_PALADIN_ACTION_TYPE_COPYFILE                = 18
    SW2_PALADIN_ACTION_TYPE_RUNCOMMAND              = 19
    SW2_PALADIN_ACTION_TYPE_REMOVESECUREW2          = 20
    SW2_PALADIN_ACTION_TYPE_SYSCHECK                = 21
    SW2_PALADIN_ACTION_TYPE_NAC                     = 22
    SW2_PALADIN_ACTION_TYPE_CREDENTIALS             = 23
    SW2_PALADIN_ACTION_TYPE_ENABLELAN               = 24
    SW2_PALADIN_ACTION_TYPE_ADDLAN                  = 25
    SW2_PALADIN_ACTION_TYPE_CUSTOMXML               = 26
    SW2_PALADIN_ACTION_TYPE_ENROLL                  = 27
    SW2_PALADIN_ACTION_TYPE__LAST_                  = 28

    ActionMap = [ None ] * SW2_PALADIN_ACTION_TYPE__LAST_

    def __init__(self, parent):
        self.parent = parent
        self.register(ReportAction)
        self.register(AddCertificateAction)
        self.register(CredentialAction)
        self.register(AddWLANAction)
        self.register(ConnectAction)
        self.ActionMap = [ am if am != None else NoneAction for am in self.ActionMap ]

    def create(self, actionconfig):
        type = int(actionconfig.get('type', 0))
        return self.ActionMap[type](self.parent, actionconfig)

    @classmethod
    def register(cls, actioncls):
        actioncls.register(cls.ActionMap)

class NoneAction(object):
    ID = ActionFactory.SW2_PALADIN_ACTION_TYPE_NONE

    def __init__(self, parent, config=None):
        self.parent = parent
        self.strings = parent.load_resources(config.findall('customization/resources/resource') if config != None else None, parent.strings)

    def run(self):
        pass

    def get_string(self, id):
        try:
            message = self.strings[id]
        except KeyError:
            try:
                message = BUILDIN_STRINGS[id]
            except KeyError:
                message = ''
        return message

    @classmethod
    def register(cls, action_map):
        action_map[cls.ID] = cls

class ReportAction(NoneAction):
    ID = ActionFactory.SW2_PALADIN_ACTION_TYPE_REPORT

    def __init__(self, parent, config):
        super(ReportAction, self).__init__(parent, config)

    def run(self):
        self.parent.reporter.report()

class AddCertificateAction(NoneAction):
    ID = ActionFactory.SW2_PALADIN_ACTION_TYPE_ADDCERTIFICATE
    directory = '{0}/.joinnow'.format(os.environ.get('HOME', ''))

    def __init__(self, parent, config):
        super(AddCertificateAction, self).__init__(parent, config)
        self.alias = config.find('certificate/alias').text
        self.data = config.find('certificate/data').text

    def run(self):
        if self.directory and not os.path.exists(self.directory):
            os.makedirs(self.directory)
        open(self.get_filename(self.alias), 'w').write(
            '-----BEGIN CERTIFICATE-----\n{0}\n-----END CERTIFICATE-----'.format(
                '\n'.join(wrap(self.data, width=64))))

    @classmethod
    def get_filename(cls, alias):
        return os.path.join(cls.directory, '{0}.pem'.format(alias))

class CredentialAction(NoneAction):
    SW2_PALADIN_CREDENTIALS_TYPE_USERNAMEPASSWORD               = 0
    SW2_PALADIN_CREDENTIALS_TYPE_USERNAMEPASSWORD_TLSENROLLMENT = 1
    SW2_PALADIN_CREDENTIALS_TYPE_WEBSSO_TLSENROLLMENT           = 2
    SW2_PALADIN_CREDENTIALS_TYPE_SHAREDSECRET                   = 3

    ID = ActionFactory.SW2_PALADIN_ACTION_TYPE_CREDENTIALS

    Credentials = []

    def __init__(self, parent, config):
        super(CredentialAction, self).__init__(parent, config)
        self.Credentials += [ self ]
        self.identity = ''
        self.password = ''
        self.default_domain = None
        credentials = config.find('credentials')
        self.type = int(credentials.get('type', self.SW2_PALADIN_CREDENTIALS_TYPE_USERNAMEPASSWORD))
        self.uuid = credentials.find('UUID').text
        try:
            self.prompt = True if credentials.find('prompt').text == 'true' else False
        except AttributeError:
            self.prompt = True
        try:
            self.default_domain = credentials.find('userDomain').text
        except AttributeError:
            pass
        try:
            self.identity_format = b64decode(credentials.find('identityFormat/pattern').text)
        except (AttributeError, TypeError):
            self.identity_format = '^.*$'
        self.regex = re.compile(self.identity_format)
        if self.type == self.SW2_PALADIN_CREDENTIALS_TYPE_SHAREDSECRET:
            try:
                self.password = credentials.find('PSK').text
            except AttributeError:
                pass

    def get_credentials(self):
        print '\n' + self.get_string(6) + '\n'
        self.identity = raw_input(self.get_string(7) + ' ')
        if self.regex and not self.regex.match(self.identity):
            print self.get_string(24)
            return self.get_credentials()
        password = getpass.getpass(self.get_string(8) + ' ')
        if self.get_string(9) != 'true':
            repassword = getpass.getpass(self.get_string(10) + ' ')
            if password != repassword:
                print '\n' + self.get_string(23) + '\n'
                return self.get_credentials()
        self.password = password
        if not '@' in self.identity:
            if self.get_string(12) != 'true':
                domain = raw_input(self.get_string(11) + ' ')
                self.identity += '@' + domain
            elif self.default_domain:
                self.identity += '@' + self.default_domain

    def get_psk(self):
        print '\n' + self.get_string(6)
        self.password = raw_input('> ')

    def run(self):
        if not self.prompt:
            return
        if self.type == self.SW2_PALADIN_CREDENTIALS_TYPE_USERNAMEPASSWORD:
            self.get_credentials()
        elif self.type == self.SW2_PALADIN_CREDENTIALS_TYPE_SHAREDSECRET:
            self.get_psk()

    @classmethod
    def get(cls, uuid):
        try:
            return filter(lambda creds: creds.uuid == uuid, cls.Credentials)[0]
        except IndexError:
            return None

class AddWLANAction(NoneAction):
    ID = ActionFactory.SW2_PALADIN_ACTION_TYPE_ADDWLAN

    SW2_PALADIN_WLANPROFILE_TYPE_PERSONAL           = 0
    SW2_PALADIN_WLANPROFILE_TYPE_ENTERPRISE         = 1

    SW2_PALADIN_SSID_CONNECTIONTYPE_ESS             = 0
    SW2_PALADIN_SSID_CONNECTIONTYPE_IBSS            = 1

    SW2_PALADIN_WLANPROFILE_SCOPE_PERUSER           = 0
    SW2_PALADIN_WLANPROFILE_SCOPE_SYSTEM            = 1

    SW2_PALADIN_SSID_CONNECTIONMODE_AUTO            = 0
    SW2_PALADIN_SSID_CONNECTIONMODE_MANUAL          = 1

    SW2_PALADIN_SSID_SECURITYTYPE_WPA2Enterprise    = 0
    SW2_PALADIN_SSID_SECURITYTYPE_WPAEnterprise     = 1
    SW2_PALADIN_SSID_SECURITYTYPE_WPA2Personal      = 2
    SW2_PALADIN_SSID_SECURITYTYPE_WPAPersonal       = 3
    SW2_PALADIN_SSID_SECURITYTYPE_8021X             = 4
    SW2_PALADIN_SSID_SECURITYTYPE_CCKM              = 5
    SW2_PALADIN_SSID_SECURITYTYPE_Open              = 6
    SW2_PALADIN_SSID_SECURITYTYPE_Shared            = 7

    SW2_PALADIN_SSID_ENCRYPTIONTYPE_AES             = 0
    SW2_PALADIN_SSID_ENCRYPTIONTYPE_TKIP            = 1
    SW2_PALADIN_SSID_ENCRYPTIONTYPE_WEP             = 2
    SW2_PALADIN_SSID_ENCRYPTIONTYPE_NONE            = 3

    class SSID(object):
        SSIDs = []

        def __init__(self, parent, ssidconfig):
            self.SSIDs += [ self ]
            try:
                self.priority = ssidconfig.find('priority').text
            except AttributeError():
                self.priority = None
            self.name = ssidconfig.find('SSIDConfig/name').text
            self.broadcast = True if ssidconfig.find('SSIDConfig/nonBroadcast').text != 'true' else False
            self.conntype = int(ssidconfig.find('connection/connectionType').text)
            self.autoconnect = True if int(ssidconfig.find('connection/connectionMode').text) == AddWLANAction.SW2_PALADIN_SSID_CONNECTIONMODE_AUTO else False
            self.security = int(ssidconfig.find('security/securityType').text)
            self.encryption = int(ssidconfig.find('security/encryptionType').text)
            self.networksetting = parent
            self.uuid = None

        @classmethod
        def find(cls, name):
            try:
                return filter(lambda ssid: ssid.name == name, cls.SSIDs)[0]
            except IndexError:
                return None


    def __init__(self, parent, config):
        super(AddWLANAction, self).__init__(parent, config)

        profile = config.find('WLANProfile')
        try:
            self.credentials_uuid = profile.find('credentialsUUID').text
        except AttributeError():
            self.credentials_uuid = None

        self.type = int(profile.get('type', self.SW2_PALADIN_WLANPROFILE_TYPE_ENTERPRISE))
        self.profilename = profile.find('name').text
        try:
            self.scope = int(profile.find('scope').text)
        except (AttributeError, ValueError):
            self.scope = self.SW2_PALADIN_WLANPROFILE_SCOPE_PERUSER
        self.ssids = [ self.SSID(self, ssid) for ssid in profile.findall('SSIDs/SSID') ]

        if self.type == self.SW2_PALADIN_WLANPROFILE_TYPE_ENTERPRISE:
            eapconfig = profile.find('EAP')
            self.method = eapconfig.find('eapMethod').text
            # Mandatory as we do not support TLS
            self.method_phase2 = eapconfig.find('eapPhase2').text
            try:
                self.anonid = eapconfig.find('anonymousIdentity').text
                if len(self.anonid) == 0:
                    self.anonid = None
            except AttributeError:
                self.anonid = None
            self.server_validation = True if eapconfig.find('enableServerValidation').text == 'true' else False
            self.cacerts = [ cert.text for cert in eapconfig.findall('CACertificates/certificate/alias') ]

    def run(self):
        nm = NetworkManagerProxy()
        for ssid in self.ssids:
            nm.delete_existing_connections(ssid.name)
            if ssid.networksetting.type == ssid.networksetting.SW2_PALADIN_WLANPROFILE_TYPE_ENTERPRISE:
                ssid.uuid = nm.add_eap_connection(ssid)
            elif ssid.networksetting.type == ssid.networksetting.SW2_PALADIN_WLANPROFILE_TYPE_PERSONAL:
                ssid.uuid = nm.add_psk_connection(ssid)

    def get_certificate_uri(self, default=None):
        if not self.type == self.SW2_PALADIN_WLANPROFILE_TYPE_ENTERPRISE:
            return default
        if not len(self.cacerts) > 0:
            return default
        return 'file://' + AddCertificateAction.get_filename(self.cacerts[0])

    def get_credentials(self):
        return CredentialAction.get(self.credentials_uuid)

class ConnectAction(NoneAction):
    ID = ActionFactory.SW2_PALADIN_ACTION_TYPE_CONNECT

    def __init__(self, parent, config):
        super(ConnectAction, self).__init__(parent, config)

    def run(self):
        print '\n' + self.get_string(65)
        ssid, ip = NetworkManagerProxy().connect()
        self.parent.reporter.set_ipaddress(ip)

        if ssid:
            connected_profile = AddWLANAction.SSID.find(ssid)

            if connected_profile:
                code = 0
                self.parent.set_success()
                report_message = 'Connection to "%s" succeeded' % ssid

                #
                # If we are connected to a network, use appropriate identity instead of last configured one
                #
                try:
                    self.parent.reporter.set_identity(connected_profile.networksetting.get_credentials().identity)
                except AttributeError:
                    pass
            else:
                code = PaladinCloudReporter.ERROR_CONNECTION_FAILED_OTHER
                report_message = 'Connection failed'
                self.parent.set_error(self.get_string(103))
        else:
            code = PaladinCloudReporter.ERROR_CONNECTION_TIMED_OUT
            report_message = 'Connection timed out'
            self.parent.set_error(self.get_string(104))

        self.parent.reporter.sendconfiguration(code, report_message)

class PaladinLinuxClient(object):
    """SecureW2 JoinNow Linux Client Implementation"""

    CONFIG_FILE_URL = 'https://cloud.securew2.com/public/28503/Columbia_U_Secure_-_With_Cached_Credentials/linux/SecureW2.cloudconfig' # configuration file URL should be placed within the single quotes
    currentAction   = -1
    devicecfg       = None
    organization    = None
    actions         = []
    locales         = []

    def __init__(self):
        signed_config_file = self.download_config()
        config_file = self.decipher(signed_config_file)
        config_file = self.strip_namespace(config_file)
        self.load_config(config_file)

    @staticmethod
    def decipher(config_file):
        p = Popen('openssl smime -verify -inform der -noverify', stdin=PIPE, stdout=PIPE, shell=True)
        config_data = p.communicate(input=config_file.read())[0]
        return StringIO(config_data)

    @staticmethod
    def strip_namespace(fp):
        """Removes xmlns attribute from XML file to avoid having to prefix all nodes"""
        contents = fp.read()
        contents = re.sub('xmlns="[^"]+"', '', contents)
        return StringIO(contents)

    @staticmethod
    def get_action_nodes(root, action_type):
        path = "configurations/deviceConfiguration/actions/action"
        nodes = [n if int(n.get('type', '0')) == action_type else None for n in root.findall(path)]
        return filter(lambda n: n != None, nodes)

    def download_config(self):
        open_url = urllib2.urlopen(self.CONFIG_FILE_URL)
        return StringIO(open_url.read())

    def load_resources(self, resources, basedata={}):
        strings = basedata.copy()
        if not resources:
            return strings
        for locale in self.locales:
            for res in resources:
                use = False
                for res_locale in res.findall('locales/locale'):
                    if res_locale.text == locale:
                        use = True
                        break
                if not use:
                    continue
                for string in res.findall('strings/string'):
                    strings[int(string.find('id').text)] = string.find('text').text
                break
        return strings

    def load_config(self, xml_file):
        """Parses the XML config file"""
        root = ET.parse(xml_file)

        #
        # Find organization node
        #
        self.organization = (root.findall('organization') + [ None ])[0]

        #
        # Find (first) deviceconfig node
        #
        self.devicecfg = root.find('configurations/deviceConfiguration')

        #
        # Read reporting config and initialize reporter
        #
        try:
            reporting = filter(lambda n: int(n.get('type', '0')) == SW2_PALADIN_REPORT_HANDLER_CLOUD, self.devicecfg.findall('reporting/handlers/handler'))[0]
        except IndexError:
            reporting = None

        self.reporter = PaladinCloudReporter(reporting, self.devicecfg, self.organization)

        #
        # Import language resources
        #
        locale = getdefaultlocale()[0]
        if locale:
            if len(locale.split('_')) > 1:
                self.locales += [ locale.split('_')[0] ]
            self.locales += [ locale ]

        if not 'en' in self.locales:
            self.locales = [ 'en' ] + self.locales

        self.strings = self.load_resources(self.devicecfg.findall('customization/resources/resource'))

        #
        # Create actions
        #
        factory = ActionFactory(self)
        self.actions = [ factory.create(a) for a in self.devicecfg.findall('actions/action') ]

    def set_success(self, message=None):
        self.success = True
        self.message = message if message else NoneAction(self).get_string(67)

    def set_error(self, message):
        self.succeess = False
        self.message = message

    def run(self):
        self.success = False
        self.message = None

        for action in self.actions:
            action.run()

        if self.success:
            self.reporter.sendconfiguration(0, 'Configuration succeeded')

        if self.message:
            print self.message

class NetworkManagerProxy(object):
    def __init__(self):
        self.NM_NAME = 'org.freedesktop.NetworkManager'
        self.NM_PATH = '/org/freedesktop/NetworkManager'
        self.NM_SETTINGS_NAME = 'org.freedesktop.NetworkManager.Settings'
        self.NM_SETTINGS_PATH = '/org/freedesktop/NetworkManager/Settings'
        self.NM_SETTINGS_CONN_NAME = 'org.freedesktop.NetworkManager.Settings.Connection'
        self.NM_ACTIVE_CONN_NAME = "org.freedesktop.NetworkManager.Connection.Active"
        self.NM_DEVICE_NAME = 'org.freedesktop.NetworkManager.Device'
        self.NM_WLAN_DEVICE_NAME = 'org.freedesktop.NetworkManager.Device.Wireless'
        self.NM_ACCESS_POINT_NAME = 'org.freedesktop.NetworkManager.AccessPoint'
        self.NM_DEVICE_TYPE_WIFI = 2
        self.DBUS_PROPERTIES_NAME = 'org.freedesktop.DBus.Properties'

        self.configure()

    def configure(self):
        self.system_bus = dbus.SystemBus()

        settings_proxy = self.system_bus.get_object(self.NM_NAME, self.NM_SETTINGS_PATH)
        self.nm_settings_iface = dbus.Interface(settings_proxy, dbus_interface=self.NM_SETTINGS_NAME)

    def get_version(self):
        nm_proxy = self.system_bus.get_object(self.NM_NAME, self.NM_PATH)
        nm_props_iface = dbus.Interface(nm_proxy, dbus_interface=dbus.PROPERTIES_IFACE)
        return nm_props_iface.Get(self.NM_NAME, 'Version')

    def get_wlan_settings(self, ssid):
        conn_settings = {
            'type': '802-11-wireless',
            'uuid': str(uuid.uuid4()),
            'id': ssid.name,
            'autoconnect': ssid.autoconnect
        }
        ssid_settings = {
            'ssid': dbus.ByteArray(ssid.name),
            'security': '802-11-wireless-security',
            'mode': [ 'infrastructure', 'adhoc' ][ssid.conntype]
        }

        if ssid.priority != None:
            ssid_settings['priority'] = ssid.priority

        security_settings = {}

        if   ssid.security == ssid.networksetting.SW2_PALADIN_SSID_SECURITYTYPE_WPA2Enterprise or \
             ssid.security == ssid.networksetting.SW2_PALADIN_SSID_SECURITYTYPE_WPAEnterprise:
            security_settings['key-mgmt'] = 'wpa-eap'
        elif ssid.security == ssid.networksetting.SW2_PALADIN_SSID_SECURITYTYPE_WPA2Personal or \
             ssid.security == ssid.networksetting.SW2_PALADIN_SSID_SECURITYTYPE_WPAPersonal:
            security_settings['key-mgmt'] = [ 'wpa-psk', 'wpa-none' ][ssid.conntype]
            security_settings['psk'] = ssid.networksetting.get_credentials().password
        elif ssid.security == ssid.networksetting.SW2_PALADIN_SSID_SECURITYTYPE_8021X:
            security_settings['key-mgmt'] = 'ieee8021x'
        else:
            security_settings['key-mgmt'] = 'none'

        security_settings['auth-alg'] = 'open'

        return dbus.Dictionary(conn_settings), dbus.Dictionary(ssid_settings), dbus.Dictionary(security_settings)

    def add_connection(self, s_con, s_wifi, s_wsec, s_8021x=None):
        s_ip4 = dbus.Dictionary({'method': 'auto'})
        s_ip6 = dbus.Dictionary({'method': 'auto'})
        con = {
            'connection': s_con,
            '802-11-wireless': s_wifi,
            '802-11-wireless-security': s_wsec,
            'ipv4': s_ip4,
            'ipv6': s_ip6
        }

        if s_8021x != None:
            con['802-1x'] = s_8021x

        setting = self.nm_settings_iface.AddConnection(dbus.Dictionary(con))
        return self.get_uuid(setting)

    def add_psk_connection(self, ssid):
        s_con, s_wifi, s_wsec = self.get_wlan_settings(ssid)
        return self.add_connection(s_con, s_wifi, s_wsec)

    def add_eap_connection(self, ssid):
        s_con, s_wifi, s_wsec = self.get_wlan_settings(ssid)

        eap_settings = {
            'eap': [ssid.networksetting.method.lower()], # peap, ttls,
            'identity': ssid.networksetting.get_credentials().identity,
            'password': ssid.networksetting.get_credentials().password,
            'password-flags': 1L,
            'phase2-auth': ssid.networksetting.method_phase2.lower(), # gtc, pap
        }

        if ssid.networksetting.server_validation:
            cert_uri = ssid.networksetting.get_certificate_uri()
            if cert_uri:
                eap_settings['system-ca-certs'] = False
                eap_settings['ca-cert'] = dbus.ByteArray(cert_uri + "\0")
            else:
                eap_settings['system-ca-certs'] = True

        if ssid.networksetting.anonid:
            eap_settings['anonymous-identity'] = ssid.networksetting.anonid

        return self.add_connection(s_con, s_wifi, s_wsec, dbus.Dictionary(eap_settings))

    def delete_existing_connections(self, ssid):
        """Checks and deletes existing *wireless* connections with the same @ssid"""
        conns = self.nm_settings_iface.ListConnections()

        for conn in conns:
            con_proxy = self.system_bus.get_object(self.NM_NAME, conn)
            connection = dbus.Interface(con_proxy, self.NM_SETTINGS_CONN_NAME)
            connection_settings = connection.GetSettings()

            if connection_settings['connection']['type'] == '802-11-wireless':  # make sure it's *wireless*
                conn_ssid = ''.join(chr(c) for c in (connection_settings['802-11-wireless']['ssid']))
                if conn_ssid.lower() == ssid.lower():
                    connection.Delete()

    def is_wireless(self, conn):
        """Checks if the given connection is a wireless connection"""
        con_proxy = self.system_bus.get_object(self.NM_NAME, conn)
        connection = dbus.Interface(con_proxy, dbus_interface=dbus.PROPERTIES_IFACE)
        connection = connection.Get(self.NM_ACTIVE_CONN_NAME, 'Connection')

        con_proxy = self.system_bus.get_object(self.NM_NAME, connection)
        connection = dbus.Interface(con_proxy, self.NM_SETTINGS_CONN_NAME)
        connection_settings = connection.GetSettings()

        return connection_settings['connection']['type'] == '802-11-wireless'
    
    def get_uuid(self, conn):
        conn_proxy = self.system_bus.get_object(self.NM_NAME, conn)
        conn_iface = dbus.Interface(conn_proxy, dbus_interface=self.NM_SETTINGS_CONN_NAME)
        try:
            return conn_iface.GetSettings()['connection']['uuid']
        except (KeyError, dbus.DBusException):
            print 'Warning: failed to obtain connection UUID'
            return None
        
    def get_connection(self, uuid):
        try:
            return self.nm_settings_iface.GetConnectionByUuid(uuid)
        except dbus.DBusException:
            return None

    def dev_get_property(self, nm_device, obj, prop):
        nm_dev_proxy = self.system_bus.get_object(self.NM_NAME, nm_device)
        nm_dev_prop_iface = dbus.Interface(nm_dev_proxy, dbus_interface=self.DBUS_PROPERTIES_NAME)
        return nm_dev_prop_iface.Get(obj, prop)

    def dev_is_wlan(self, nm_device):
        return self.dev_get_property(nm_device, self.NM_DEVICE_NAME, 'DeviceType') == self.NM_DEVICE_TYPE_WIFI

    def dev_get_name(self, nm_device):
        return str(self.dev_get_property(nm_device, self.NM_DEVICE_NAME, 'Interface'))

    def dev_get_ip(self, nm_device):
        ip4addr = int(self.dev_get_property(nm_device, self.NM_DEVICE_NAME, 'Ip4Address'))
        return ('%d.%d.%d.%d' % (ip4addr / (2**0) & 0xff, ip4addr / (2**8) & 0xff, ip4addr / (2**16) & 0xff, ip4addr / (2**24) & 0xff)) if ip4addr else None

    def dev_get_macaddress(self, nm_device):
        return str(self.dev_get_property(nm_device, self.NM_WLAN_DEVICE_NAME, 'HwAddress'))

    def dev_get_ssid(self, nm_device):
        ap = self.dev_get_property(nm_device, self.NM_WLAN_DEVICE_NAME, 'ActiveAccessPoint')

        if str(ap) == '/':
            return None

        ap_proxy = self.system_bus.get_object(self.NM_NAME, ap)
        ap_iface = dbus.Interface(ap_proxy, dbus_interface=dbus.PROPERTIES_IFACE)
        return ''.join([chr(byte) for byte in ap_iface.Get(self.NM_ACCESS_POINT_NAME, 'Ssid')])

    def get_wireless_devices(self):
        nm_proxy = self.system_bus.get_object(self.NM_NAME, self.NM_PATH)
        nm_iface = dbus.Interface(nm_proxy, dbus_interface=self.NM_NAME)
        return filter(lambda dev: self.dev_is_wlan(dev), nm_iface.GetDevices())

    def connect(self):
        """Connects to one of the newly configured networks"""
        adapters = self.get_wireless_devices()
        if len(adapters) == 0:
            return None, None

        for _ in range(1, SW2_PALADIN_WLAN_CONNECTION_TIMEOUT):
            for adapter in adapters:
                current_ssid = self.dev_get_ssid(adapter)
                if current_ssid:
                    profile = AddWLANAction.SSID.find(current_ssid)
                    if not profile:
                        adapter_proxy = self.system_bus.get_object(self.NM_NAME, adapter)
                        adapter_iface = dbus.Interface(adapter_proxy, dbus_interface=self.NM_DEVICE_NAME)
                        adapter_iface.Disconnect()
                    else:
                        ip = self.dev_get_ip(adapter)
                        if ip:
                            return current_ssid, ip
                else:
                    adapter_proxy = self.system_bus.get_object(self.NM_NAME, adapter)
                    adapter_iface = dbus.Interface(adapter_proxy, dbus_interface=self.NM_WLAN_DEVICE_NAME)
                    aps = adapter_iface.GetAccessPoints()
                    for ap in aps:
                        ssid = ''.join([chr(c) for c in self.dev_get_property(ap, self.NM_ACCESS_POINT_NAME, 'Ssid')])
                        profile = AddWLANAction.SSID.find(ssid)
                        if profile and profile.uuid:
                            conn = self.get_connection(profile.uuid)
                            if conn:
                                nm_proxy = self.system_bus.get_object(self.NM_NAME, self.NM_PATH)
                                nm_iface = dbus.Interface(nm_proxy, dbus_interface=self.NM_NAME)
                                nm_iface.ActivateConnection(conn, adapter, "/")
                                break
            sleep(1)
        return None, None

if __name__ == '__main__':
    PaladinLinuxClient().run()

