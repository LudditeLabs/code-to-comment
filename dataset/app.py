""" Flask application for data visualization
"""

from flask import Flask
from flask import Response
from flask import abort
from flask import make_response
from flask import request, render_template
from flask.ext.sqlalchemy import SQLAlchemy
from config import BaseConfig

import logging

app = Flask(__name__, static_url_path='/static')
app.config.from_object(BaseConfig)
db = SQLAlchemy(app)


_logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(module)s:%(lineno)s %(levelname)s %(message)s',
    level=logging.DEBUG,
)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

if __name__ == '__main__':
    _logger.info("Flask application for data visualization started")
    app.run()
    _logger.info("Flask application for data visualization finished")
