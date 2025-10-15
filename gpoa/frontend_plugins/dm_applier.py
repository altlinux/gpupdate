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


class DMApplier(FrontendPlugin):
    """
    Display Manager Applier - handles loading of display manager policy keys
    from registry (machine/user) and user preferences.

    Also includes DMConfigGenerator functionality for display manager configuration.
    """

    __registry_path = 'Software/BaseALT/Policies/DisplayManager'
    domain = 'dm_applier'

    def __init__(self, dict_dconf_db, username=None, fs_file_cache=None):
        super().__init__(dict_dconf_db, username, fs_file_cache)

        # Initialize plugin-specific logger - locale_dir will be set by plugin_manager
        self._init_plugin_log(
            message_dict={
                'i': {
                    1: "Display Manager Applier initialized",
                    2: "LightDM configuration generated successfully",
                    3: "Display Manager Applier execution started",
                    4: "Display manager configuration completed successfully",
                    5: "LightDM GTK greeter configuration generated successfully"
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
            #"Greeter.Background": self.config.get("Greeter.Background", ""),
            "Greeter.Theme": self.config.get("Greeter.Theme", ""),
            "Session.Default": self.config.get("Session.Default", ""),
            "Security.AllowRootLogin": self.config.get("Security.AllowRootLogin", True),
            "Remote.XDMCP.Enable": self.config.get("Remote.XDMCP.Enable", False),
            "Logging.Level": self.config.get("Logging.Level", "")
        }
        background_path = self.config.get("Greeter.Background", None)
        if background_path:
            fs_file_cache.store(background_path)
            self.dm_config["Greeter.Background"] = fs_file_cache.get(background_path)
        else:
            self.dm_config["Greeter.Background"] = ''
        if not self.dm_config["Autologin.User"]:
            self.dm_config["Autologin.Enable"] = False
            self.dm_config["Autologin.Session"] = ""

        self.log("I1")  # Display Manager Applier initialized

    @classmethod
    def _get_plugin_prefix(cls):
        """Return plugin prefix for translation lookup."""
        return "dm_applier"

    def _prepare_conf(self, path):
        """
        Load existing file or create new, preserving all comments and structure.
        """
        try:
            conf = GpoaConfigObj(path, encoding="utf-8", create_empty=True)
            return conf
        except Exception as e:
            self.log("E20", {"path": path, "error": str(e)})  # Configuration file path is invalid or inaccessible
            return None

    def generate_lightdm(self, path):
        if not path or not os.path.isabs(path):
            self.log("E20", {"path": path})  # Configuration file path is invalid or inaccessible
            return None

        conf = self._prepare_conf(path)
        if not conf:
            return None
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
        if not conf:
            return None
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
        if not conf:
            return None
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

        result = gen(filename)

        # For LightDM, also generate greeter configuration if needed
        if dm_name == "lightdm" and result:
            self._generate_lightdm_greeter_config()

        return result

    def _detect_lightdm_greeter(self):
        """Detect which LightDM greeter is being used"""

        # Check main lightdm.conf
        lightdm_conf_path = "/etc/lightdm/lightdm.conf"
        if os.path.exists(lightdm_conf_path):
            with open(lightdm_conf_path, 'r') as f:
                for line in f:
                    if line.strip().startswith("greeter-session") and not line.strip().startswith('#'):
                        greeter = line.split('=')[1].strip()
                        self.log("D30", {"greeter": greeter, "source": "lightdm.conf"})  # Greeter detection details
                        return greeter

        # Check lightdm.conf.d directory
        lightdm_conf_d = "/etc/lightdm/lightdm.conf.d"
        if os.path.exists(lightdm_conf_d):
            for file in sorted(os.listdir(lightdm_conf_d)):
                if file.endswith('.conf'):
                    file_path = os.path.join(lightdm_conf_d, file)
                    with open(file_path, 'r') as f:
                        for line in f:
                            if line.strip().startswith("greeter-session") and not line.strip().startswith('#'):
                                greeter = line.split('=')[1].strip()
                                self.log("D30", {"greeter": greeter, "source": file})  # Greeter detection details
                                return greeter

        # Check default greeter
        default_greeter_path = "/usr/share/xgreeters/lightdm-default-greeter.desktop"
        if os.path.exists(default_greeter_path):
            with open(default_greeter_path, 'r') as f:
                for line in f:
                    if line.strip().startswith("Exec=") and not line.strip().startswith('#'):
                        greeter_exec = line.split('=')[1].strip()
                        # Extract greeter name from exec path
                        greeter_name = os.path.basename(greeter_exec)
                        self.log("D30", {"greeter": greeter_name, "source": "default-greeter"})  # Greeter detection details
                        return greeter_name

        # Fallback to gtk-greeter (most common)
        self.log("D30", {"greeter": "lightdm-gtk-greeter", "source": "fallback"})  # Greeter detection details
        return "lightdm-gtk-greeter"

    def _generate_lightdm_greeter_config(self):
        """Generate configuration for the detected LightDM greeter"""

        # Only generate if we have greeter settings
        if not (self.dm_config["Greeter.Background"] or self.dm_config["Greeter.Theme"]):
            return

        greeter_name = self._detect_lightdm_greeter()

        # Map greeter names to configuration files and settings
        greeter_configs = {
            "lightdm-gtk-greeter": {
                "config_path": "/etc/lightdm/lightdm-gtk-greeter.conf",
                "section": "greeter",
                "background_key": "background",
                "theme_key": "theme-name"
            },
            "lightdm-webkit2-greeter": {
                "config_path": "/etc/lightdm/lightdm-webkit2-greeter.conf",
                "section": "greeter",
                "background_key": "background",
                "theme_key": "theme"
            },
            "lightdm-unity-greeter": {
                "config_path": "/etc/lightdm/lightdm-unity-greeter.conf",
                "section": "greeter",
                "background_key": "background",
                "theme_key": "theme-name"
            },
            "lightdm-slick-greeter": {
                "config_path": "/etc/lightdm/lightdm-slick-greeter.conf",
                "section": "greeter",
                "background_key": "background",
                "theme_key": "theme-name"
            },
            "lightdm-kde-greeter": {
                "config_path": "/etc/lightdm/lightdm-kde-greeter.conf",
                "section": "greeter",
                "background_key": "background",
                "theme_key": "theme"
            }
        }

        config_info = greeter_configs.get(greeter_name)
        if not config_info:
            self.log("E22", {"greeter": greeter_name})  # Unknown greeter type
            return

        conf = self._prepare_conf(config_info["config_path"])

        # Get or create the greeter section
        greeter_section = conf.setdefault(config_info["section"], {})

        # Apply greeter settings
        if self.dm_config["Greeter.Background"]:
            greeter_section[config_info["background_key"]] = self.dm_config["Greeter.Background"]
        if self.dm_config["Greeter.Theme"]:
            greeter_section[config_info["theme_key"]] = self.dm_config["Greeter.Theme"]

        # Remove settings if they were previously set but now empty
        if not self.dm_config["Greeter.Background"] and config_info["background_key"] in greeter_section:
            del greeter_section[config_info["background_key"]]
        if not self.dm_config["Greeter.Theme"] and config_info["theme_key"] in greeter_section:
            del greeter_section[config_info["theme_key"]]

        conf.initial_comment = [f"# {greeter_name} custom config"]
        try:
            conf.write()
            self.log("I5", {"path": config_info["config_path"], "greeter": greeter_name})  # Greeter config generated
        except Exception as e:
            self.log("E21", {"path": config_info["config_path"], "error": str(e)})  # Failed to generate greeter config

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
            self.log("D2", {"unit": "display-manager.service", "error": str(e)})  # DM config details
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
            target_dm = dm_info["active"] or (dm_info["available"][0] if dm_info["available"] else None)

            if not target_dm:
                self.log("W10")  # No display managers detected
                return False

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
                self.log("I4", {"dm": target_dm, "config_dir": config_dir})  # DM config completed successfully
                return True
            else:
                self.log("E23", {"dm": target_dm, "config_dir": config_dir})  # Failed to generate DM config
                return False

        except Exception as e:
            self.log("E24", {"error": str(e)})  # Display Manager Applier execution failed
            return False


def create_applier(dict_dconf_db, username=None, fs_file_cache=None):
    """Factory function to create DMApplier instance"""
    return DMApplier(dict_dconf_db, username, fs_file_cache)
