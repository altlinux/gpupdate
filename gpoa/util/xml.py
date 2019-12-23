from xml.etree import ElementTree

def get_xml_root(xml_file):
    '''
    Get top-level element of XML file from disk.
    '''
    xml_contents = ElementTree.parse(xml_file)
    xml_root = xml_contents.getroot()

    return xml_root

