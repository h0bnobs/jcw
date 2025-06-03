from flask import Flask

app = Flask(__name__, static_folder="static", template_folder="templates")

@app.route("/")
def hello_world():
    return "<h3>jcw</h3>"
