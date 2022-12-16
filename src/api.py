from typing import List
from fastapi import FastAPI, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
import uvicorn
from threading import Thread
import logging

import serverstatus

app = FastAPI(docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json")
port = 61000

def run():
	try:
		uvicorn.run("api:app", host="0.0.0.0", port=port)
	except Exception as e:
		logging.warning(f"Failed to start API")
		logging.error(str(e))

def start():
	t = Thread(target=run)
	t.start()

@app.get("/api")
def get_serverstatus(platform: List[str] = Query(default=None)):
	status = {}

	# パラメーターが指定されていない場合は全てのプラットフォームのステータスを返す
	if platform == None:
		status = serverstatus.data
		if "_update_date" in status.keys(): del status["_update_date"]
	else:
		# 指定されたプラットフォームのステータスだけ返す
		#platforms = platforms.split(",")
		for p in platform:
			d = serverstatus.data.get(p)
			if d != None:
				status[p] = d

	# JSONでサーバーステータスのデータを返す
	return JSONResponse(content=jsonable_encoder(status))

if __name__ == "__main__":
	start()
