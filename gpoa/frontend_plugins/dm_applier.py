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

# Import only what's absolutely necessary
try:
    from gpoa.frontend.appliers.systemd import systemd_unit
except ImportError:
    # Fallback for testing
    systemd_unit = None

try:
    from gpoa.util.gpoa_ini_parsing import GpoaConfigObj
except ImportError:
    # Fallback for testing
    GpoaConfigObj = None

from gpoa.plugin.plugin_base import FrontendPlugin
from gpoa.plugin.plugin_log import PluginLog


class DMApplier(FrontendPlugin):
    """
    Display Manager Applier - handles loading of display manager policy keys
    from registry (machine/user) and user preferences.

    Also includes DMConfigGenerator functionality for display manager configuration.
    """

    __registry_path = 'Software/BaseALT/Policies/DisplayManager'
    __plugin_prefix = 'DM1'

    def __init__(self, dict_dconf_db, username=None):
        super().__init__(dict_dconf_db, username)

        # Initialize plugin-specific logger - locale_dir will be set by plugin_manager
        self._init_plugin_log(
            plugin_prefix=self.__plugin_prefix,
            message_dict={
                'i': {
                    1: "Display Manager Applier initialized",
                    2: "LightDM configuration generated successfully",
                    3: "Display Manager Applier execution started",
                    4: "Display manager configuration completed successfully"
                },
                'w': {
                    10: "No display managers detected"
                },
                'e': {
                    20: "Configuration file path is invalid or inaccessible",
                    21: "Failed to generate LightDM configuration",
                    22: "Unknown display manager config directory",
                    23: "Failed to generate display manager configuration",
                    24: "Display Manager Applier execution failed"
                },
                'd': {
                    30: "Display manager detection details",
                    31: "Display manager configuration details"
                }
            },
            # locale_dir will be set by plugin_manager during plugin loading
            domain="dm_applier"
        )

        self.config = self.get_dict_registry(self.__registry_path)

        # DMConfigGenerator configuration
        self.dm_config = {
            "Autologin.Enable": self.config.get("Autologin.Enable", False),
            "Autologin.User": self.config.get("Autologin.User", ""),
            "Autologin.Session": self.config.get("Autologin.Session", ""),
            "Greeter.Background": self.config.get("Greeter.Background", ""),
            "Greeter.Theme": self.config.get("Greeter.Theme", ""),
            "Session.Default": self.config.get("Session.Default", ""),
            "Security.AllowRootLogin": self.config.get("Security.AllowRootLogin", True),
            "Remote.XDMCP.Enable": self.config.get("Remote.XDMCP.Enable", False),
            "Logging.Level": self.config.get("Logging.Level", "")
        }

        if not self.dm_config["Autologin.User"]:
            self.dm_config["Autologin.Enable"] = False

        self.log("I1")  # Display Manager Applier initialized

    @classmethod
    def _get_plugin_prefix(cls):
        """Return plugin prefix for translation lookup."""
        return cls.__plugin_prefix

    def _prepare_conf(self, path):
        """
        Load existing file or create new, preserving all comments and structure.
        """
        conf = GpoaConfigObj(path, encoding="utf-8", create_empty=True)
        return conf

    def generate_lightdm(self, path):
        if not path or not os.path.isabs(path):
            self.log("E20", {"path": path})  # Configuration file path is invalid or inaccessible
            return None

        conf = self._prepare_conf(path)
        section = conf.setdefault("Seat:*", {})

        # Set values:
        if self.dm_config["Autologin.Enable"]:
            section["autologin-user"] = self.dm_config["Autologin.User"]
            if self.dm_config["Autologin.Session"]:
                section["autologin-session"] = self.dm_config["Autologin.Session"]
        if self.dm_config["Greeter.Theme"]:
            section["greeter-theme-name"] = self.dm_config["Greeter.Theme"]
        if self.dm_config["Greeter.Background"]:
            section["greeter-background"] = self.dm_config["Greeter.Background"]
        if not self.dm_config["Security.AllowRootLogin"]:
            section["allow-root"] = "false"
        if self.dm_config["Remote.XDMCP.Enable"]:
            x = conf.setdefault("XDMCPServer", {})
            x["enabled"] = "true"
        if self.dm_config["Logging.Level"]:
            section["log-level"] = self.dm_config["Logging.Level"]

        # Comments example:
        conf.initial_comment = ["# LightDM custom config"]
        try:
            conf.write()
            self.log("I2", {"path": path})  # LightDM configuration generated successfully
            return conf
        except Exception as e:
            self.log("E21", {"path": path, "error": str(e)})  # Failed to generate LightDM configuration
            return None

    def generate_gdm(self, path):
        conf = self._prepare_conf(path)
        daemon = conf.setdefault("daemon", {})
        if self.dm_config["Autologin.Enable"]:
            daemon["AutomaticLoginEnable"] = "true"
            daemon["AutomaticLogin"] = self.dm_config["Autologin.User"]
            if self.dm_config["Autologin.Session"]:
                daemon["AutomaticLoginSession"] = self.dm_config["Autologin.Session"]
        if self.dm_config["Session.Default"].lower() == "x11":
            daemon["WaylandEnable"] = "false"
        if self.dm_config["Remote.XDMCP.Enable"]:
            conf.setdefault("xdmcp", {})["Enable"] = "true"
        if self.dm_config["Greeter.Background"] or self.dm_config["Greeter.Theme"]:
            greeter = conf.setdefault("greeter", {})
            if self.dm_config["Greeter.Background"]:
                greeter["Background"] = self.dm_config["Greeter.Background"]
            if self.dm_config["Greeter.Theme"]:
                greeter["ThemeName"] = self.dm_config["Greeter.Theme"]
        if not self.dm_config["Security.AllowRootLogin"]:
            daemon.comments = daemon.comments or {}
            daemon.comments.setdefault("AutomaticLogin", []).append(
                "# Root login disabled (handled externally)"
            )
        if self.dm_config["Logging.Level"]:
            daemon.comments = daemon.comments or {}
            daemon.comments.setdefault("log-comment", []).append(
                f"# Logging: {self.dm_config['Logging.Level']}"
            )
        conf.write()
        return conf

    def generate_sddm(self, path):
        conf = self._prepare_conf(path)
        autologin = conf.setdefault("Autologin", {})
        if self.dm_config["Autologin.Enable"]:
            autologin["User"] = self.dm_config["Autologin.User"]
            if self.dm_config["Autologin.Session"]:
                autologin["Session"] = self.dm_config["Autologin.Session"]
        theme = conf.setdefault("Theme", {})
        if self.dm_config["Greeter.Theme"]:
            theme["Current"] = self.dm_config["Greeter.Theme"]
        if self.dm_config["Greeter.Background"]:
            theme["Background"] = self.dm_config["Greeter.Background"]
        users = conf.setdefault("Users", {})
        if not self.dm_config["Security.AllowRootLogin"]:
            users["AllowRootLogin"] = "false"
        general = conf.setdefault("General", {})
        if self.dm_config["Logging.Level"]:
            general["LogLevel"] = self.dm_config["Logging.Level"]
        if self.dm_config["Remote.XDMCP.Enable"]:
            general.comments = general.comments or {}
            general.comments.setdefault("xdmcp", []).append(
                "# XDMCP enabled (manual config may be required)"
            )
        conf.write()
        return conf

    def write_config(self, dm_name, directory):
        os.makedirs(directory, exist_ok=True)
        filename = os.path.join(directory, "50-custom.conf")
        gen = {
            "lightdm": self.generate_lightdm,
            "gdm": self.generate_gdm,
            "sddm": self.generate_sddm
        }.get(dm_name)
        if not gen:
            raise ValueError("Unknown DM: {}".format(dm_name))
        return gen(filename)

    def detect_dm(self):
        result = {"available": [], "active": None}

        if shutil.which("lightdm"):
            result["available"].append("lightdm")
        if shutil.which("gdm") or shutil.which("gdm3"):
            result["available"].append("gdm")
        if shutil.which("sddm"):
            result["available"].append("sddm")

        # Check via systemd D-Bus
        active = self._check_systemd_dm()
        if active:
            result["active"] = active

        return result

    def _check_systemd_dm(self):
        """
        Check active display manager via systemd D-Bus API.
        Returns dm name (lightdm/gdm/sddm) or None if not active.
        """
        try:
            dm_unit = systemd_unit("display-manager.service", 1)
            state = dm_unit._get_state()
            if state in ("active", "activating"):
                unit_path = str(dm_unit.unit)  # D-Bus object path, e.g. /org/.../lightdm_2eservice
                for dm in ["lightdm", "gdm", "sddm"]:
                    if dm in unit_path:
                        return dm
        except Exception as e:
            self.log("D2", {"unit": "display-manager.service", "error": str(e)})  # Display manager configuration details
        return None

    def run(self):
        """
        Main plugin execution method.
        Detects active display manager and applies configuration.
        """
        self.log("I3")  # Display Manager Applier execution started

        try:
            # Detect available and active display managers
            dm_info = self.detect_dm()
            self.log("D30", {"dm_info": dm_info})  # Display manager detection details

            if not dm_info["available"]:
                self.log("W10")  # No display managers detected
                return False

            # Use active DM or first available
            target_dm = dm_info["active"] or dm_info["available"][0]

            # Determine config directory based on DM
            config_dirs = {
                "lightdm": "/etc/lightdm/lightdm.conf.d",
                "gdm": "/etc/gdm/custom.conf.d",
                "sddm": "/etc/sddm.conf.d"
            }

            config_dir = config_dirs.get(target_dm)
            if not config_dir:
                self.log("E22", {"dm": target_dm})  # Unknown display manager config directory
                return False

            # Generate configuration
            result = self.write_config(target_dm, config_dir)

            if result:
                self.log("I4", {"dm": target_dm, "config_dir": config_dir})  # Display manager configuration completed successfully
                return True
            else:
                self.log("E23", {"dm": target_dm, "config_dir": config_dir})  # Failed to generate display manager configuration
                return False

        except Exception as e:
            self.log("E24", {"error": str(e)})  # Display Manager Applier execution failed
            return False

def create_applier(dict_dconf_db, username=None):
    """Factory function to create DMApplier instance"""
    return DMApplier(dict_dconf_db, username)