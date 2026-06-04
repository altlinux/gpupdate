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

from .applier_frontend import applier_frontend, DualContextApplier
from .chromium_applier import chromium_applier
from .cifs_applier import cifs_applier, cifs_applier_user
from .control_applier import control_applier
from .envvar_applier import envvar_applier, envvar_applier_user
from .file_applier import file_applier, file_applier_user
from .firefox_applier import firefox_applier
from .firewall_applier import firewall_applier
from .folder_applier import folder_applier, folder_applier_user
from .gsettings_applier import gsettings_applier, gsettings_applier_user
from .ini_applier import ini_applier, ini_applier_user
from .kde_applier import kde_applier, kde_applier_user
from .laps_applier import laps_applier
from .networkshare_applier import networkshare_applier
from .ntp_applier import ntp_applier
from .package_applier import package_applier, package_applier_user
from .polkit_applier import polkit_applier, polkit_applier_user
from .scripts_applier import scripts_applier, scripts_applier_user
from .systemd_applier import systemd_applier, systemd_applier_user
from .thunderbird_applier import thunderbird_applier
from .yandex_browser_applier import yandex_browser_applier
