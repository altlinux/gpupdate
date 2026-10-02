#!/usr/bin/python3

#Script for parsing the chrome.admx or the Yandex Browser.admx file
#into the number of keys needed to be treated as an integer

import argparse
from xml.etree import ElementTree


def _children(parent, tag):
    """Select direct children regardless of the ADMX namespace."""
    return (child for child in parent if child.tag.rsplit('}', 1)[-1] == tag)


def extract_integer_values(root):
    """Return numeric DWORD value names and the total policy count.

    Direct decimal elements cover sizes and intervals. Enum decimal values
    cover numeric choices. Boolean enabled/disabled values are not exceptions.
    This is a candidate list: ADMX availability does not imply Linux support.
    """
    names = []
    seen = set()
    policy_count = 0
    for policies in _children(root, 'policies'):
        for policy in _children(policies, 'policy'):
            policy_count += 1
            for elements in _children(policy, 'elements'):
                for element in elements:
                    tag = element.tag.rsplit('}', 1)[-1]
                    numeric = tag == 'decimal'
                    if tag == 'enum':
                        numeric = any(
                            next(_children(value, 'decimal'), None) is not None
                            for item in _children(element, 'item')
                            for value in _children(item, 'value')
                        )
                    if not numeric:
                        continue
                    name = element.get('valueName') or policy.get('valueName')
                    if name and name not in seen:
                        seen.add(name)
                        names.append(name)
    return names, policy_count


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='List candidate numeric registry values from browser ADMX. '
                    'Verify Linux support before updating an applier.')
    parser.add_argument('admx', help='Path to chrome.admx or YandexBrowser.admx')
    args = parser.parse_args(argv)
    try:
        names, policy_count = extract_integer_values(ElementTree.parse(args.admx).getroot())
    except (OSError, ElementTree.ParseError) as exc:
        parser.exit(1, f'{args.admx}: {exc}\n')
    for index, name in enumerate(names):
        suffix = ',' if index < len(names) - 1 else ''
        print(repr(name) + suffix)
    print('\nkey_int:', len(names))
    print('total:', policy_count)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
