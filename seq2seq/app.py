# app.py


from flask import Flask
from flask import request, render_template
from flask.ext.sqlalchemy import SQLAlchemy
from config import BaseConfig


app = Flask(__name__)
app.config.from_object(BaseConfig)
db = SQLAlchemy(app)


@app.route('/', methods=['GET', 'POST'])
def index():
    """

    Returns:

    """
    if request.method == 'POST':
        # text = request.form['text']
        # post = Post(text)
        # db.session.add(post)
        # db.session.commit()
        return render_template('index.html')
    return render_template('index.html')


if __name__ == '__main__':
    app.run()
