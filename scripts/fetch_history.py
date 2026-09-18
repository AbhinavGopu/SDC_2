"""Fetch a dated historical reanalysis sample, never label it station telemetry."""
import csv, json, urllib.request
from pathlib import Path
URL = "https://archive-api.open-meteo.com/v1/archive?latitude=17.435&longitude=78.445&start_date=2025-07-01&end_date=2025-07-07&daily=precipitation_sum&timezone=UTC&models=era5"
def main():
    with urllib.request.urlopen(URL,timeout=30) as r: data=json.load(r)
    target=Path("data/historical");target.mkdir(parents=True,exist_ok=True)
    (target/"open_meteo_era5_2025_07.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    with (target/"rainfall.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f);writer.writerow(["ward_id","domain","metric","value","unit","observed_at"])
        for date,value in zip(data["daily"]["time"],data["daily"]["precipitation_sum"]):
            if value is not None: writer.writerow([1,"weather","precipitation_sum",value,"mm",date+"T00:00:00+00:00"])
    (target/"provenance.json").write_text(json.dumps({"url":URL,"source":"Open-Meteo historical API / ERA5 reanalysis","license":"CC BY 4.0 (Open-Meteo); attribution to Copernicus ERA5 required","kind":"historical gridded weather reanalysis; NOT observed traffic or official live telemetry","requested_coordinates":[17.435,78.445],"returned_coordinates":[data["latitude"],data["longitude"]]},indent=2),encoding="utf-8")
    print("Downloaded",len(data["daily"]["time"]),"historical daily precipitation records")
if __name__=="__main__":main()
