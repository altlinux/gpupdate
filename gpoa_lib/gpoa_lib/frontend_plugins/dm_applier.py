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
import shlex
import stat
import tempfile
from pathlib import Path

# Import only what's absolutely necessary
try:
    from gpoa_lib.frontend.appliers.systemd import systemd_unit
except ImportError:
    systemd_unit = None

try:
    from gpoa_lib.util.gpoa_ini_parsing import GpoaConfigObj
except ImportError:
    GpoaConfigObj = None

from gpoa_lib.plugin.plugin_base import FrontendPlugin
from ..util.logging import log
from ..applier_result import ApplierResult, ItemStatus, RESULT_SUCCESS
from .gdm_resource import apply_background, restore_background


if GpoaConfigObj is not None:
    class _LightDMConfig(GpoaConfigObj):
        """GLib/KConfig INI values are not ConfigObj lists or quoted strings."""

        def _handle_value(self, value):
            # Also repair quoting written by earlier DMApplier versions.
            value = value.strip()
            return self._unquote(value) if value else '', ''

        def _quote(self, value, multiline=True):
            if not isinstance(value, str) or any(c in value for c in '\r\n\x00'):
                raise ValueError('Invalid LightDM INI value')
            return value


    class _LightDMReadConfig(_LightDMConfig):
        """Read the active native INI literally, without repairing its meaning."""

        def _unquote(self, value):
            # LightDM does not treat ["Seat:*"] as [Seat:*], or strip quotes
            # around a greeter-session value. Repair belongs to the write path.
            return value


class DMApplier(FrontendPlugin):
    """
    Display Manager Applier - handles loading of display manager policy keys
    from registry (machine/user) and user preferences.

    Also includes DMConfigGenerator functionality for display manager configuration.
    """

    __registry_path = 'Software/BaseALT/Policies/DisplayManager'
    domain = 'dm_applier'
    LIGHTDM_CONFIG_DIRS = (
        '/usr/share/lightdm/lightdm.conf.d',
        '/usr/local/share/lightdm/lightdm.conf.d',
        '/etc/xdg/lightdm/lightdm.conf.d',
        '/etc/lightdm/lightdm.conf.d',
    )
    LIGHTDM_CONFIG_FILE = '/etc/lightdm/lightdm.conf'
    LIGHTDM_GREETER_DIRS = (
        '/usr/local/share/lightdm/greeters', '/usr/share/lightdm/greeters',
        '/usr/local/share/xgreeters', '/usr/share/xgreeters',
    )
    LIGHTDM_GREETER_CONFIGS = {
        'lightdm-gtk-greeter': ('/etc/lightdm/lightdm-gtk-greeter.conf', 'greeter', 'background'),
        'slick-greeter': ('/etc/lightdm/slick-greeter.conf', 'Greeter', 'background'),
        'lightdm-kde-greeter': ('/etc/lightdm/lightdm-kde-greeter.conf', 'lightdm_theme_userbar', 'Background'),
        'lightdm-kde-greeter-x11': ('/etc/lightdm/lightdm-kde-greeter.conf', 'lightdm_theme_userbar', 'Background'),
    }

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
                    6: "GDM theme modified successfully",
                    7: "GDM backup restored successfully",
                    8: "GDM fallback configuration generated successfully"
                },
                'w': {
                    10: "No display managers detected",
                    11: "No background configuration to apply",
                    12: "GDM backup file not found",
                    13: "Backup mode only supported for GDM"
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
                    28: "Failed to recompile GDM gresource",
                    29: "Failed to restore GDM backup",
                    30: "Failed to add GDM background"
                },
                'd': {
                    30: "Display manager detection details",
                    31: "Display manager configuration details",
                    32: "Removed empty configuration value",
                    33: "GDM background modification details",
                    34: "GDM backup operation details",
                    35: "GDM CSS file not found",
                    36: "GDM background pattern analysis",
                    37: "GDM background added to CSS"
                }
            },
            # locale_dir will be set by plugin_manager during plugin loading
            domain="dm_applier"
        )

        self.config = self.get_dict_registry(self.__registry_path)

        # DMConfigGenerator configuration - only background settings
        background_path = self.config.get("Greeter.Background", None)
        self.backup = background_path == 'backup'
        self.background_source = background_path
        self.file_cache = fs_file_cache
        self.dm_config = {"Greeter.Background": ''}

        self.log("I1")  # Display Manager Applier initialized

    @classmethod
    def _get_plugin_prefix(cls):
        """Return plugin prefix for translation lookup."""
        return "dm_applier"

    def _prepare_conf(self, path, lightdm=False):
        """
        Load existing file or create new, preserving all comments and structure.
        """
        try:
            if lightdm:
                conf = _LightDMConfig(path, encoding='utf-8', create_empty=True,
                                      list_values=False, interpolation=False)
            else:
                conf = GpoaConfigObj(path, encoding="utf-8", create_empty=True)
            return conf
        except Exception as exc:
            self.log("E20", {"path": path, "error": str(exc)})
            return None

    def _write_lightdm_conf(self, conf):
        """Publish a complete INI without truncating the previous working file."""
        path = os.path.realpath(conf.filename)
        previous = os.stat(path) if os.path.exists(path) else None
        if previous is not None and not stat.S_ISREG(previous.st_mode):
            raise ValueError('LightDM configuration is not a regular file')
        fd, temporary = tempfile.mkstemp(prefix='.gpupdate-', dir=os.path.dirname(path))
        try:
            with os.fdopen(fd, 'wb') as output:
                conf.write(output)
                if previous is not None:
                    os.fchown(output.fileno(), previous.st_uid, previous.st_gid)
                os.fchmod(output.fileno(), stat.S_IMODE(previous.st_mode) if previous else 0o644)
                output.flush()
                os.fsync(output.fileno())
            if previous is not None:
                shutil.copystat(path, temporary)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _prepare_background(self):
        """Resolve the source only when an enabled plugin is actually applied."""
        source = self.background_source
        if not isinstance(source, str) or not source.strip():
            raise ValueError('Invalid display manager background path')
        normalized = source.replace('\\', '/')
        if normalized.startswith('//'):
            if self.file_cache is None:
                raise ValueError('No file cache available for the background')
            self.file_cache.store(normalized, checked=True)
            normalized = self.file_cache.get(normalized)
        if not normalized or not os.path.isabs(normalized) or not Path(normalized).is_file():
            raise ValueError('Background is not an existing absolute file: {}'.format(normalized))
        # Check readability before touching any display-manager configuration.
        with open(normalized, 'rb') as background:
            background.read(1)
        self.dm_config['Greeter.Background'] = normalized

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

        conf = self._prepare_conf(path, lightdm=True)
        if conf is None:
            return None
        section = conf.setdefault("Seat:*", {})

        # Set values only if they have meaningful content (avoid writing empty values)
        if self.dm_config["Greeter.Background"]:
            section["greeter-background"] = self.dm_config["Greeter.Background"]

        # Comments example:
        if not conf.initial_comment:
            conf.initial_comment = ["# LightDM custom config"]
        try:
            self._write_lightdm_conf(conf)
            self.log("I2", {"path": path, "dm": "lightdm"})
            return conf
        except Exception as exc:
            self.log("E21", {"path": path, "error": str(exc)})
            return None


    def generate_gdm(self, path):
        """Generate GDM configuration by modifying gnome-shell-theme.gresource"""
        if self.backup:
            return self._restore_gdm_backup()
        if not self.dm_config["Greeter.Background"]:
            return False
        background_path = self.dm_config["Greeter.Background"]
        try:
            gresource_path = self._find_gnome_shell_gresource()
            if not gresource_path:
                self.log("E25", {"path": "gnome-shell-theme.gresource"})
                return False
            apply_background(gresource_path, background_path)
            self.log("I6", {"path": gresource_path, "background": background_path})
            return True
        except Exception as exc:
            self.log("E21", {"path": "gnome-shell-theme.gresource", "error": str(exc), "dm": "gdm"})
            return False

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

    def _restore_gdm_backup(self):
        """Restore GDM gresource from backup if available"""
        try:
            gresource_path = self._find_gnome_shell_gresource()
            if not gresource_path:
                self.log("E25", {"path": "gnome-shell-theme.gresource"})
                return False
            restore_background(gresource_path)
            self.log("I7", {"path": gresource_path})
            return True
        except Exception as exc:
            self.log("E29", {"path": "gnome-shell-theme.gresource", "error": str(exc)})
            return False

    def _generate_gdm_fallback(self, path, background_path):
        # GDM does not implement a [daemon] Background setting. Do not create
        # an ineffective configuration or report a resource failure as success.
        return False

    def generate_sddm(self, path):
        conf = self._prepare_conf(path)
        if conf is None:
            return None

        theme = conf.setdefault("Theme", {})
        # Set values only if they have meaningful content
        if self.dm_config["Greeter.Background"]:
            theme["Background"] = self.dm_config["Greeter.Background"]

        # Clean up empty values from all sections
        self._clean_empty_values(theme)

        conf.write()
        return conf

    def write_config(self, dm_name, directory):
        if self.backup and dm_name!='gdm':
            self.log("W13", {"dm": dm_name})
            return False

        greeter_name = None
        if dm_name == 'lightdm':
            greeter_name = self._detect_lightdm_greeter()
            if greeter_name not in self.LIGHTDM_GREETER_CONFIGS:
                self.log('E22', {'greeter': greeter_name})
                return False

        filename = os.path.join(directory, "50-custom.conf")
        gen = {
            "lightdm": self.generate_lightdm,
            "gdm": self.generate_gdm,
            "sddm": self.generate_sddm
        }.get(dm_name)
        if not gen:
            raise ValueError("Unknown DM: {}".format(dm_name))
        if dm_name != 'gdm':
            os.makedirs(directory, exist_ok=True)

        result = gen(filename)
        if result is None or result is False:
            return False

        # For LightDM, always generate greeter configuration if needed
        if dm_name == "lightdm":
            return self._generate_lightdm_greeter_config(greeter_name)

        return True

    def _detect_lightdm_greeter(self):
        """Read the configured main session in LightDM's configuration order."""
        paths = []
        for directory in self.LIGHTDM_CONFIG_DIRS:
            if os.path.isdir(directory):
                paths.extend(os.path.join(directory, name) for name in sorted(os.listdir(directory))
                             if name.endswith('.conf'))
        paths.append(self.LIGHTDM_CONFIG_FILE)
        conf = self._read_lightdm_conf()
        for path in paths:
            if os.path.exists(path):
                conf.merge(self._read_lightdm_conf(path))
        # Only the exact key applies: greeter-session-fallback is a different
        # session and must not override the primary (possibly Wayland) greeter.
        session = 'lightdm-default-greeter'
        for section in ('SeatDefaults', 'Seat:*'):
            if 'greeter-session' in conf.get(section, {}):
                session = conf[section]['greeter-session'].strip()
        overrides = {conf[section]['greeter-session'].strip()
                     for section in conf.sections
                     if section.startswith('Seat:') and section != 'Seat:*'
                     and 'greeter-session' in conf[section]}
        if overrides and overrides != {session}:
            # A shared greeter configuration cannot represent conflicting
            # per-seat themes. Do not guess a seat or modify the wrong greeter.
            self.log('E22', {'greeter': session, 'seat_overrides': sorted(overrides)})
            return None
        greeter = self._resolve_lightdm_session(session)
        self.log('D30', {'greeter': greeter, 'session': session, 'source': 'lightdm configuration'})
        return greeter

    @staticmethod
    def _read_lightdm_conf(path=None):
        conf = _LightDMReadConfig(path, encoding='utf-8', list_values=False,
                                  interpolation=False, file_error=True,
                                  allow_duplicate_sections=True, allow_duplicate_keys=True)
        if conf.scalars or any(conf[section].sections for section in conf.sections):
            raise ValueError('LightDM INI must contain flat sections')
        return conf

    def _resolve_lightdm_session(self, session):
        if not session or os.path.basename(session) != session:
            return None
        if session in self.LIGHTDM_GREETER_CONFIGS:
            return session
        for directory in self.LIGHTDM_GREETER_DIRS:
            desktop = os.path.join(directory, session + '.desktop')
            if not os.path.isfile(desktop):
                continue
            # Alternatives often point to a Wayland desktop whose Exec is a
            # compositor wrapper. Identify that desktop, never execute Exec.
            name = Path(os.path.realpath(desktop)).stem
            if name in self.LIGHTDM_GREETER_CONFIGS:
                return name
            entry = self._read_lightdm_conf(desktop)
            if 'Exec' in entry.get('Desktop Entry', {}):
                command = shlex.split(entry['Desktop Entry']['Exec'])
                if command and os.path.basename(command[0]) in self.LIGHTDM_GREETER_CONFIGS:
                    return os.path.basename(command[0])
            return session
        # Unknown/missing sessions are unsupported; no silent GTK fallback.
        return session

    def _generate_lightdm_greeter_config(self, greeter_name=None):
        """Generate configuration for the detected LightDM greeter"""

        # Only generate if we have background settings
        if not self.dm_config["Greeter.Background"]:
            return False

        if greeter_name is None:
            greeter_name = self._detect_lightdm_greeter()
        config_info = self.LIGHTDM_GREETER_CONFIGS.get(greeter_name)
        if not config_info:
            self.log("E22", {"greeter": greeter_name})  # Unknown greeter type
            return False

        config_path, section, background_key = config_info
        conf = self._prepare_conf(config_path, lightdm=True)
        if conf is None:
            return False

        # Get or create the greeter section
        greeter_section = conf.setdefault(section, {})

        # Apply background setting only if it has meaningful content
        if self.dm_config["Greeter.Background"]:
            greeter_section[background_key] = self.dm_config["Greeter.Background"]

        if not conf.initial_comment:
            conf.initial_comment = [f"# {greeter_name} custom config"]
        try:
            self._write_lightdm_conf(conf)
            self.log("I5", {"path": config_path, "greeter": greeter_name})
            return True
        except Exception as exc:
            self.log("E21", {"path": config_path, "error": str(exc)})
            return False

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
        except (ImportError, psutil.NoSuchProcess) as exc:
            log('D286', {'exc': str(exc)})
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
            if not self.background_source:
                self.log("W11")
                return ApplierResult.skipped(self.plugin_name, 'No background policy configured')

            # Detect available and active display managers
            dm_info = self.detect_dm()
            self.log("D30", {"dm_info": dm_info})

            if not dm_info["available"]:
                self.log("W10")
                return ApplierResult.failed(self.plugin_name, 'No display managers detected')

            # Use active DM or first available
            target_dm = dm_info["active"] or (dm_info["available"][0] if dm_info["available"] else None)

            if not target_dm:
                self.log("W10")
                return ApplierResult.failed(self.plugin_name, 'No target display manager')

            # Determine config directory based on DM
            config_dir = self._get_config_directory(target_dm)
            if not config_dir:
                self.log("E22", {"dm": target_dm})
                return ApplierResult.failed(self.plugin_name, 'Unknown display manager configuration directory')

            if not self.backup:
                self._prepare_background()
            # Generate configuration
            result = self.write_config(target_dm, config_dir)

            if result:
                self.log("I4", {"dm": target_dm, "config_dir": config_dir})
                return ApplierResult.applied(self.plugin_name, [ItemStatus(
                    key=target_dm, action='restore' if self.backup else 'set', result=RESULT_SUCCESS)])
            else:
                self.log("E23", {"dm": target_dm, "config_dir": config_dir})
                return ApplierResult.failed(self.plugin_name, 'Display manager configuration failed')

        except Exception as exc:
            self.log("E24", {"error": str(exc)})
            return ApplierResult.failed(self.plugin_name, str(exc))

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
