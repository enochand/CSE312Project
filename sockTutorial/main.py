from flask import Flask, render_template
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

socks = []

@app.route('/')
def index():
    return render_template('auctions_page.html')


@sock.route('/echo')
def echo(sock):
    print(f'{sock} joined!')
    socks.append(sock)
    while True:
        data = sock.receive()
        for sock in socks:
            sock.send(data)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)