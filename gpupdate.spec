%define _unpackaged_files_terminate_build 1

Name: gpupdate
Version: 0.0.2
Release: alt1

Summary: GPT applier
License: MIT
Group: Other
Url: http://git.altlinux.org/
BuildArch: noarch

Requires: control
Requires: samba-dc

Source0: %name-%version.tar

%description
GPT applier

%prep
%setup -q

%install
install -pD -m755 gpupdate \
	%buildroot%_bindir/gpupdate
mkdir -p %buildroot/var/cache/samba
install -pD -m644 gpoa/cache.pkl \
	%buildroot/var/cache/samba
install -pD -m644 gpoa/sid_cache.pkl \
	%buildroot/var/cache/samba
mkdir -p \
	%buildroot%prefix/libexec
cp -r gpoa \
	%buildroot%prefix/libexec

%files
%prefix/bin/gpupdate
%prefix/libexec/gpoa
/var/cache/samba/cache.pkl
/var/cache/samba/sid_cache.pkl

%changelog
* Fri Nov 15 2019 Igor Chudov <nir@altlinux.org> 0.0.2-alt1
- Removed hreg dependency
- Introduced caches for SIDs and Registry.pol file paths
- gpupdate transformed into simple gpoa starter
- gpoa learned to work with username
- Introduced TDB manager in order to work with samba-regedit registry
- DC domain detection now uses native python-samba functions to query LDAP

* Thu Nov 14 2019 Igor Chudov <nir@altlinux.org> 0.0.1-alt1
- Initial release

