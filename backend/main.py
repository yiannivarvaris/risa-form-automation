import logging
import os
import shutil

from fastapi import FastAPI, File, UploadFile
from fastapi import HTTPException
from fastapi.responses import FileResponse

from excel_writer import write_races_to_excel
from parser import extract_text_from_pdf, parse_races_from_text

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

app = FastAPI()


@app.get("/")
def home():
    return {"message": "RISA Form Automation backend is running"}


@app.post("/generate")
async def generate_form(
    risa_file: UploadFile = File(...),
    excel_template: UploadFile = File(...),
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
    races = parse_races_from_text(text)
    LOGGER.info("Preparing workbook for %s races", len(races))
    if not races:
        raise HTTPException(status_code=422, detail="No races extracted from PDF")

    write_races_to_excel(template_path, output_path, races)

    return FileResponse(
        output_path,
        filename="completed_form.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
