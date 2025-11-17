from fastapi import FastAPI
import json
from pathlib import Path

app = FastAPI()

def get_json_path(*paths):
    return Path(__file__).parent.joinpath(*paths)

def load_json(path: Path):
    if path.exists():
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {}

laser_data = load_json(get_json_path("yacht", "Laser", "description.json"))
_470_data = load_json(get_json_path("yacht", "470", "description.json"))
baseball_data = load_json(get_json_path("baseball", "baseball.json"))
gym_men_data = load_json(get_json_path("gymnastics", "gymnastics_men.json"))
gym_women_data = load_json(get_json_path("gymnastics", "gymnastics_women.json"))

@app.get("/")
async def root():
    return {"message": "Yacht Expert AI"}

@app.get("/laser")
async def laser():
    return laser_data

@app.get("/470")
async def four_seventy():
    return _470_data

@app.get("/baseball")
async def baseball():
    return baseball_data

@app.get("/gym/men")
async def gymnastics_men():
    return gym_men_data

@app.get("/gym/women")
async def gymnastics_women():
    return gym_women_data
