import xml.etree.ElementTree as ET

# Switch To BlackList After Testing (ex. Notes Section)
section_whitelist = ["medication", "allerg", "problem", "immunization", "laboratory"]

# TODO
# HISTORY OF PAST ILLNESSS (Resolved Problems) => Skipped
# Normalize and refactor parsers to be more flexible with node locations


def main():
    tree = ET.parse('Input.XML')
    root = tree.getroot()
    parser_version = root.find('./author//*/manufacturerModelName').text
    # Grab EHR and version of C-CDA Generator
    print("VERSION: " + parser_version + '\n')
    section_base_roots = root.findall('./component/structuredBody/component/section')
    section_nodes = []

    for element in section_base_roots:
        element_name = element.find('./code').attrib['displayName'].lower()
        if whitelisted_name(element_name):
            section_nodes.append(Sections(element_name, element.find('./text'), element))

    # test = section_nodes[1].entry_root.findall('./entry/')
    # MAKE CASE FOR NO /LIST
    for section in section_nodes:
        print("STARTING SECTION: " + section.name)
        if 'medicat' in section.name:
            medications_get(section)
        elif 'problem' in section.name:
            problems_get(section)
        elif 'immunization' in section.name:
            immunizations_get(section)
        elif 'laboratory' in section.name:
            labs_get(section)
        else:
            print("Error: " + section.name + " has not implemented yet and/or matching did not catch the section")
    # TODO: Add Method To Print Results (HTML Or Through Console)
    print("COMPLETED")


############################
#   MAIN PARSERS METHODS   #
############################

# History of Medication use Narrative
def medications_get(section):
    for item in section.text_root.findall('./list/'):
        new_item = SectionItem()
        for contents in item.findall('./content'):
            if len(contents.attrib) > 0:
                new_item.ref_id = contents.attrib['ID']
                new_item.name = contents.text
            else:
                new_item.date = contents.text
        new_item.additional_info.append(SigCodes(item.find('./paragraph').text))
        section.items.append(new_item)
    # NOW LOOK AT ENTRY SECTION
    for entry in section.entry_root.findall('./entry/'):
        # USING Medical reference (ex. '#med5')
        compare_ref = str.replace(entry.find('./consumable/manufacturedProduct/manufacturedMaterial/code/originalText/')
                                  .attrib['value'], '#', '', 1)
        # Get Med From Text Section That Is Referenced By Entry
        new_item = get_ref_idx(section, compare_ref)
        # START DATE (If Text Section Was Empty (Do Compare jik))
        if new_item.date == '':
            for times in entry.findall('./effectiveTime//'):
                if hasattr(times, 'value') and times.tag == 'low':
                    new_item.date = times.attrib['value']
        # GET RxNorm
        base_code = entry.find('./consumable/manufacturedProduct/manufacturedMaterial/code')
        new_item.code = base_code.attrib['code'] if 'code' in base_code.attrib else 'ERROR'
    return section


# Problem list - Reported
def problems_get(section):
    # TEXT SECTION
    for item in section.text_root.findall('./list/'):
        new_item = SectionItem()
        new_item.ref_id = item.find('./').attrib['ID']
        new_item.name = item.find('./').text
        new_item.date = item.find('./').tail
        section.items.append(new_item)
    # ENTRY SECTION (Refactor To Loop Through)
    for entry in section.entry_root.findall('./entry'):
        compare_ref = str.replace(entry.find('./act/entryRelationship/observation/text/reference').attrib['value'],
                                  '#', '', 1)
        # TEST CASE: Maybe Not All Would Have A text == entry equivalent?
        # Get Item From Text Section That Matches Current Entry Section
        new_item = get_ref_idx(section, compare_ref)
        # GET CODE(s), Set ICD9 into main object 'code'
        codes_base = entry.find('./act/entryRelationship/observation/value')
        code_obj = ProblemCodes()
        code_obj.snomed = codes_base.attrib['code']
        for codes in codes_base.findall('./translation'):
            if 'codeSystemName' in codes.attrib:
                if 'ICD9' == codes.attrib['codeSystemName']:
                    new_item.code = codes.attrib['code']
                elif 'ICD10' == codes.attrib['codeSystemName']:
                    code_obj.icd10 = codes.attrib['code']
        new_item.additional_info.append(code_obj)
    return section


# HISTORY OF PAST ILLNESS
def illnesses_get(section):
    return 0


# History of Immunization Narrative
def immunizations_get(section):
    for item in section.text_root.findall('./list/'):
        new_item = SectionItem()
        new_item.ref_id = item.find('./').attrib['ID']
        new_item.name = item.find('./').text
        new_item.date = item.find('./').tail
        section.items.append(new_item)
    # Could Compare Dates, Or Pull Immunization Manufactured (But Not Needed For Patient Perspective)
    for entry in section.entry_root.findall('./entry/substanceAdministration'):
        test = entry.find('./consumable//code')
        if test is not None and 'code' in test.attrib:
            compare_ref = str.replace(entry.find('.//originalText/reference').attrib['value'], '#', '', 1)
            item_ref = get_ref_idx(section, compare_ref)
            item_ref.code = test.attrib['code']
    return section


# Relevant diagnostic tests/laboratory data Narrative
def labs_get(section):
    # Try to separate narrative by title
    for item in section.text_root.findall('./list/'):
        new_item = SectionItem()
        caption_name = str(item.find('./caption').text).split('-')
        new_item.name = caption_name[0]
        # TODO: Use Regex Here (Currently 're' method names that would conflict with ElementTree)
        new_item.date = caption_name[1].split('(', 1)[-1].strip(')')
        # Key == Thead, Value == TBody
        table_info = dict()
        for table in item.findall('./table'):
            t_heads = table.findall('./thead/tr/th')
            t_body_tr = table.findall('./tbody/tr')
            rows_info = []
            for row in t_body_tr:
                if new_item.name == 'HEMOGLOBIN A1C':
                    a = 1
                for index, element in enumerate(row.findall('./td')):
                    td_elements = element.findall('.//')
                    summary = ''
                    # <paragraph/> == New Section Of Narrative
                    # TODO: Split Narrative Into Sections
                    for info in td_elements:
                        summary += info.text if info.text is not None else '\n'
                    table_info[t_heads[index].text] = summary if summary != '\n' else ''



        new_item.additional_info.append(table_info)
        section.items.append(new_item)
        a =1
    return section


##################
#   EXTENSIONS   #
##################

# Returns text section item of entry section item
def get_ref_idx(section, entry_ref_id):
    for item in section.items:
        if entry_ref_id == item.ref_id:
            return item


# Returns name if in whitelist
def whitelisted_name(section_name):
    for approved in section_whitelist:
        if approved in section_name:
            return True
    # If its not in list
    return False


def fill_section_items(sectionobj):
    return 0


# Weight/Keyword System For Pulling Individual Sig Codes From Description
def sig_parse(sig_str):
    return ['', '', '']


##############
#   MODELS   #
##############

# _root(tree Element): Pointer for xml section node
class Sections:
    def __init__(self, name, text_root, entry_root):
        self.name = name
        self.text_root = text_root
        self.entry_root = entry_root
        self.items = []

    def __getitem__(self, item):
        return self.items[item]


class SectionItem:
    def __init__(self):
        self.ref_id = ""
        self.name = ""
        self.code = ""
        self.date = ""
        self.additional_info = []


class SigCodes:
    def __init__(self, text_value, sig1='', sig2='', sig3=''):
        if text_value is None:
            self.sig1 = sig1
            self.sig2 = sig2
            self.sig3 = sig3
        # Make A Weighting System For Determining Sig Codes
        else:
            text_value = sig_parse(text_value)
            self.sig1 = text_value[0]
            self.sig2 = text_value[1]
            self.sig3 = text_value[2]


class ProblemCodes:
    def __init__(self, icd10='', snomed=''):
        self.icd10 = icd10
        self.snomed = snomed


# LAB MODELS
# TODO: Find Way To Determine Type Of Lab
class LabTableInfo:
    def __init__(self):
        self.Information = dict([])


# Lazy Start
main()
