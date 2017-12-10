"""
    Class for DB
"""

import logging
import sqlite3
import os.path as op
import json


_logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(module)s:%(lineno)s %(levelname)s %(message)s',
    level=logging.DEBUG,
)


class CodeCommentDB():

    def __init__(self, outdb='codecomment.db'):
        self.conn = sqlite3.connect(outdb)
        self._init_db()
        self.cached = False
        self.ginfo = None
        self.cache_path = './cached.tmp'
        if not self._check_newdata() and op.exists(self.cache_path):
            self.cached = True
            self.ginfo = self._load_cache()

    def _save_cache(self, cache):
        json.dump(cache, open(self.cache_path, 'w'))

    def _load_cache(self):
        return json.load(open(self.cache_path, 'r'))

    def _check_newdata(self):
        cur = self.conn.cursor()
        cur.execute('SELECT value FROM tmp WHERE option="cached"''')
        res = cur.fetchone()
        if not res:
            return res
        return res[0]

    def _set_newdata(self, value):
        cur = self.conn.cursor()
        cur.execute('''UPDATE tmp SET value=? WHERE option="cached"''', (value,))

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
        cur.execute('''CREATE TABLE IF NOT EXISTS tmp (option TEXT PRIMARY KEY, value INTEGER)''')
        if not self._check_newdata():
            cur.execute('''INSERT OR IGNORE INTO 
                                    tmp (option, value)
                            VALUES
                                ("cached", 0)''')

    def get_files_repo(self, cur, repo_id):
        cur.execute('SELECT id, path, repo FROM sources WHERE repo=?', (repo_id,))
        return cur.fetchall()

    def get_pairs_file(self, cur, source_id):
        cur.execute('SELECT id, code, comment, line, is_inline, source_id FROM code_comment WHERE source_id=?', (source_id,))
        return cur.fetchall()

    def get_pairs_repo(self, cur, repo_id):
        sources = self.get_files_repo(cur, repo_id)
        ccpairs = []
        for s in sources:
            ccpairs.extend(self.get_pairs_file(cur, s[0]))
        return ccpairs

    def _get_paris_info(self, ccpairs):
        codes = [cc[1] for cc in ccpairs]
        comments = [cc[2] for cc in ccpairs]
        codes_len = list(map(lambda x: len(x), codes))
        comments_len = list(map(lambda x: len(x), comments))
        return codes, comments, codes_len, comments_len

    def get_db_info(self):
        """ Return short summary about all data in DB

            Args:
        """
        if self.cached:
            return self.ginfo
        res = {}
        cur = self.conn.cursor()
        cur.execute('SELECT COUNT(*) FROM repositories')
        res['rcount'] = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM sources')
        res['scount'] = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM code_comment')
        res['pcount'] = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM code_comment WHERE is_inline=1')
        res['picount'] = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM code_comment WHERE is_inline=0')
        res['pbcount'] = cur.fetchone()[0]

        cur.execute('SELECT id, path FROM repositories')
        repos_data = cur.fetchall()
        repos = []
        ccpairs = []
        for rn in repos_data:
            rinfo = self.get_repo_info(rn[1])
            repos.append(rinfo)
            ccpairs.extend(rinfo['pairs'])

        codes, comments, codes_len, comments_len = self._get_paris_info(ccpairs)

        res['repos'] = repos
        res['pairs'] = ccpairs
        res['ccpairs'] = len(ccpairs)
        res['codes'] = codes
        res['comments'] = comments
        res['codes_len'] = codes_len
        res['comments_len'] = comments_len
        res['avgcode'] = sum(codes_len) / float(len(codes_len)) if len(codes_len) else 0
        res['avgcomment'] = sum(comments_len) / float(len(comments_len)) if len(comments_len) else 0

        self.cached = True
        self.ginfo = res
        self._save_cache(self.ginfo)
        self._set_newdata(0)

        return res

    def get_repo_info(self, rpath):
        """ Return short summary about particular repo

            Args:
        """
        if self.cached:
            for r in self.ginfo['repos']:
                if r['rpath'] == rpath:
                    return r
        cur = self.conn.cursor()
        cur.execute('SELECT id FROM repositories WHERE path=?', (rpath,))
        repo_id = cur.fetchone()
        if not repo_id:
            _logger.error("Couldn't locate in DB repository with path {}".format(rpath))
            return {}
        repo_id = repo_id[0]

        repo_files = self.get_files_repo(cur, repo_id)
        rsources = []
        ccpairs_repo = []
        for rp in repo_files:
            sinfo = self.get_source_info(rp[0])
            rsources.append(sinfo)
            ccpairs_repo.extend(sinfo['pairs'])

        codes, comments, codes_len, comments_len = self._get_paris_info(ccpairs_repo)
        rinfo = {
            'rpath': rpath,
            'sources_cnt': len(rsources),
            'sources': rsources,
            'pairs': ccpairs_repo,
            'ccpairs': len(ccpairs_repo),
            'codes': codes,
            'comments': comments,
            'codes_len': codes_len,
            'comments_len': comments_len,
            'avgcode': sum(codes_len) / float(len(codes_len)) if len(codes_len) else 0,
            'avgcomment': sum(comments_len) / float(len(comments_len)) if len(comments_len) else 0,
        }

        return rinfo

    def get_source_info(self, spath):
        cur = self.conn.cursor()
        ccpairs_file = self.get_pairs_file(cur, spath)
        codes, comments, codes_len, comments_len = self._get_paris_info(ccpairs_file)
        sinfo = {
            'path': spath,
            'pairs': ccpairs_file,
            'ccpairs': len(ccpairs_file),
            'codes': codes,
            'comments': comments,
            'codes_len': codes_len,
            'comments_len': comments_len,
            'avgcode': sum(codes_len) / float(len(codes_len)) if len(codes_len) else 0,
            'avgcomment': sum(comments_len) / float(len(comments_len)) if len(comments_len) else 0,
        }
        return sinfo

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
        self._set_newdata(1)
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
        self._set_newdata(1)
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
        self._set_newdata(1)
        _logger.info("Inserting into DB information about repository {} started".format(rd['rpath']))
        cur = self.conn.cursor()
        cur.execute('''INSERT OR IGNORE INTO repositories (path, name) VALUES (?, ?)''', (rd['rpath'], ''))
        repoid = cur.lastrowid
        for fd in rd['files']:
            fd['repoid'] = repoid
            self.save_file_data(fd)
        _logger.info("Inserting into DB information about repository {} finished".format(rd['rpath']))

    def get_codecomment_pairs(self, params={}):
        cur = self.conn.cursor()
        sql = "SELECT code, comment FROM code_comment"
        where = []
        if params.get('inline'):
            where.append("is_inline = :inline")
        if where:
            sql = "{} WHERE {}".format(sql, ' AND '.join(where))
        cur.execute(sql)
        return cur.fetchall()
