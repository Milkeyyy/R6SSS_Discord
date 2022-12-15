from flask import Flask, jsonify, request
from threading import Thread

import serverstatus

app = Flask('')
#日本語を利用
app.config['JSON_AS_ASCII'] = False

def run():
  app.run(host='0.0.0.0', port=8080)

def start():
    t = Thread(target=run)
    t.start()

@app.route("/")
def alive():
    return "ここにはなにもないようだ ▼"

@app.route("/api", methods=["GET"])
def get_serverstatus():
	status = {}
	args = request.args
	platforms = args.get("platforms")
	#print(str(platforms) + " / " + str(type(platforms)))

	# パラメーターが指定されていない場合は全てのプラットフォームのステータスを返す
	if platforms == None:
		status = serverstatus.data
	else:
		# 指定されたプラットフォームのステータスだけ返す
		platforms = platforms.split(",")
		for p in platforms:
			d = serverstatus.data.get(p)
			if d != None:
				status[p] = d

	return jsonify(status)