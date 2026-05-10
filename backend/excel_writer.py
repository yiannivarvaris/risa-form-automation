from openpyxl import load_workbook
from copy import copy

def create_race_sheet(template_path, output_path):
    workbook = load_workbook(template_path)

    template = workbook["template"]

    new_sheet = workbook.copy_worksheet(template)
    new_sheet.title = "Race 1"

    # Test data for now
    new_sheet["B4"] = "TEST HORSE"
    new_sheet["P4"] = 58
    new_sheet["D5"] = 59
    new_sheet["E5"] = 58
    new_sheet["I5"] = 56
    new_sheet["K5"] = 2.5

    workbook.save(output_path)
