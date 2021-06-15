from flask import Flask, request, abort, render_template
from webhookListener import write_to_csv


app = Flask(__name__)


@app.route("/", methods=['GET', 'POST'])
def application():
    if request.method == 'POST':
        try:
            write_to_csv(request)
        except PermissionError:
            print(request)
        return 'success!', 200
    elif request.method == 'GET':
        return render_template('index.html')
    else:
        abort(400)







