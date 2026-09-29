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
  backslashes and Unicode. Verify the resulting policy in the browser, not only
  the JSON file. Existing registry-subkey lists, boolean DWORDs and integer
  exceptions must retain their types.
