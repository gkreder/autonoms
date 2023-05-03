import sys
import os
import csv
import xml.etree.ElementTree as ET
import argparse

def read_tsv(file_path):
    with open(file_path, "r") as tsv_file:
        tsv_reader = csv.reader(tsv_file, delimiter='\t')
        sequences = [row[0] for i_row, row in enumerate(tsv_reader) if i_row > 0]
    return sequences

def create_xml(sequences, output_file, plate_type="P384"):
    rf_plate_map = ET.Element("RFPlateMap")
    rf_plate_map.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    rf_plate_map.set("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")

    file_name = ET.SubElement(rf_plate_map, "FileName")
    file_name.text = output_file

    plate_type_element = ET.SubElement(rf_plate_map, "PlateType")
    plate_type_element.text = plate_type

    sequences_element = ET.SubElement(rf_plate_map, "Sequences")
    array_of_string = ET.SubElement(sequences_element, "ArrayOfString")

    for seq in sequences:
        seq_element = ET.SubElement(array_of_string, "string")
        seq_element.text = seq

    xml_string = ET.tostring(rf_plate_map, encoding="utf-8", method="xml")
    with open(output_file, "wb") as output_xml:
        output_xml.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
        output_xml.write(xml_string)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--in_tsv', required = True)
    parser.add_argument('--out_rfmap', required = True)
    parser.add_argument('--plate_type', default = "P384")
    args = parser.parse_args()
    sequences = read_tsv(args.in_tsv)
    create_xml(sequences, args.out_rfmap, args.plate_type)

if __name__ == "__main__":
    main()
