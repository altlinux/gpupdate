import logging

from .applier_frontend import applier_frontend
from .appliers.gsettings import (
    system_gsetting,
    user_gsetting
)

class gsettings_applier(applier_frontend):
    __registry_branch = 'Software\\BaseALT\\Policies\\gsettings'

    def __init__(self, storage):
        self.storage = storage
        gsettings_filter = '{}%'.format(self.__registry_branch)
        self.gsettings_keys = self.storage.filter_hklm_entries(gsettings_filter)
        self.gsettings = list()

    def apply(self):
        for setting in self.gsettings_keys:
            valuename = setting.hive_key.rpartition('\\')[2]
            rp = valuename.rpartition('.')
            schema = rp[0]
            path = rp[2]
            self.gsettings.append(system_gsetting(schema, path, setting.data))

        for gsetting in self.gsettings:
            gsetting.apply()

class gsettings_applier_user(applier_frontend):
    __registry_branch = 'Software\\BaseALT\\Policies\\gsettings'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        gsettings_filter = '{}%'.format(self.__registry_branch)
        self.gsettings_keys = self.storage.filter_hkcu_entries(self.sid, gsettings_filter)
        self.gsettings = list()

    def user_context_apply(self):
        for setting in self.gsettings_keys:
            valuename = setting.hive_key.rpartition('\\')[2]
            rp = valuename.rpartition('.')
            schema = rp[0]
            path = rp[2]
            self.gsettings.append(user_gsetting(schema, path, setting.data))

        for gsetting in self.gsettings:
            gsetting.apply()

    def admin_context_apply(self):
        pass

