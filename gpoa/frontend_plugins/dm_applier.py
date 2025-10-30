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
import re

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
                    2: "Display manager configuration generated successfully",
                    3: "Display Manager Applier execution started",
                    4: "Display manager configuration completed successfully",
                    5: "LightDM greeter configuration generated successfully",
                    6: "GDM theme modified successfully"
                },
                'w': {
                    10: "No display managers detected",
                    11: "No background configuration to apply"
                },
                'e': {
                    20: "Configuration file path is invalid or inaccessible",
                    21: "Failed to generate display manager configuration",
                    22: "Unknown display manager config directory",
                    23: "Failed to generate display manager configuration",
                    24: "Display Manager Applier execution failed",
                    25: "GDM theme gresource not found",
                    26: "Failed to extract GDM gresource",
                    27: "Failed to modify GDM background",
                    28: "Failed to recompile GDM gresource"
                },
                'd': {
                    30: "Display manager detection details",
                    31: "Display manager configuration details",
                    32: "Removed empty configuration value",
                    33: "GDM background modification details"
                }
            },
            # locale_dir will be set by plugin_manager during plugin loading
            domain="dm_applier"
        )

        self.config = self.get_dict_registry(self.__registry_path)

        # DMConfigGenerator configuration - only background settings
        background_path = self.config.get("Greeter.Background", None)
        if background_path:
            normalized_path = background_path.replace('\\', '/')
            fs_file_cache.store(normalized_path)
            self.dm_config = {
                "Greeter.Background": fs_file_cache.get(normalized_path)
            }
        else:
            self.dm_config = {
                "Greeter.Background": ''
            }

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
        except Exception as exc:
            self.log("E20", {"path": path, "error": str(exc)})
            return None

    def _clean_empty_values(self, section):
        """
        Remove keys with empty values from configuration section.
        Avoids writing empty values to config files.
        """
        if not section:
            return

        # Create list of keys to remove (can't modify dict during iteration)
        keys_to_remove = []
        for key, value in section.items():
            # Remove keys with empty strings, None, or whitespace-only values
            if value is None or (isinstance(value, str) and not value.strip()):
                keys_to_remove.append(key)

        # Remove the identified keys
        for key in keys_to_remove:
            del section[key]
            self.log("D32", {"key": key, "section": str(section)})

    def generate_lightdm(self, path):
        if not path or not os.path.isabs(path):
            self.log("E20", {"path": path})  # Configuration file path is invalid or inaccessible
            return None

        conf = self._prepare_conf(path)
        if conf is None:
            return None
        section = conf.setdefault("Seat:*", {})

        # Set values only if they have meaningful content (avoid writing empty values)
        if self.dm_config["Greeter.Background"]:
            section["greeter-background"] = self.dm_config["Greeter.Background"]

        # Remove any existing empty values that might have been set previously
        self._clean_empty_values(section)

        # Comments example:
        conf.initial_comment = ["# LightDM custom config"]
        try:
            conf.write()
            self.log("I2", {"path": path, "dm": "lightdm"})
            return conf
        except Exception as exc:
            self.log("E21", {"path": path, "error": str(exc)})
            return None


    def generate_gdm(self, path):
        """Generate GDM configuration by modifying gnome-shell-theme.gresource"""
        if not self.dm_config["Greeter.Background"]:
            return None

        background_path = self.dm_config["Greeter.Background"]

        try:
            # Find gnome-shell-theme.gresource
            gresource_path = self._find_gnome_shell_gresource()
            if not gresource_path:
                self.log("E25", {"path": "gnome-shell-theme.gresource"})
                return None

            # Extract gresource to temporary directory
            temp_dir = self._extract_gresource(gresource_path)
            if not temp_dir:
                return None

            # Modify background in theme files
            modified = self._modify_gdm_background(temp_dir, background_path)
            if not modified:
                shutil.rmtree(temp_dir)
                return None

            # Recompile gresource
            success = self._recompile_gresource(temp_dir, gresource_path)

            # Clean up temporary directory
            shutil.rmtree(temp_dir)

            if success:
                self.log("I6", {"path": gresource_path, "background": background_path})
                return True
            else:
                self.log("E28", {"path": gresource_path})
                return None

        except Exception as exc:
            self.log("E21", {"path": "gnome-shell-theme.gresource", "error": str(exc), "dm": "gdm"})
            return None

    def _find_gnome_shell_gresource(self):
        """Find gnome-shell-theme.gresource file"""
        possible_paths = [
            "/usr/share/gnome-shell/gnome-shell-theme.gresource",
            "/usr/share/gnome-shell/theme/gnome-shell-theme.gresource",
            "/usr/share/gdm/gnome-shell-theme.gresource",
            "/usr/local/share/gnome-shell/gnome-shell-theme.gresource"
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def _extract_gresource(self, gresource_path):
        """Extract gresource file to temporary directory by creating XML from gresource list"""
        try:
            temp_dir = "/tmp/gdm_theme_" + str(os.getpid())
            os.makedirs(temp_dir, exist_ok=True)

            # Get list of resources from gresource file
            cmd_list = ["gresource", "list", gresource_path]
            result_list = subprocess.run(cmd_list, capture_output=True, text=True)

            if result_list.returncode != 0:
                self.log("E26", {"path": gresource_path, "error": result_list.stderr})
                shutil.rmtree(temp_dir)
                return None

            resource_paths = result_list.stdout.strip().split('\n')
            if not resource_paths or not resource_paths[0]:
                self.log("E26", {"path": gresource_path, "error": "No resources found in gresource file"})
                shutil.rmtree(temp_dir)
                return None

            # Extract prefix from resource paths (remove filename from first path)
            first_resource = resource_paths[0]
            prefix = os.path.dirname(first_resource)

            # Create temporary XML file using proper XML generation
            import xml.etree.ElementTree as ET

            # Create root element
            gresources = ET.Element('gresources')
            gresource = ET.SubElement(gresources, 'gresource', prefix=prefix)

            for resource_path in resource_paths:
                # Extract filename from resource path
                filename = os.path.basename(resource_path)
                ET.SubElement(gresource, 'file').text = filename

                # Extract the resource to temporary directory
                cmd_extract = ["gresource", "extract", gresource_path, resource_path]
                result_extract = subprocess.run(cmd_extract, capture_output=True, text=True)

                if result_extract.returncode == 0:
                    # Write extracted content to file
                    output_path = os.path.join(temp_dir, filename)
                    with open(output_path, 'w') as f:
                        f.write(result_extract.stdout)
                else:
                    self.log("E26", {"path": gresource_path, "error": f"Failed to extract {resource_path}: {result_extract.stderr}"})

            # Write XML file with proper formatting
            xml_file = os.path.join(temp_dir, "gnome-shell-theme.gresource.xml")
            tree = ET.ElementTree(gresources)
            tree.write(xml_file, encoding='utf-8', xml_declaration=True)

            return temp_dir

        except Exception as exc:
            self.log("E26", {"path": gresource_path, "error": str(exc)})
            return None



    def _modify_gdm_background(self, temp_dir, background_path):
        """Modify background in GDM theme files - specifically target gnome-shell-dark.css and gnome-shell-light.css"""
        try:
            # Target specific CSS files that contain GDM background definitions
            target_css_files = ["gnome-shell-dark.css", "gnome-shell-light.css"]

            modified = False
            for css_filename in target_css_files:
                css_file = os.path.join(temp_dir, css_filename)
                if not os.path.exists(css_file):
                    continue

                with open(css_file, 'r') as f:
                    content = f.read()

                # Look for background-related CSS rules
                patterns = [
                    # Handle only #lockDialogGroup background with file://// (4 slashes)
                    r'(#lockDialogGroup\s*{[^}]*background:\s*[^;]*)url\(file:////[^)]+\)',
                    # Handle only #lockDialogGroup background with file:/// (3 slashes)
                    r'(#lockDialogGroup\s*{[^}]*background:\s*[^;]*)url\(file:///[^)]+\)'
                ]

                for pattern in patterns:
                    # Use lambda function to handle optional groups gracefully
                    def replace_url(match):
                        groups = match.groups()
                        return f'{groups[0]}url(file:///{background_path})'

                    new_content = re.sub(pattern, replace_url, content)
                    if new_content != content:
                        with open(css_file, 'w') as f:
                            f.write(new_content)
                        modified = True
                        self.log("D33", {"file": css_filename, "background": background_path})
                        break

            return modified

        except Exception as exc:
            self.log("E27", {"path": temp_dir, "error": str(exc)})
            return False

    def _recompile_gresource(self, temp_dir, gresource_path):
        """Recompile gresource from modified files using temporary XML"""
        try:
            # Use the temporary XML file created during extraction
            xml_file = os.path.join(temp_dir, "gnome-shell-theme.gresource.xml")
            if not os.path.exists(xml_file):
                self.log("E28", {"path": gresource_path, "error": "Temporary XML file not found"})
                return False

            # Recompile gresource - run from temp directory where files are located
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                cmd = ["glib-compile-resources", "--target", gresource_path, "gnome-shell-theme.gresource.xml"]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    return True
                else:
                    self.log("E28", {"path": gresource_path, "error": result.stderr})
                    return False
            finally:
                os.chdir(original_cwd)

        except Exception as exc:
            self.log("E28", {"path": gresource_path, "error": str(exc)})
            return False

    def generate_sddm(self, path):
        conf = self._prepare_conf(path)
        if conf is None:
            return None

        # Set values only if they have meaningful content
        if self.dm_config["Greeter.Background"]:
            theme = conf.setdefault("Theme", {})
            theme["Background"] = self.dm_config["Greeter.Background"]

        # Clean up empty values from all sections
        self._clean_empty_values(theme)

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

        # For LightDM, always generate greeter configuration if needed
        if dm_name == "lightdm":
            self._generate_lightdm_greeter_config()

        # Return True if configuration was created or if we have background settings
        return result is not None or self.dm_config["Greeter.Background"]

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

        # Only generate if we have background settings
        if not self.dm_config["Greeter.Background"]:
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

        # Apply background setting only if it has meaningful content
        if self.dm_config["Greeter.Background"]:
            greeter_section[config_info["background_key"]] = self.dm_config["Greeter.Background"]

        # Clean up any empty values in the greeter section
        self._clean_empty_values(greeter_section)

        conf.initial_comment = [f"# {greeter_name} custom config"]
        try:
            conf.write()
            self.log("I5", {"path": config_info["config_path"], "greeter": greeter_name})
        except Exception as exc:
            self.log("E21", {"path": config_info["config_path"], "error": str(exc)})

    def detect_dm(self):
        """Detect available and active display managers with fallback methods"""
        result = {"available": [], "active": None}

        # Check for available DMs using multiple methods
        available_dms = self._detect_available_dms()
        result["available"] = available_dms

        # Check active DM with fallbacks
        active_dm = self._detect_active_dm_with_fallback(available_dms)
        if active_dm:
            result["active"] = active_dm

        return result

    def _detect_available_dms(self):
        """Detect available display managers using multiple reliable methods"""
        available = []

        # Method 1: Check systemd unit files
        systemd_units = [
            ("lightdm", "lightdm.service"),
            ("gdm", "gdm.service"),
            ("gdm", "gdm3.service"),
            ("sddm", "sddm.service")
        ]

        for dm_name, unit_name in systemd_units:
            if self._check_systemd_unit_exists(unit_name):
                if dm_name not in available:
                    available.append(dm_name)

        # Method 2: Check binary availability as fallback
        binary_checks = [
            ("lightdm", ["lightdm"]),
            ("gdm", ["gdm", "gdm3"]),
            ("sddm", ["sddm"])
        ]

        for dm_name, binaries in binary_checks:
            if dm_name not in available:
                if any(shutil.which(binary) for binary in binaries):
                    available.append(dm_name)

        return available

    def _detect_active_dm_with_fallback(self, available_dms):
        """Detect active DM with multiple fallback methods"""
        # Primary method: systemd D-Bus
        active_dm = self._check_systemd_dm()
        if active_dm:
            return active_dm

        # Fallback 1: Check running processes
        active_dm = self._check_running_processes(available_dms)
        if active_dm:
            return active_dm

        # Fallback 2: Check display manager symlink
        active_dm = self._check_display_manager_symlink()
        if active_dm:
            return active_dm

        return None

    def _check_systemd_unit_exists(self, unit_name):
        """Check if systemd unit exists without requiring D-Bus"""
        unit_paths = [
            f"/etc/systemd/system/{unit_name}",
            f"/usr/lib/systemd/system/{unit_name}",
            f"/lib/systemd/system/{unit_name}"
        ]
        return any(os.path.exists(path) for path in unit_paths)

    def _check_running_processes(self, available_dms):
        """Check running processes for display manager indicators"""
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                proc_name = proc.info['name'].lower()
                for dm in available_dms:
                    if dm in proc_name:
                        return dm
        except (ImportError, psutil.NoSuchProcess):
            pass
        return None

    def _check_display_manager_symlink(self):
        """Check /etc/systemd/system/display-manager.service symlink"""
        symlink_path = "/etc/systemd/system/display-manager.service"
        if os.path.islink(symlink_path):
            target = os.readlink(symlink_path)
            for dm in ["lightdm", "gdm", "sddm"]:
                if dm in target:
                    return dm
        return None

    def _check_systemd_dm(self):
        """
        Check active display manager via systemd D-Bus API with improved error handling.
        Returns dm name (lightdm/gdm/sddm) or None if not active.
        """
        try:
            dm_unit = systemd_unit("display-manager.service", 1)
            state = dm_unit._get_state()
            if state in ("active", "activating"):
                unit_path = str(dm_unit.unit)  # D-Bus object path, e.g. /org/.../lightdm_2eservice
                # More robust DM name extraction
                dm_mapping = {
                    "lightdm": "lightdm",
                    "gdm": "gdm",
                    "sddm": "sddm"
                }
                for key, dm_name in dm_mapping.items():
                    if key in unit_path.lower():
                        return dm_name
        except Exception as exc:
            self.log("D30", {"unit": "display-manager.service", "error": str(exc)})
        return None

    def run(self):
        """
        Main plugin execution method with improved error handling and validation.
        Detects active display manager and applies configuration.
        """
        self.log("I3")

        try:
            # Validate configuration before proceeding
            if not self._validate_configuration():
                self.log("W11")
                return False

            # Detect available and active display managers
            dm_info = self.detect_dm()
            self.log("D30", {"dm_info": dm_info})

            if not dm_info["available"]:
                self.log("W10")
                return False

            # Use active DM or first available
            target_dm = dm_info["active"] or (dm_info["available"][0] if dm_info["available"] else None)

            if not target_dm:
                self.log("W10")
                return False

            # Determine config directory based on DM
            config_dir = self._get_config_directory(target_dm)
            if not config_dir:
                self.log("E22", {"dm": target_dm})
                return False

            # Generate configuration
            result = self.write_config(target_dm, config_dir)

            if result:
                self.log("I4", {"dm": target_dm, "config_dir": config_dir})
                return True
            else:
                self.log("E23", {"dm": target_dm, "config_dir": config_dir})
                return False

        except Exception as exc:
            self.log("E24", {"error": str(exc)})
            return False

    def _validate_configuration(self):
        """Validate DM configuration before applying"""
        # Check if we have background configuration to apply
        return bool(self.dm_config["Greeter.Background"])

    def _get_config_directory(self, dm_name):
        """Get configuration directory for display manager with fallbacks"""
        config_dirs = {
            "lightdm": ["/etc/lightdm/lightdm.conf.d", "/etc/lightdm"],
            "gdm": ["/etc/gdm/custom.conf.d", "/etc/gdm"],
            "sddm": ["/etc/sddm.conf.d", "/etc/sddm"]
        }

        dirs = config_dirs.get(dm_name, [])
        for config_dir in dirs:
            if os.path.exists(config_dir):
                return config_dir

        # If no existing directory, use the primary one
        return dirs[0] if dirs else None


def create_machine_applier(dict_dconf_db, username=None, fs_file_cache=None):
    """Factory function to create DMApplier instance"""
    return DMApplier(dict_dconf_db, username, fs_file_cache)


def create_user_applier(dict_dconf_db, username=None, fs_file_cache=None):
    """Factory function to create DMApplier instance"""
    pass
