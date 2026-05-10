from openpyxl import load_workbook

def write_races_to_excel(template_path, output_path, races):
    workbook = load_workbook(template_path)

    template = workbook["template"]

    for race in races:
        new_sheet = workbook.copy_worksheet(template)
        new_sheet.title = race["race_name"]

        row = 4

        for horse in race["horses"]:
            new_sheet[f"B{row}"] = horse["name"]
            row += 2

    workbook.save(output_path)
