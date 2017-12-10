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
from bokeh.layouts import gridplot
from bokeh.plotting import figure, show, output_file
from bokeh.embed import components
from bokeh.models.tools import BoxSelectTool, BoxZoomTool, SaveTool, PanTool, ZoomInTool, ZoomOutTool

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
    return render_template('gen_info.html', ginfo=gen_info)


@app.route('/repo_info', methods=['POST'])
def repo_info():
    if not ccdb:
        _logger.error("Error during repo_info call. DB should be initialized first!")
        return 'Error'
    rpath = request.values.get('rpath')
    repo = ccdb.get_repo_info(rpath)

    codes_len = repo['codes_len']
    comments_len = repo['comments_len']

    tools = [BoxSelectTool(), BoxZoomTool(), SaveTool(), PanTool(), ZoomInTool(), ZoomOutTool()]

    p1 = figure(title="Distribution of code sequences lengths", plot_width=500, tools=tools,
                toolbar_location="below", plot_height=300, background_fill_color="#E8DDCB")

    hist, edges = np.histogram(codes_len, density=True, bins=50)

    p1.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
            fill_color="#036564", line_color="#033649")

    p1.legend.location = "center_right"
    p1.legend.background_fill_color = "darkgrey"
    p1.xaxis.axis_label = 'Sequence len'
    p1.yaxis.axis_label = 'Count'

    script, div = components(p1)

    p2 = figure(title="Distribution of comments sequences lengths", plot_width=500, tools=tools,
                toolbar_location="below", plot_height=300, background_fill_color="#E8DDCB")

    hist, edges = np.histogram(comments_len, density=True, bins=50)

    p2.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
            fill_color="#036564", line_color="#033649")

    p2.legend.location = "center_right"
    p2.legend.background_fill_color = "darkgrey"
    p2.xaxis.axis_label = 'Sequence len'
    p2.yaxis.axis_label = 'Count'

    script2, div2 = components(p2)

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
