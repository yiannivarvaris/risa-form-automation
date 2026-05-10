from openpyxl import load_workbook


def write_races_to_excel(template_path, output_path, races):
    workbook = load_workbook(template_path)

    template = workbook["template"]

    # Delete old Race tabs if they already exist
    for sheet_name in list(workbook.sheetnames):
        if sheet_name.startswith("Race "):
            del workbook[sheet_name]

    for race in races:
        new_sheet = workbook.copy_worksheet(template)
        new_sheet.title = race["race_name"]

        row = 4

        for horse in race["horses"]:
            # Runner identity
            new_sheet[f"A{row}"] = horse.get("number")
            new_sheet[f"B{row}"] = horse["name"]

            # Today's adjusted weight (step 5)
            new_sheet[f"P{row}"] = horse.get("today_weight")

            # Last-start metrics (steps 6-9)
            new_sheet[f"D{row+1}"] = horse.get("last_rating")
            new_sheet[f"E{row+1}"] = horse.get("last_declared_weight")
            new_sheet[f"I{row+1}"] = horse.get("last_carried_weight")
            new_sheet[f"K{row+1}"] = horse.get("last_margin")

            # Most recent race class (step 20)
            new_sheet[f"U{row}"] = horse.get("last_class")

            # 3yo/sex note (step 19)
            if horse.get("age") == 3 and horse.get("sex"):
                new_sheet[f"V{row}"] = f"3yo {horse['sex'].lower()}"

            # Repeat horse names in downstream modelling columns (step 10)
            new_sheet[f"AA{row+1}"] = horse["name"]
            new_sheet[f"AD{row+1}"] = horse["name"]

            # Remaining required tracking columns (steps 13-16)
            new_sheet[f"AE{row+1}"] = horse.get("runs_since_first_up")
            new_sheet[f"AF{row+1}"] = horse.get("days_since_last_start")
            new_sheet[f"AG{row+1}"] = horse.get("track_record")
            new_sheet[f"AH{row+1}"] = horse.get("distance_record")

            # Step 17: do not skip rows; each runner goes directly below the previous.
            row += 1

    workbook.save(output_path)
