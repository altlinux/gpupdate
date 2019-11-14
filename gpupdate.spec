%define _unpackaged_files_terminate_build 1

Name: gpupdate
Version: 0.0.1
Release: alt1

Summary: GPT applier
License: MIT
Group: Other
Url: http://git.altlinux.org/
BuildArch: noarch

Requires: hreg
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
mkdir -p \
	%buildroot%prefix/libexec
cp -r gpoa \
	%buildroot%prefix/libexec

%files
%prefix/bin/gpupdate
%prefix/libexec/gpoa

%changelog
* Thu Nov 14 2019 Igor Chudov <nir@altlinux.org> 0.0.1-alt1
- Initial release

