#!/usr/bin/python3

#Script for parsing the chrome.admx or the Yandex Browser.admx file
#into the number of keys needed to be treated as an integer

import sys
from xml.etree import ElementTree


def get_child(parent, desires:list, list_data_pol:list):
    if parent.tag == 'decimal':
        list_data_pol.append(parent.get('value'))
        return
    for child in parent:
        if child.tag == desires[0]:
            get_child(child, desires[1:], list_data_pol)

if __name__ == '__main__':
    try:
        try:
            xml_contents = ElementTree.iterparse(sys.argv[1])
        except:
            print('Enter the correct file path')
            sys.exit()

        #Ignore XML file namespace
        for _, el in xml_contents:
            prefix, has_namespace, postfix = el.tag.partition('}')
            if has_namespace:
                el.tag = postfix

        xml_root = xml_contents.root
        pol_count = 0
        dict_policies = dict()
        for parent in xml_root:
            if parent.tag == 'policies':
                for child in parent:
                    pol_count += 1
                    dict_policies[child.get('name')] = list()
                    desires = ['elements', 'enum', 'item', 'value', 'decimal']
                    get_child(child, desires, dict_policies[child.get('name')])

        target_list = list()
        count = 0
        len_dict = len(set([key if val else None for key,val in dict_policies.items()])) - 1
        for key, value in dict_policies.items():
            if value:
                target_list.append(key)
                count+=1
                key_int = "'{}'".format(key)
                if len_dict > count:
                    key_int += ','
                else:
                    print(key_int, '\n\nkey_int:', count)
                    break
                print(key_int)

        print('total:',pol_count)

    except Exception as exc:
        print(exc)
