""" Flask application for data visualization
"""

from flask import Flask
from flask import Response
from flask import abort
from flask import make_response
from flask import request, render_template
from flask.ext.sqlalchemy import SQLAlchemy
from config import BaseConfig
from database import CodeCommentDB
import logging

import numpy as np
from datavisual import DataVisualizer

app = Flask(__name__, static_url_path='/static')
app.config.from_object(BaseConfig)
db = SQLAlchemy(app)

ccdb = None

_logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(module)s:%(lineno)s %(levelname)s %(message)s',
    level=logging.DEBUG,
)


@app.route('/gen_info', methods=['POST'])
def gen_info():
    _logger.info('gen_info called')
    global ccdb
    dbpath = request.values.get('dbpath')
    if not dbpath:
        _logger.error('Error during gen_info call. DBPATH parameter missed!')
        return 'Error'
    ccdb = CodeCommentDB(dbpath)
    gen_info = ccdb.get_db_info()

    codes_len = gen_info['codes_len']
    comments_len = gen_info['comments_len']
    hist_params = {
        'title': "Distribution of code sequences lengths",
        'plot_width': 500,
        'plot_height': 300,
        'bins': 500
    }
    script, div = DataVisualizer.generate_web_hist(codes_len, hist_params)
    hist_params['title'] = "Distribution of comments sequences lengths"
    script2, div2 = DataVisualizer.generate_web_hist(comments_len, hist_params)

    return render_template('gen_info.html', ginfo=gen_info,
                           the_div=div, the_script=script,
                           the_div2=div2, the_script2=script2)


@app.route('/repo_info', methods=['POST'])
def repo_info():
    if not ccdb:
        _logger.error("Error during repo_info call. DB should be initialized first!")
        return 'Error'
    rpath = request.values.get('rpath')
    repo = ccdb.get_repo_info(rpath)

    codes_len = repo['codes_len']
    comments_len = repo['comments_len']

    hist_params = {
        'title': "Distribution of code sequences lengths",
        'plot_width': 500,
        'plot_height': 300,
        'bins': 500
    }
    script, div = DataVisualizer.generate_web_hist(codes_len, hist_params)
    hist_params['title'] = "Distribution of comments sequences lengths"
    script2, div2 = DataVisualizer.generate_web_hist(comments_len, hist_params)

    return render_template('repo_info.html', repo=repo,
                           the_div=div, the_script=script,
                           the_div2=div2, the_script2=script2)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

if __name__ == '__main__':
    _logger.info("Flask application for data visualization started")
    app.run()
    _logger.info("Flask application for data visualization finished")
