from typing import Union
from fastapi import FastAPI, Query, Request
import pymongo
import uuid
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
import random
import os

app = FastAPI()

app.mount("/assets", StaticFiles(directory="Template/assets"), name="assets")
# app.mount("/", StaticFiles(directory="Template", html=True), name="Template")

# templates = Jinja2Templates(directory="Template")

url = os.environ.get("mongodb_url")
# client = motor.motor_asyncio.AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)



@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
async def get_index(request: Request):
    return FileResponse("Template/index.html")


@app.get("/100.html", response_class=HTMLResponse)
async def get_index(request: Request):
    return FileResponse("Template/100.html")


@app.get("/get_names")
async def read_root(request: Request):
    client = pymongo.MongoClient(url)
    name_mash_master_col = client["NameMash"]["name_mash_master"]
    name_mash_submission_col = client["NameMash"]["name_mash_submission"]
    two_names_from_name_mash = list(
        name_mash_master_col.aggregate([
            {"$project": {
                "selection_name": 1,
                "_id": 0
            }}
        ])
    )
    two_names_from_name_mash = random.sample(two_names_from_name_mash, 2)
    first_id, second_id, token = str(uuid.uuid4()), str(
        uuid.uuid4()), str(uuid.uuid4())
    name_mash_submission_col.insert_one({
        "first_id": first_id,
        "second_id": second_id,
        "token": token,
        "first_option": two_names_from_name_mash[0]["selection_name"],
        "second_option": two_names_from_name_mash[1]["selection_name"],
        "voted_id": 0,
        # "request_client_host": request.client.host,
        # "request_header": request.headers
    })
    random.shuffle(two_names_from_name_mash)
    print("====================================")
    return {
        "first_id": first_id,
        "second_id": second_id,
        "token": token,
        "names_list": two_names_from_name_mash
    }


class NameMashSelection(BaseModel):
    token: str
    first_id: str
    second_id: str
    voted_id: int = Query(gt=0, lt=3)


@app.post("/select")
async def read_root(data: NameMashSelection, request: Request):
    client = pymongo.MongoClient(url)
    name_mash_submission_col = client["NameMash"]["name_mash_submission"]
    consume_token = name_mash_submission_col.update_one({
        "first_id": data.first_id,
        "second_id": data.second_id,
        "token": data.token,
        "voted_id": 0
    }, {
        "$set": {
            "voted_id": data.voted_id,
            # "client_host": request.client.host,
            # "header": request.headers
        }
    })
    if consume_token.matched_count > 0:
        name_mash_master_col = client["NameMash"]["name_mash_master"]
        master_name = name_mash_submission_col.find_one({
            "first_id": data.first_id,
            "second_id": data.second_id,
            "token": data.token,
        })
        selected_option = master_name["first_option"] if data.voted_id == 1 else master_name["second_option"]
        effected_master = list(name_mash_master_col.find({
            "$or": [{
                "selection_name": master_name["first_option"]
            }, {
                "selection_name": master_name["second_option"]
            }]
        }))
        for single_master in effected_master:
            positve_votes = single_master.get(
                "positve_votes") if single_master.get("positve_votes") else 0
            negative_votes = single_master.get(
                "negative_votes") if single_master.get("negative_votes") else 0
            if single_master["selection_name"] == selected_option:
                positve_votes = positve_votes + 1
            else:
                negative_votes = negative_votes + 1
            total_votes = positve_votes + negative_votes
            postive_percentage = positve_votes / total_votes
            negative_percentage = negative_votes / total_votes
            name_mash_master_col.update_one({
                "selection_name": single_master["selection_name"]
            }, {
                "$set": {
                    "positve_votes": positve_votes,
                    "negative_votes": negative_votes,
                    "total_votes": total_votes,
                    "postive_percentage": postive_percentage,
                    "negative_percentage": negative_percentage
                }
            })
        return f"successfully voted for '{selected_option}'"
    return "invalid token or already used"


@app.get("/top100")
async def get_top100(request: Request):
    client = pymongo.MongoClient(url)
    name_mash_master_col = client["NameMash"]["name_mash_master"]
    # result = name_mash_master_col.find({}).sort([("postive_percentage", -1), ("total_votes", -1), ("selection_name", 1)]).limit(100)
    result = name_mash_master_col.find({}, {
        "selection_name": 1,
        "positve_votes": 1,
        "negative_votes": 1,
        "total_votes": 1,
        "postive_percentage": 1,
        "negative_percentage": 1,
        "_id": 0
    }).sort([
        ("postive_percentage", -1),
        ("total_votes", -1),
        ("selection_name", 1),
    ]).limit(100)
    result = {
        "top100": list(result)
    }
    return result



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
