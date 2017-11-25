"""
    Class for DB
"""

import logging
import sqlite3


_logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(module)s:%(lineno)s %(levelname)s %(message)s',
    level=logging.DEBUG,
)


class CodeCommentDB():

    def __init__(self, outdb='codecomment.db'):
        self.conn = sqlite3.connect(outdb)
        self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS repositories (id INTEGER PRIMARY KEY, path TEXT UNIQUE, name TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS sources (id INTEGER PRIMARY KEY, path TEXT UNIQUE, repo INTEGER)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS code_comment (id INTEGER PRIMARY KEY,
                                                                code TEXT,
                                                                comment TEXT,
                                                                line INTEGER,
                                                                is_inline INTEGER,
                                                                source_id INTEGER)''')

    def save_cc_pairs(self, pd):
        """ Save all pairs from pd parameter to DB

            Args:
                pd: dict with following fields {'srcid': int, 'pairs': list_of_dicts}
                'pairs' element have following structure
                    Dict {
                        'pair': tuple(code, comment),
                        'is_inline': boolean,
                        'linenum': int
                    }
        """
        cur = self.conn.cursor()
        srcid = pd['srcid']
        pairs = pd['pairs']
        iso_level = self.conn.isolation_level
        self.conn.isolation_level = None
        _logger.info("Inserting into DB information about founded code-comment pairs started")
        if pairs:
            cur.execute('begin')
            for p in pairs:
                cur.execute('''INSERT OR IGNORE INTO 
                                    code_comment (code, comment, line, is_inline, source_id)
                                VALUES
                                    (?, ?, ?, ?, ?)
                            ''', (unicode(p['pair'][0], errors='ignore'), unicode(p['pair'][1], errors='ignore'), p['linenum'], p['is_inline'], srcid))
            cur.execute('commit')
        self.conn.isolation_level = iso_level
        _logger.info("Inserting into DB information about founded code-comment pairs finished")
        pass

    def save_file_data(self, fd):
        """ Save all information about source file (both about filepath and all founded in file code-comment pairs) into DB

            Args:
                fd: dict with file description {'fpath': fp, 'repoid': repo, 'pairs': pairs}
                    pairs - dict with structure
                        Dict {
                            'accepted_block': [...],
                            'rejected_block': [...],
                            'accepted_inline': [...],
                            'rejected_inline': [...]
                        }
                        all lists contains dicts with following structure
                            Dict {
                                'pair': tuple(code, comment),
                                'is_inline': boolean,
                                'linenum': int
                            }
        """
        _logger.info("Inserting into DB information about file {} started".format(fd['fpath']))
        cur = self.conn.cursor()
        cur.execute('''INSERT OR IGNORE INTO sources (path, repo) VALUES (?, ?)''', (fd['fpath'], fd['repoid']))
        srcid = cur.lastrowid
        p = fd['pairs']
        pairs = p['accepted_block'] + p['accepted_inline']
        pd = {'srcid': srcid, 'pairs': pairs}
        self.save_cc_pairs(pd)
        _logger.info("Inserting into DB information about file {} finished".format(fd['fpath']))
        return srcid

    def save_repo_data(self, rd):
        _logger.info("Inserting into DB information about repository {} started".format(rd['rpath']))
        cur = self.conn.cursor()
        cur.execute('''INSERT OR IGNORE INTO repositories (path, name) VALUES (?, ?)''', (rd['rpath'], ''))
        repoid = cur.lastrowid
        for fd in rd['files']:
            fd['repoid'] = repoid
            self.save_file_data(fd)
        _logger.info("Inserting into DB information about repository {} finished".format(rd['rpath']))

    def get_codecomment_pairs(self, params):
        cur = self.conn.cursor()
        sql = "SELECT code, comment FROM code_comment"
        where = []
        if params.get('inline'):
            where.append("is_inline = :inline")
        if where:
            sql = "{} WHERE {}".format(sql, ' AND '.join(where))
        cur.execute(sql)
        return cur.fetchall()
