import xml.etree.ElementTree as ET
from xml.dom import minidom
import pandas as pd
import sys
import os
import csv
import xml.etree.ElementTree as ET

def read_tsv(file_path):
    with open(file_path, "r") as tsv_file:
        tsv_reader = csv.reader(tsv_file, delimiter='\t')
        sequences = [row[0] for i_row, row in enumerate(tsv_reader) if i_row > 0]
    return sequences

def write_xml(xml_string, output_file, add_header = True):
    with open(output_file, 'wb') as output_xml:
        if add_header:
            output_xml.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
        output_xml.write(xml_string)

def create_rfmap_xml(sequences, output_file = None, plate_type="P384"):
    rf_plate_map = ET.Element("RFPlateMap")
    rf_plate_map.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    rf_plate_map.set("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")

    file_name = ET.SubElement(rf_plate_map, "FileName")
    if output_file:
        file_name.text = output_file

    plate_type_element = ET.SubElement(rf_plate_map, "PlateType")
    plate_type_element.text = plate_type

    sequences_element = ET.SubElement(rf_plate_map, "Sequences")
    array_of_string = ET.SubElement(sequences_element, "ArrayOfString")

    for seq in sequences:
        seq_element = ET.SubElement(array_of_string, "string")
        seq_element.text = seq

    xml_string = ET.tostring(rf_plate_map, encoding="utf-8", method="xml")

    if output_file:
        write_xml(xml_string, output_file, add_header = True)

    return(xml_string)


def prettify(elem):
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')
    out_s = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
    return (out_s)



def create_rfbat_file(rfmap_filename, rfcfg_filename, rfbat_filename, ms_method, column_type, sequence_name, plate_name, cal_method):
    
    rfcfg_tree = ET.parse(rfcfg_filename)
    rfcfg_data = rfcfg_tree.getroot()

    rfmap_tree = ET.parse(rfmap_filename)
    rfmap_data = rfmap_tree.getroot()
    sequences_element = rfmap_data.find('Sequences')
    rfmap_injections = []
    for string_element in sequences_element.findall('.//string'):
        rfmap_injections.append(string_element.text)
    mapping_file = os.path.basename(rfmap_filename)


    rfbatch = ET.Element('RFBatch')
    rfbatch.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    rfbatch.set('xmlns:xsd', 'http://www.w3.org/2001/XMLSchema')

    ET.SubElement(rfbatch, 'Specified').text = 'false'
    ET.SubElement(rfbatch, 'PlateType').text = 'P384'
    ET.SubElement(rfbatch, 'MSIntegrationType').text = 'MASSHUNTER_TOF'
    ET.SubElement(rfbatch, 'FileName').text = rfbat_filename

    plates = ET.SubElement(rfbatch, 'Plates')
    batch_plate = ET.SubElement(plates, 'BatchPlate')
    ET.SubElement(batch_plate, 'MappingFile').text = mapping_file

    unique_name = ET.SubElement(batch_plate, 'uniqueName')
    unique_name.text = sequence_name

    sequences = ET.SubElement(batch_plate, 'Sequences')
    sequence = ET.SubElement(sequences, 'Sequence')

    for well in rfmap_injections:
        ET.SubElement(sequence, 'SEQUENCE').text = well

    cfgfile = ET.SubElement(sequence, 'CFGFILE')
    cfgfile.extend(rfcfg_data)

    ET.SubElement(sequence, "ColumnType").text = column_type
    ET.SubElement(sequence, "PlateNum").text = "1"
    ET.SubElement(sequence, "Method").text = ms_method
    ET.SubElement(sequence, "PlateName").text = plate_name

    ET.SubElement(sequence, "CalibrationMethod").text = cal_method


    output = prettify(rfbatch)
    with open(rfbat_filename, 'w') as output_file:
        output_file.write(output)

def get_set_val(g, key):
    s = set(g[f'{key}'].values)
    if len(s) != 1:
        sys.exit(f"Error, {key} set = {s}")
    return(s.pop())

def create_rfcfg_file(in_xlsx, out_rfcfg, sheet_name = "rf_params"):
    types_d = {"CycleNames" : "string", "CycleDurations" : "int", 
               "Pump1Composition" : "double", "Pump2Composition" : "double", 
               "Pump3Composition" : "double" }

    df = pd.read_excel(in_xlsx, sheet_name = sheet_name)

    # Create the XML structure
    root = ET.Element("RFConfig")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")

    bool_params = ["StandByAfterRun","UsePlateHandler","UseBcodeScanner",
                   "MSStandbyAfterRun","Pump1Active","Pump2Active",
                   "Pump3Active","Pump4Active"]
    bool_d = {'0' : 'false', '1' : 'true'}
    for i, row in df.iterrows():
        row = [x for x in row.values.astype(str) if x != 'nan']
        param = row[0]
        values = row[1 : ]
        if param in bool_params:
            values = [bool_d[x] for x in values]
        if not values:
            continue
        if len(values) == 1:
            elem = ET.SubElement(root, param)
            elem.text = values[0]
        else:
            parent = ET.SubElement(root, param)
            for value in values:
                # elem = ET.SubElement(parent, "double" if "." in value else "int")
                elem = ET.SubElement(parent, types_d[param])
                elem.text = value

    # Generate the XML string
    xml_string = ET.tostring(root, encoding="utf-8", method="xml").decode("utf-8")
    xml_string = '<?xml version="1.0" encoding="utf-8"?>\n' + xml_string

    with open(out_rfcfg, 'w') as f:
        print(prettify(root), file = f)

def get_cal_method_xlsx(in_xlsx, sequence_name, sample_sheet = "samples"):
    df = pd.read_excel(in_xlsx, sheet_name = sample_sheet)
    df = df[df['Sequence'] == sequence_name]
    ms_method = get_set_val(df, "6560_Method")
    ms_mfile = os.path.basename(ms_method)
    cal_mfile = ms_mfile.replace('.m', '_calB.m')
    cal_method = os.path.join(os.path.dirname(ms_method), cal_mfile)
    return(cal_method)


def get_cal_method_rfbat(rfbat_file):
    tree = ET.parse(rfbat_file)
    root = tree.getroot()
    for sequence in root.findall(".//Sequence"):
        calibration_method = sequence.find("CalibrationMethod")
        if calibration_method is not None:
            return calibration_method.text
    if not calibration_method:
        sys.exit(f'Error - couldnt find an IM calibration method element in file {rfbat_file}')
    return None




def create_sequences(in_xlsx, out_dir, sample_sheet = "samples", rf_sheet = "rf_params"):
    df = pd.read_excel(in_xlsx, sheet_name = sample_sheet)
    # os.system(f"mkdir -p {out_dir}")
    os.makedirs(f"{out_dir}", exist_ok = True)
    sequence_files = []
    for sequence_name, g in df.groupby("Sequence"):
        rfcfg_filename = os.path.join(out_dir, f"{sequence_name}.rfcfg")
        create_rfcfg_file(in_xlsx, rfcfg_filename, sheet_name = rf_sheet)
        sequences = g['Well'].values
        rfmap_filename = os.path.join(out_dir, f"{sequence_name}.rfmap")
        plate_type = get_set_val(g, "Plate_Type")
        _ = create_rfmap_xml(sequences, plate_type= plate_type, output_file = rfmap_filename)
        ms_method = get_set_val(g, "6560_Method")
        cal_method = get_cal_method_xlsx(in_xlsx, sequence_name, sample_sheet = sample_sheet)
        column_type = get_set_val(g, "Column_Type")
        rfbat_filename = os.path.join(out_dir, f"{sequence_name}.rfbat")
        plate_name = sequence_name
        create_rfbat_file(rfmap_filename, rfcfg_filename, rfbat_filename, ms_method, column_type, sequence_name, plate_name, cal_method)
        print(rfbat_filename)
        sequence_files.append((sequence_name, rfbat_filename, rfmap_filename, rfcfg_filename))
    return(sequence_files)
        