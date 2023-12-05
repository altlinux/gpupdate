#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2021 BaseALT Ltd. <org@basealt.ru>
# Copyright (C) 2021 Igor Chudov <nir@nir.org.ru>
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

import os
import os.path
import tempfile
from pathlib import Path
import smbc


from util.logging import log
from util.paths import file_cache_dir, file_cache_path_home, UNCPath
from util.exceptions import NotUNCPathError


class fs_file_cache:
    __read_blocksize = 4096

    def __init__(self, cache_name, username = None):
        self.cache_name = cache_name
        if username:
            try:
                self.storage_uri = file_cache_path_home(username)
            except:
                self.storage_uri = file_cache_dir()
        else:
            self.storage_uri = file_cache_dir()
        logdata = dict({'cache_file': self.storage_uri})
        log('D20', logdata)
        self.samba_context = smbc.Context(use_kerberos=1)
                #, debug=10)

    def store(self, uri, destfile = None):
        try:
            uri_path = UNCPath(uri)
            if not destfile:
                file_name = os.path.basename(uri_path.get_path())
                file_path = os.path.dirname(uri_path.get_path())
                destdir = Path('{}/{}/{}'.format(self.storage_uri,
                    uri_path.get_domain(),
                    file_path))
            else:
                destdir = destfile.parent
        except NotUNCPathError:
            return None

        except Exception as exc:
            logdata = dict({'exception': str(exc)})
            log('D144', logdata)
            raise exc

        if not destdir.exists():
            destdir.mkdir(parents=True, exist_ok=True)

        if not destfile:
            destfile = Path('{}/{}/{}'.format(self.storage_uri,
                uri_path.get_domain(),
                uri_path.get_path()))

        try:
            fd, tmpfile = tempfile.mkstemp('', str(destfile))
            df = os.fdopen(fd, 'wb')
            file_handler = self.samba_context.open(str(uri_path), os.O_RDONLY)
            while True:
                data = file_handler.read(self.__read_blocksize)
                if not data:
                    break
                df.write(data)
            df.close()
            os.rename(tmpfile, destfile)
            os.chmod(destfile, 0o644)
        except:
            tmppath = Path(tmpfile)
            if tmppath.exists():
                tmppath.unlink()

    def get(self, uri):
        destfile = uri
        try:
            uri_path = UNCPath(uri)
            file_name = os.path.basename(uri_path.get_path())
            file_path = os.path.dirname(uri_path.get_path())
            destfile = Path('{}/{}/{}'.format(self.storage_uri,
                uri_path.get_domain(),
                uri_path.get_path()))
        except NotUNCPathError as exc:
            logdata = dict({'path': str(exc)})
            log('D62', logdata)
        except Exception as exc:
            logdata = dict({'exception': str(exc)})
            log('E36', logdata)
            raise exc

        return str(destfile)

    def get_ls_smbdir(self, uri):
        type_file_smb = 8
        try:
            uri_path = UNCPath(uri)
            opendir = self.samba_context.opendir(str(uri_path))
            ls_obj = opendir.getdents()
            ls = [obj.name for obj in ls_obj if obj.smbc_type == type_file_smb]
            return ls
        except Exception as exc:
            if Path(uri).exists():
                return None
            logdata = dict({'exception': str(exc)})
            log('W12', logdata)
            return None
