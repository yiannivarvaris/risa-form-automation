from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import shutil
import os

from parser import extract_text_from_pdf, extract_races
from excel_writer import write_races_to_excel

app = FastAPI()


@app.get("/")
def home():
    return {"message": "RISA Form Automation backend is running"}


@app.post("/generate")
async def generate_form(
    risa_file: UploadFile = File(...),
    excel_template: UploadFile = File(...)
):
    os.makedirs("uploads", exist_ok=True)

    risa_path = f"uploads/{risa_file.filename}"
    template_path = f"uploads/{excel_template.filename}"
    output_path = "uploads/completed_form.xlsx"

    with open(risa_path, "wb") as buffer:
        shutil.copyfileobj(risa_file.file, buffer)

    with open(template_path, "wb") as buffer:
        shutil.copyfileobj(excel_template.file, buffer)

    text = extract_text_from_pdf(risa_path)

    print("PDF TEXT START")
    print(text[:5000])
    print("PDF TEXT END")

    races = extract_races(text)

    print("RACES FOUND")
    for race in races:
        print(race["race_name"], [horse["name"] for horse in race["horses"]])

    write_races_to_excel(
        template_path,
        output_path,
        races
    )

    return FileResponse(
        output_path,
        filename="completed_form.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
