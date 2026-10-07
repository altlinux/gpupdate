# Production regression checks

Run these scenarios on disposable domain clients before deploying the fixes.
Unit tests cover controlled failures and successful paths; the checks below
exercise distribution services, credentials and package transactions.

## Baseline and upgrade

- Record the selected backend, local-policy template, active timers, policy
  databases and generated configuration before upgrading.
- Upgrade enabled Samba, FreeIPA and local installations with custom templates.
  An unqualified `gpupdate-setup update` must preserve their source selection.
- Test explicit backend/template overrides separately.
- Install `gpoa-lib` alone and render Polkit and CIFS templates. Upgrade a full
  installation across the template ownership change and verify package removal
  does not remove templates still owned by the library.

## Identity, privileges and credentials

- An unresolved user, and an explicit UID-zero user target, must fail before any
  machine policy database is modified. Valid domain users retain separate DBs.
- For each polkit verdict, configure multiple actions for one user. Check the
  first and last action as both that user and a different user, while retaining
  a conflicting machine-policy case.
- Interrupt the ordinary client with an existing user TGT. That TGT must remain
  usable. Separately interrupt machine credential acquisition and command
  execution; only the wrapper/engine-owned cache may be removed.
- Return a multi-megabyte user plugin result. The update must finish, the full
  result must arrive, and the worker must be reaped. Follow a failing plugin with
  a healthy plugin and check that the latter still executes.
- Inject a local LAPS password-change failure after LDAP success. The local
  success marker and post-actions must not advance. The next run must retry even
  when LDAP already holds the new expiration time. Pending state contains no
  password and is removed only after local success.

## Files and preferences

- Test symlinks and hard links at environment output paths; unrelated target
  files must remain unchanged. Disabled appliers must not truncate output.
- Exercise all folder deletion flags with nested and broken symlinks. Files
  outside the selected tree must survive both Replace and remove-policy cleanup.
- Keep both visible and hidden siblings; cleanup must remove only the actual
  managed target. Include directory and wildcard Files destinations.
- Copy `*.pub` from a directory also containing private files. Only matching
  regular files may be selected. Repeat using an SMB source.
- Update a file in a root-owned external directory using user Files policy.
  Directory ownership must remain unchanged; in-home ownership must still work.
- Fail replacement acquisition and confirm the old file remains. After source
  recovery, the operation must retry and complete with the expected permissions.
- Apply once-only Folder Replace, INI and Environment entries, add sentinel
  content, then perform two further refreshes. The sentinel and once-only values
  must survive, including root-driven user updates crossing the fork boundary.
- Remove the policy and verify its configured removal behaviour separately.
- Disable machine and user CIFS appliers independently with working maps already
  present. Their maps must survive; enabled removal of the last drive still
  removes the appropriate maps. Requester Kerberos authentication is unchanged.

## Retrieval, ordering and cached application

- Give two GPOs equal display names and versions but different identifiers and
  values. Each must use its own content; renaming must not change identity.
- Compare FreeIPA cold, warm and mixed caches. Effective order must be identical.
- Inject discovery, RPC, directory-listing, file-transfer and parsing failures.
  No partial snapshot/version may be accepted and no removal cleanup may run.
- After a successful update removing a server-side XML file, verify it is absent
  from the new snapshot. Retained older snapshots must not be selected as current.
- Run overlapping updates/readers and verify each reader sees a complete
  snapshot. Monitor disk usage: old immutable snapshots are currently retained.
- Check loopback modes 0/1/2 with shared and disjoint user/computer chains. In
  Merge, the computer-linked occurrence wins; test GPP side effects as well as
  registry values.
- Exercise `--noupdate` with and without a cache, targeting machine and user
  policy. No retrieval or refreshed database save may occur. Confirm targeting
  filters and existing apply-once markers still work.

## Services and operational results

- Return failed and successful oddjob replies for combined targets. Both targets
  must be attempted; the CLI must report a failure when either execution fails.
- Run failing and successful scripts in sequence. Later scripts must run and
  failures must be visible. Verify strict exit mode separately; default units
  must still execute their shutdown/logoff actions.
- Disable periodic updates with multiple sessions and lingering user managers.
  Timers must stop without killing an ongoing update or invoking script stop
  actions. An inaccessible user manager must be reported.
- Compare native DWORD and legacy string enablement for experimental Firewall
  and NTP appliers. Keep their enablement defaults unchanged.
- Apply lock-only GSettings changes through the standalone API and check actual
  writability after each transition. Repeat through the normal controller.

## Desktop and browser follow-up checks

- For #60718, apply user KDE settings before the graphical session is ready and
  from the periodic user service on KDE 5 and 6. Verify the configured values in
  `~/.config/kwinrc`. Version detection must not require DISPLAY, alter the parent
  environment, or report successful application when the writer fails. Test
  missing `kinfo` with one available writer and an ambiguous dual-writer install.
- For #56019, create, update and replace a user desktop shortcut on GNOME and
  XFCE 4.20, including first login with a new home. Check executable permissions,
  `metadata::trusted` and `metadata::xfce-exe-checksum` in the user's GVFS store,
  and launch the shortcut from the desktop. XFCE's checksum must match the final
  file contents. A Create operation that leaves an existing modified shortcut
  untouched must not mark that file trusted. Missing metadata support must not
  prevent the shortcut from being written; inspect the diagnostic in that case.
- For #60563, enable machine-shortcut merging into user policy. Verify Icon,
  Comment, URL versus application type, targeting filters, disabled state and
  apply-once behaviour. Do not copy the machine's application stamp to the user.
- For #47135, configure an absolute local script path containing mixed case and
  spaces. Check its cached contents, mode and arguments, then its execution at
  the existing startup/shutdown or logon/logoff event. Test relative GPT scripts
  alongside it. Policy application itself must not execute the script.
- For #46281, check managed and recommended ExtensionSettings in both Chromium
  and Yandex. Include JSON objects with true, false, null, nested arrays, escaped
  backslashes and Unicode. Start with an actual REG_SZ in Registry.pol: testing
  only the browser applier bypasses ingestion and can miss damaged quoting.
  Check the current and Previous values after dconf compilation/readback, then
  the browser policy value and status. Existing registry-subkey lists, boolean
  DWORDs and integer exceptions must retain their types. A previously damaged
  cached value needs a normal policy refresh from Registry.pol; do not attempt
  to repair it by replacing quotes in the cached text.

## Yandex numeric policy values

- Start with DWORD values in Registry.pol and compare them with the generated
  JSON and `browser://policy`. Cover these numeric values:
  `YandexLoginAllowedDomainsForceLogoutMaxDelay`, `BrowserSwitcherDelay`,
  `PolicyRefreshRate`, `CloudReportingUploadFrequency`,
  `YandexClipboardMaxImageSize`, `YandexClipboardMaxTextSize`,
  `MaxConnectionsPerProxy`, `IntranetRedirectBehavior` and `ImportFrom`.
- Test zero and one where valid, plus a larger documented value. Numeric zero
  and one must remain JSON numbers, not false and true; larger values must not
  become null. Keep boolean controls such as VideoCaptureAllowed boolean and
  existing exceptions such as DiskCacheSize and DownloadRestrictions numeric.
- Use valid values and supported browser versions for browser acceptance:
  ImportFrom requires version 26.6.4 or later, and some policies require the
  extended corporate edition. Check recommended output only where the browser
  supports that policy as recommended. Serialization tests alone do not prove
  support in an older browser or another edition.

## Packaged display-manager plugin

- With no external plugins directory, enable `GPUpdate/Plugins` and configure
  `DisplayManager/Greeter.Background`. The packaged `DMApplier` must be discovered
  once in machine context. Verify the existing `PluginsList` allowlist, disabled
  plugins, and precedence of an installed external replacement. Discovery alone
  must not download the background or modify display-manager files.
- Test a readable absolute local background and a UNC source. An unavailable
  source must fail without replacing the working theme or using a stale cached
  download. An unconfigured background must be skipped.
- First test GDM generation on a copy of the installed resource. Compare the full
  resource entry list, nested aliases and binary contents. Check light, dark and
  supported high-contrast CSS independently; file URLs must encode spaces and
  special characters correctly. Confirm resource ownership and mode survive.
- Repeat application within the same theme generation and verify that its
  `.backup` remains unchanged.
  Inject compilation and publication failures, then exercise `backup` restoration.
  Unsupported themes and invalid backups must report failure rather than claim
  success through an ineffective GDM configuration key.
- The updater does not restart GDM or terminate graphical sessions. Schedule a
  separate login-screen test after package installation to verify the visible
  background and access to the image by the greeter. Keep a console recovery
  session available for that deployment test. Check LightDM and SDDM separately
  where deployed; a successful resource-copy test only validates the GDM path.
- For LightDM, test GTK, Slick, KDE Wayland and the KDE X11 session alias. Compare
  detection with `lightdm --show-config` and the greeter desktop alternatives in
  both `lightdm/greeters` and `xgreeters`. A `greeter-session-fallback` entry must
  not select the main greeter. Verify vendor/local drop-in ordering and the final
  main configuration override; conflicting per-seat greeters must not be guessed.
- Start with a copy of the old `50-custom.conf` containing `["Seat:*"]` and quoted
  keys. Applying the policy must produce `[Seat:*]` and native INI keys/values,
  preserving other settings, comments, ownership and mode. Check each greeter's
  own background section, repeated application and failed publication. Preserve
  KDE theme selection and Slick's existing `draw-user-backgrounds` setting. An
  unknown greeter must fail without creating a guessed GTK configuration.

## Review follow-up regressions

- Apply a wildcard Files preference into a directory containing an unrelated
  matching file and a pre-existing Create destination. Remove the preference:
  only successfully managed, recorded destinations may be removed. Legacy
  wildcard state without a manifest must defer cleanup. Delete must still work
  when its unused UNC source is unavailable. Folder Delete/Replace must reject
  an ordinary file at the directory target without deleting it.
- Move an apply-once preference between GPOs while retaining its item UID. A
  different policy GUID must not inherit the old application stamp. For merged
  machine shortcuts, verify three user refreshes and two distinct users:
  per-user stamps survive serialization/IPC and do not become machine stamps.
- Fail LDAP and local password updates during a post-login LAPS rotation. The
  eventual successful retry must retain the configured post-action; an
  expiration-only retry must not acquire that action. Pending state contains
  only the post-action flag, never the password.
- Return a large user-plugin result, then repeat with a fork descendant holding
  the IPC writer after the worker exits. Framed JSON must complete without EOF;
  truncated frames must fail. The supported payload limit is 64 MiB. Verify
  plugin continuation followed by a failed engine status and strict script
  failure when its arguments cannot be loaded; default script exit semantics
  remain unchanged.
- Cancel a machine command whose children ignore SIGTERM. Its owned process
  group must stop before credential cleanup, including background children
  after normal command completion. Commands deliberately creating independent
  sessions are outside this process-group contract.
- Test LightDM alias groups in native file/group order, including a later
  SeatDefaults override. A repaired quoted greeter-session must select the
  planned greeter, not the old one. Preparation or second-file publication
  failure must preserve both existing configurations.
- Include ordinary payloads named Files.xml, Registry.pol and scripts.ini below
  GPT script directories. FreeIPA validates only real policy locations; script
  validation must not consume execution-order counters.
- Inject browser conversion, staged-write and second-file publication failures.
  Both managed and recommended policy files must retain their old contents.
  Related-file publication uses per-file atomic replacements and rollback;
  this is not a crash-atomic multi-file filesystem transaction.
- Apply a GDM background to V1, simulate an RPM theme replacement with V2,
  reapply and restore. Restore must select the V2 baseline, not an old V1 backup.
  Refuse an unverified legacy/cross-generation restore until a current baseline
  has been established. Keep historical backups separate from the active one.

## Validation scope on the domain stand

The follow-up candidate was tested separately from installed packages on a
Samba-domain Workstation p11 with LightDM/KDE and an active domain user. The
library suite and a broad applier matrix exercised non-empty settings and fault
fixtures. Actual operations included privilege dropping/private D-Bus,
headless KDE detection, native KDE configuration in temporary files, LightDM
configuration copies, GLib resource compilation, dconf round trips and harmless
process-tree termination. CUPS, service, firewall, package, LDAP/password and
PAM-changing operations were mocked. GDM, SDDM, Yandex and XFCE were not installed
there. These checks do not replace full GPO delivery, visual login-screen,
FreeIPA-server, reboot/logoff or installed-RPM transaction acceptance tests.
