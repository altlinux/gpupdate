#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2025 BaseALT Ltd.
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
import shutil
import subprocess
from pathlib import Path
from util.gpoa_ini_parsing import GpoaConfigObj


class DMConfigGenerator:
    """
    Generate configs for LightDM, GDM, SDDM using GpoaConfigObj (ConfigObj-based, preserving comments).
    """
    def __init__(self, config: dict):
        self.cfg = {
            "Autologin.Enable": config.get("Autologin.Enable", False),
            "Autologin.User": config.get("Autologin.User", ""),
            "Autologin.Session": config.get("Autologin.Session", ""),
            "Greeter.Background": config.get("Greeter.Background", ""),
            "Greeter.Theme": config.get("Greeter.Theme", ""),
            "Session.Default": config.get("Session.Default", ""),
            "Security.AllowRootLogin": config.get("Security.AllowRootLogin", True),
            "Remote.XDMCP.Enable": config.get("Remote.XDMCP.Enable", False),
            "Logging.Level": config.get("Logging.Level", "")
        }
        if not self.cfg["Autologin.User"]:
            self.cfg["Autologin.Enable"] = False

    def _prepare_conf(self, path: str):
        """
        Load existing file or create new, preserving all comments and structure.
        """
        conf = GpoaConfigObj(path, encoding="utf-8", create_empty=True)
        return conf

    def generate_lightdm(self, path: str):
        conf = self._prepare_conf(path)
        section = conf.setdefault("Seat:*", {})
        # Set values:
        if self.cfg["Autologin.Enable"]:
            section["autologin-user"] = self.cfg["Autologin.User"]
            if self.cfg["Autologin.Session"]:
                section["autologin-session"] = self.cfg["Autologin.Session"]
        if self.cfg["Greeter.Theme"]:
            section["greeter-theme-name"] = self.cfg["Greeter.Theme"]
        if self.cfg["Greeter.Background"]:
            section["greeter-background"] = self.cfg["Greeter.Background"]
        if not self.cfg["Security.AllowRootLogin"]:
            section["allow-root"] = "false"
        if self.cfg["Remote.XDMCP.Enable"]:
            x = conf.setdefault("XDMCPServer", {})
            x["enabled"] = "true"
        if self.cfg["Logging.Level"]:
            section["log-level"] = self.cfg["Logging.Level"]

        # Comments example:
        conf.initial_comment = ["# LightDM custom config"]
        conf.write()
        return conf

    def generate_gdm(self, path: str):
        conf = self._prepare_conf(path)
        daemon = conf.setdefault("daemon", {})
        if self.cfg["Autologin.Enable"]:
            daemon["AutomaticLoginEnable"] = "true"
            daemon["AutomaticLogin"] = self.cfg["Autologin.User"]
            if self.cfg["Autologin.Session"]:
                daemon["AutomaticLoginSession"] = self.cfg["Autologin.Session"]
        if self.cfg["Session.Default"].lower() == "x11":
            daemon["WaylandEnable"] = "false"
        if self.cfg["Remote.XDMCP.Enable"]:
            conf.setdefault("xdmcp", {})["Enable"] = "true"
        if self.cfg["Greeter.Background"] or self.cfg["Greeter.Theme"]:
            greeter = conf.setdefault("greeter", {})
            if self.cfg["Greeter.Background"]:
                greeter["Background"] = self.cfg["Greeter.Background"]
            if self.cfg["Greeter.Theme"]:
                greeter["ThemeName"] = self.cfg["Greeter.Theme"]
        if not self.cfg["Security.AllowRootLogin"]:
            daemon.comments = daemon.comments or {}
            daemon.comments.setdefault("AutomaticLogin", []).append(
                "# Root login disabled (handled externally)"
            )
        if self.cfg["Logging.Level"]:
            daemon.comments = daemon.comments or {}
            daemon.comments.setdefault("log-comment", []).append(
                f"# Logging: {self.cfg['Logging.Level']}"
            )
        conf.write()
        return conf

    def generate_sddm(self, path: str):
        conf = self._prepare_conf(path)
        autologin = conf.setdefault("Autologin", {})
        if self.cfg["Autologin.Enable"]:
            autologin["User"] = self.cfg["Autologin.User"]
            if self.cfg["Autologin.Session"]:
                autologin["Session"] = self.cfg["Autologin.Session"]
        theme = conf.setdefault("Theme", {})
        if self.cfg["Greeter.Theme"]:
            theme["Current"] = self.cfg["Greeter.Theme"]
        if self.cfg["Greeter.Background"]:
            theme["Background"] = self.cfg["Greeter.Background"]
        users = conf.setdefault("Users", {})
        if not self.cfg["Security.AllowRootLogin"]:
            users["AllowRootLogin"] = "false"
        general = conf.setdefault("General", {})
        if self.cfg["Logging.Level"]:
            general["LogLevel"] = self.cfg["Logging.Level"]
        if self.cfg["Remote.XDMCP.Enable"]:
            general.comments = general.comments or {}
            general.comments.setdefault("xdmcp", []).append(
                "# XDMCP enabled (manual config may be required)"
            )
        conf.write()
        return conf

    def write_config(self, dm_name: str, directory: str):
        os.makedirs(directory, exist_ok=True)
        filename = os.path.join(directory, "50-custom.conf")
        gen = {
            "lightdm": self.generate_lightdm,
            "gdm": self.generate_gdm,
            "sddm": self.generate_sddm
        }.get(dm_name)
        if not gen:
            raise ValueError(f"Unknown DM: {dm_name}")
        return gen(filename)

    def detect_dm(self):
        result = {"available": [], "active": None}
        for dm, bins in {"lightdm": ["lightdm"], "gdm": ["gdm", "gdm3"], "sddm": ["sddm"]}.items():
            if any(shutil.which(bn) for bn in bins):
                result["available"].append(dm)
        dm_service = Path("/etc/systemd/system/display-manager.service")
        if dm_service.is_symlink():
            target = os.path.basename(os.readlink(dm_service))
            result["active"] = next((d for d in result["available"] if d in target), None)
        else:
            try:
                status = subprocess.check_output(
                    ["systemctl", "status", "display-manager.service"], stderr=subprocess.DEVNULL
                ).decode()
                result["active"] = next((d for d in result["available"] if d in status), None)
            except Exception:
                pass
        return result