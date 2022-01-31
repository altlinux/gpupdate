#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2020 BaseALT Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import gettext

def info_code(code):
    info_ids = dict()
    info_ids[1] = 'Got GPO list for username'
    info_ids[2] = 'Got GPO'
    info_ids[3] = 'Working with control'
    info_ids[4] = 'Working with systemd'
    info_ids[5] = 'Unable to work with systemd unit'
    info_ids[6] = 'Starting systemd unit'
    info_ids[7] = 'Firefox policy'
    info_ids[8] = 'Chromium policy'
    info_ids[9] = 'Set user property to'

    return info_ids.get(code, 'Unknown info code')

def error_code(code):
    error_ids = dict()
    error_ids[1] = 'Insufficient permissions to run gpupdate'
    error_ids[2] = 'gpupdate will not be started'
    error_ids[3] = 'Backend execution error'
    error_ids[4] = 'Error occurred while running frontend manager'
    error_ids[5] = 'Error running GPOA for computer'
    error_ids[6] = 'Error running GPOA for user'
    error_ids[7] = 'Unable to initialize Samba backend'
    error_ids[8] = 'Unable to initialize no-domain backend'
    error_ids[9] = 'Error running ADP'
    error_ids[10] = 'Unable to determine DC hostname'
    error_ids[11] = 'Error occured while running applier with user privileges'
    error_ids[12] = 'Unable to initialize backend'
    error_ids[13] = 'Not sufficient privileges to run machine appliers'
    error_ids[14] = 'Kerberos ticket check failed'
    error_ids[15] = 'Unable to retrieve domain name via CLDAP query'
    error_ids[16] = 'Error getting SID using wbinfo, will use SID from cache'
    error_ids[17] = 'Unable to get GPO list for user from AD DC'
    error_ids[18] = 'Error getting XDG_DESKTOP_DIR'
    error_ids[19] = 'Error occured while running user applier in administrator context'
    error_ids[20] = 'Error occured while running user applier in user context (with dropped privileges)'
    error_ids[21] = 'No reply from oddjobd GPOA runner via D-Bus for current user'
    error_ids[22] = 'No reply from oddjobd GPOA runner via D-Bus for computer'
    error_ids[23] = 'No reply from oddjobd GPOA runner via D-Bus for user'
    error_ids[24] = 'Error occured while running machine applier'
    error_ids[25] = 'Error occured while initializing user applier'
    error_ids[26] = 'Error merging machine GPT'
    error_ids[27] = 'Error merging user GPT'
    error_ids[28] = 'Error merging machine part of GPT'
    error_ids[29] = 'Error merging user part of GPT'
    error_ids[30] = 'Error occured while running dropped privileges process for user context appliers'
    error_ids[31] = 'Error connecting to DBus Session daemon'
    error_ids[32] = 'No reply from DBus Session'
    error_ids[33] = 'Error occured while running forked process with dropped privileges'
    error_ids[34] = 'Error running GPOA directly for computer'
    error_ids[35] = 'Error caching URI to file'
    error_ids[36] = 'Error getting cached file for URI'
    error_ids[37] = 'Error caching file URIs'
    error_ids[38] = 'Unable to cache specified URI'
    error_ids[39] = 'Unable to work with control'
    error_ids[40] = 'Control applier for machine will not be started'
    error_ids[41] = 'Error getting control'
    error_ids[42] = 'Is not in possible values for control'
    error_ids[43] = 'Unable to set'
    error_ids[44] = 'Unable to generate file'
    error_ids[45] = 'Failed applying unit'
    error_ids[46] = 'Unable to start systemd unit'
    error_ids[47] = 'Unable to cache specified URI for machine'
    error_ids[48] = 'Error recompiling global GSettings schemas'
    error_ids[49] = 'Error update configuration dconf'
    error_ids[50] = 'Unable to cache specified URI for user'
    error_ids[51] = 'Chromium preferences file does not exist at the moment'
    error_ids[52] = 'Error during attempt to read Chromium preferences for user'
    error_ids[53] = 'Fail for applying shortcut to file with \'%\''
    error_ids[54] = 'Fail for applying shortcut to not absolute path'
    error_ids[55] = 'Error running pkcon_runner sync for machine'
    error_ids[56] = 'Error run apt-get update'
    error_ids[57] = 'Package install error'
    error_ids[58] = 'Package remove error'
    error_ids[59] = 'Is not in possible values for control'
    error_ids[60] = 'Error running pkcon_runner sync for user'
    error_ids[61] = 'Error running pkcon_runner async for machine'
    error_ids[62] = 'Error running pkcon_runner async for user'


    return error_ids.get(code, 'Unknown error code')

def debug_code(code):
    debug_ids = dict()
    debug_ids[1] = 'The GPOA process was started for user'
    debug_ids[2] = 'Username is not specified - will use username of the current process'
    debug_ids[3] = 'Initializing plugin manager'
    debug_ids[4] = 'ADP plugin initialized'
    debug_ids[5] = 'Running ADP plugin'
    debug_ids[6] = 'Starting GPOA for user via D-Bus'
    debug_ids[7] = 'Cache directory determined'
    debug_ids[8] = 'Initializing local backend without domain'
    debug_ids[9] = 'Initializing Samba backend for domain'
    debug_ids[10] = 'Group Policy target set for update'
    debug_ids[11] = 'Starting GPOA for computer via D-Bus'
    debug_ids[12] = 'Got exit code'
    debug_ids[13] = 'Starting GPOA via D-Bus'
    debug_ids[14] = 'Starting GPOA via command invocation'
    debug_ids[15] = 'Username for frontend is determined'
    debug_ids[16] = 'Applying computer part of settings'
    debug_ids[17] = 'Kerberos ticket check succeed'
    debug_ids[18] = 'Found AD domain via CLDAP query'
    debug_ids[19] = 'Setting info'
    debug_ids[20] = 'Initializing cache'
    debug_ids[21] = 'Set operational SID'
    debug_ids[22] = 'Got PReg entry'
    debug_ids[23] = 'Looking for preference in user part of GPT'
    debug_ids[24] = 'Looking for preference in machine part of GPT'
    debug_ids[25] = 'Re-caching Local Policy'
    debug_ids[26] = 'Adding HKCU entry'
    debug_ids[27] = 'Skipping HKLM branch deletion key'
    debug_ids[28] = 'Reading and merging machine preference'
    debug_ids[29] = 'Reading and merging user preference'
    debug_ids[30] = 'Found SYSVOL entry'
    debug_ids[31] = 'Trying to load PReg from .pol file'
    debug_ids[32] = 'Finished reading PReg from .pol file'
    debug_ids[33] = 'Determined length of PReg file'
    debug_ids[34] = 'Merging machine settings from PReg file'
    debug_ids[35] = 'Merging machine (user part) settings from PReg file'
    debug_ids[36] = 'Loading PReg from XML'
    debug_ids[37] = 'Setting process permissions'
    debug_ids[38] = 'Samba DC setting is overriden by user setting'
    debug_ids[39] = 'Saving information about drive mapping'
    debug_ids[40] = 'Saving information about printer'
    debug_ids[41] = 'Saving information about link'
    debug_ids[42] = 'Saving information about folder'
    debug_ids[43] = 'No value cached for object'
    debug_ids[44] = 'Key is already present in cache, will update the value'
    debug_ids[45] = 'GPO update started'
    debug_ids[46] = 'GPO update finished'
    debug_ids[47] = 'Retrieving list of GPOs to replicate from AD DC'
    debug_ids[48] = 'Establishing connection with AD DC'
    debug_ids[49] = 'Started GPO replication from AD DC'
    debug_ids[50] = 'Finished GPO replication from AD DC'
    debug_ids[51] = 'Skipping HKCU branch deletion key'
    debug_ids[52] = 'Read domain name from configuration file'
    debug_ids[53] = 'Saving information about environment variables'
    debug_ids[54] = 'Run forked process with droped privileges'
    debug_ids[55] = 'Run user context applier with dropped privileges'
    debug_ids[56] = 'Kill dbus-daemon and dconf-service in user context'
    debug_ids[57] = 'Found connection by org.freedesktop.DBus.GetConnectionUnixProcessID'
    debug_ids[58] = 'Connection search return org.freedesktop.DBus.Error.NameHasNoOwner'
    debug_ids[59] = 'Running GPOA without GPT update directly for user'
    debug_ids[60] = 'Running GPOA by root for user'
    debug_ids[61] = 'The GPOA process was started for computer'
    debug_ids[62] = 'Path not resolved as UNC URI'
    debug_ids[63] = 'Delete HKLM branch key'
    debug_ids[64] = 'Delete HKCU branch key'
    debug_ids[65] = 'Delete HKLM branch key error'
    debug_ids[66] = 'Delete HKCU branch key error'
    debug_ids[67] = 'Running Control applier for machine'
    debug_ids[68] = 'Setting control'
    debug_ids[69] = 'Deny_All setting found'
    debug_ids[70] = 'Deny_All setting for user'
    debug_ids[71] = 'Deny_All setting not found'
    debug_ids[72] = 'Deny_All setting not found for user'
    debug_ids[73] = 'Running Polkit applier for machine'
    debug_ids[74] = 'Running Polkit applier for user in administrator context'
    debug_ids[75] = 'Polkit applier for machine will not be started'
    debug_ids[76] = 'Polkit applier for user in administrator context will not be started'
    debug_ids[77] = 'Generated file'
    debug_ids[78] = 'Running systemd applier for machine'
    debug_ids[79] = 'Running systemd applier for machine will not be started'
    debug_ids[80] = 'Running GSettings applier for machine'
    debug_ids[81] = 'GSettings applier for machine will not be started'
    debug_ids[82] = 'Removing GSettings policy file from previous run'
    debug_ids[83] = 'Mapping Windows policies to GSettings policies'
    debug_ids[84] = 'GSettings windows policies mapping not enabled'
    debug_ids[85] = 'Applying user setting'
    debug_ids[86] = 'Found GSettings windows mapping'
    debug_ids[87] = 'Running GSettings applier for user in user context'
    debug_ids[88] = 'GSettings applier for user in user context will not be started'
    debug_ids[89] = 'Applying machine setting'
    debug_ids[90] = 'Getting cached file for URI'
    debug_ids[91] = 'Wrote Firefox preferences to'
    debug_ids[92] = 'Found Firefox profile in'
    debug_ids[93] = 'Running Firefox applier for machine'
    debug_ids[94] = 'Firefox applier for machine will not be started'
    debug_ids[95] = 'Running Chromium applier for machine'
    debug_ids[96] = 'Chromium applier for machine will not be started'
    debug_ids[97] = 'Wrote Chromium preferences to'
    debug_ids[98] = 'Running Shortcut applier for machine'
    debug_ids[99] = 'Shortcut applier for machine will not be started'
    debug_ids[100] = 'No shortcuts to process for'
    debug_ids[101] = 'Running Shortcut applier for user in user context'
    debug_ids[102] = 'Shortcut applier for user in user context will not be started'
    debug_ids[103] = 'Running Shortcut applier for user in administrator context'
    debug_ids[104] = 'Shortcut applier for user in administrator context will not be started'
    debug_ids[105] = 'Try to expand path for shortcut'
    debug_ids[106] = 'Applying shortcut file to'
    debug_ids[107] = 'Running Folder applier for machine'
    debug_ids[108] = 'Folder applier for machine will not be started'
    debug_ids[109] = 'Running Folder applier for user in administrator context'
    debug_ids[110] = 'Folder applier for user in administrator context will not be started'
    debug_ids[111] = 'Running Folder applier for user in user context'
    debug_ids[112] = 'Folder applier for user in user context will not be started'
    debug_ids[113] = 'Running CUPS applier for machine'
    debug_ids[114] = 'CUPS applier for machine will not be started'
    debug_ids[115] = 'Running CUPS applier for user in administrator context'
    debug_ids[116] = 'CUPS applier for user in administrator context will not be started'
    debug_ids[117] = 'Running Firewall applier for machine'
    debug_ids[118] = 'Firewall is enabled'
    debug_ids[119] = 'Firewall is disabled, settings will be reset'
    debug_ids[120] = 'Firewall applier will not be started'
    debug_ids[121] = 'Running NTP applier for machine'
    debug_ids[122] = 'NTP server is configured to'
    debug_ids[123] = 'Starting Chrony daemon'
    debug_ids[124] = 'Setting reference NTP server to'
    debug_ids[125] = 'Stopping Chrony daemon'
    debug_ids[126] = 'Configuring NTP server...'
    debug_ids[127] = 'NTP server is enabled'
    debug_ids[128] = 'NTP server is disabled'
    debug_ids[129] = 'NTP server is not configured'
    debug_ids[130] = 'NTP client is enabled'
    debug_ids[131] = 'NTP client is disabled'
    debug_ids[132] = 'NTP client is not configured'
    debug_ids[133] = 'NTP applier for machine will not be started'
    debug_ids[134] = 'Running Envvar applier for machine'
    debug_ids[135] = 'Envvar applier for machine will not be started'
    debug_ids[136] = 'Running Envvar applier for user in user context'
    debug_ids[137] = 'Envvar applier for user in user context will not be started'
    debug_ids[138] = 'Running Package applier for machine'
    debug_ids[139] = 'Package applier for machine will not be started'
    debug_ids[140] = 'Running Package applier for user in administrator context'
    debug_ids[141] = 'Package applier for user in administrator context will not be started'
    debug_ids[142] = 'Running pkcon_runner to install and remove packages'
    debug_ids[143] = 'Run apt-get update'
    debug_ids[144] = 'Unable to cache specified URI'
    debug_ids[145] = 'Unable to cache specified URI for machine'
    debug_ids[146] = 'Running CIFS applier for user in administrator context'
    debug_ids[147] = 'CIFS applier for user in administrator context will not be started'
    debug_ids[148] = 'Installing the package'
    debug_ids[149] = 'Removing a package'
    debug_ids[150] = 'Failed to found gsettings for machine'
    debug_ids[151] = 'Failed to found user gsettings'

    return debug_ids.get(code, 'Unknown debug code')

def warning_code(code):
    warning_ids = dict()
    warning_ids[1] = (
        'Unable to perform gpupdate for non-existent user, '
        'will update machine settings'
    )
    warning_ids[2] = (
        'Current permissions does not allow to perform gpupdate for '
        'designated user. Will update current user settings'
    )
    warning_ids[3] = 'oddjobd is inaccessible'
    warning_ids[4] = 'No SYSVOL entry assigned to GPO'
    warning_ids[5] = 'ADP package is not installed - plugin will not be initialized'
    warning_ids[6] = 'Unable to resolve GSettings parameter'
    warning_ids[7] = 'No home directory exists for user'
    warning_ids[8] = 'User\'s shortcut not placed to home directory'
    warning_ids[9] = 'CUPS is not installed: no printer settings will be deployed'
    warning_ids[10] = 'Unsupported NTP server type'
    warning_ids[11] = 'Unable to refresh GPO list'

    return warning_ids.get(code, 'Unknown warning code')

def fatal_code(code):
    fatal_ids = dict()
    fatal_ids[1] = 'Unable to refresh GPO list'
    fatal_ids[2] = 'Error getting GPTs for machine'
    fatal_ids[3] = 'Error getting GPTs for user'

    return fatal_ids.get(code, 'Unknown fatal code')

def get_message(code):
    retstr = 'Unknown message type, no message assigned'

    if code.startswith('E'):
        retstr = error_code(int(code[1:]))
    if code.startswith('I'):
        retstr = info_code(int(code[1:]))
    if code.startswith('D'):
        retstr = debug_code(int(code[1:]))
    if code.startswith('W'):
        retstr = warning_code(int(code[1:]))
    if code.startswith('F'):
        retstr = fatal_code(int(code[1:]))

    return retstr

def message_with_code(code):
    retstr = '[' + code[0:1] + code[1:].rjust(5, '0') + ']| ' + gettext.gettext(get_message(code))

    return retstr

