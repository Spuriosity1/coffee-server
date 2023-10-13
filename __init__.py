from flask import Flask, g, request, current_app, render_template
import json
import os
from datetime import datetime as dt
# app = Flask(__name__)


# The factory function
def create_app(test_config=None):

    app = Flask(__name__, instance_relative_config=True)

    @app.route('/ping', methods=['GET', 'POST'])
    def ping():
        return "Pong!"

    # Defaults to be overridden
#    app.config.from_mapping(
#            PRIMARYDB=os.path.join(app.instance_path, 'testDB1.sqlite'),
#            SECONDARYDB=os.path.join(app.instance_path, 'testDB2.sqlite')
#            )

    if test_config is None:
        app.config.from_file("config.json", load=json.load)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

#    from beanbot import auth
#    app.register_blueprint(auth.bp)

    from beanbot.db import init_app
    init_app(app)

    @app.route('/favicon.ico')
    def faviconIt():
        return app.serve_static('favicon.ico')

    @app.route('/')
    @app.route('/index')
    def index():
        return render_template("index.html")


    @app.route('/docs')
    def docs():
        return render_template("docs.html")

    #@app.route('/api/userstats/')
    #def user_all_stats():
    #    db.open_db()
    #    total_shots = g.db.execute(
    #            "SELECT crsid, sum(ncoffee) FROM transactions GROUP BY crsid").fetchall()
    #    res = {}
    #    for row in total_shots:
    #        res[row[0]] = {
    #                "total_shots": row[1],
    #                "totals": g.db.execute(
    #            "SELECT type, count(ts) FROM transactions \
    #                    WHERE crsid=? GROUP BY type",(row[0],)).fetchall()
    #                }
    #    return res

    @app.route('/api/leaderboard',
               defaults={'begin': '2023-01-01T00-00-00'})
    @app.route('/api/leaderboard/<begin>')
    def get_leaderboard(begin):
        db.open_db()
        begin_posix = dt.strptime(begin, "%Y-%m-%dT%H-%M-%S").strftime('%s')
        total_shots = g.db.execute(
                "SELECT sum(ncoffee), crsid FROM transactions \
                        WHERE ts > ? \
                        GROUP BY crsid \
                        ORDER BY -sum(ncoffee)", (begin_posix,)).fetchall()
        return [{"crsid": r[1], "shots": r[0]} for r in total_shots]



    @app.route('/api/userstats/<crsid>', defaults={'begin': '2023-01-01T00-00-00'})
    @app.route('/api/userstats/<crsid>/<begin>')
    def user_stats(crsid, begin):
        db.open_db()
        begin_posix = dt.strptime(begin, "%Y-%m-%dT%H-%M-%S").strftime('%s')
        total_shots = g.db.execute(
                "SELECT sum(ncoffee) FROM transactions \
                        WHERE crsid=? AND ts > ?",
                (crsid, begin_posix)).fetchone()
        totals = g.db.execute(
                "SELECT type,count(ts) FROM transactions \
                        WHERE crsid=? AND ts > ? GROUP BY type",
                (crsid, begin_posix)).fetchall()
        return {
                "total_shots": total_shots,
                "totals": {r[0]: r[1] for r in totals}
                }

    @app.route('/api/timeseries')
    def get_timeseries():
        db.open_db()
        hdr = ["DATETIME(ts,'unixepoch')", "type", "crsid"]
        crsid = request.args.get('crsid')
        after = request.args.get('after')
        before = request.args.get('before')

        conds = []

        if crsid is not None:
            hdr.remove('crsid')
            conds += [("crsid=?", crsid)]

        if after is not None:
            after = dt.strptime(after, "%Y-%m-%dT%H-%M-%S").strftime('%s')
            conds += [('ts >= ?', after)]

        if before is not None:
            before = dt.strptime(before, "%Y-%m-%dT%H-%M-%S").strftime('%s')
            conds += [('ts <= ?', before)]

        q = "SELECT " + ", ".join(hdr) + " FROM transactions"
        if len(conds) > 0:
            q += " WHERE " + " AND ".join([x[0] for x in conds])
        print(q)
        r = g.db.execute(q, tuple([x[1] for x in conds]))

        data = r.fetchall()
        hdr[0] = 'timestamp'

        return {
                "headers": hdr,
                "table": data
                }

    @app.route('/api/existsuser/<crsid>')
    def exists_user(crsid):
        # check if user exists at all
        db.open_db()
        r1 = g.db.execute(
                "SELECT count(crsid), rfid FROM users WHERE crsid=?", (crsid,))
        found_id, rfid = r1.fetchone()
        if found_id != 0:
            return {"user-exists": True, "rfid": rfid}

        return {"user-exists": False}

#    @app.route('/newuser/<crsid>', methods=['POST'])
#    @auth.login_required
#    def create_user(crsid):
#        if len(crsid) > 8:
#            return {"reason": "crsid must be <= 8 characters"}, 400
#        if 'debt' not in request.args:
#            return {"reason": "Malformed query: debt is mandartory"}, 400
#        debt = request.args['debt']

#        db.open_db()
#        try:
#            res = {
#                "added_user": True,
#                "added_init_transactions": False
#                }
#            g.db.execute(
#                    "INSERT INTO users (crsid, debt) VALUES (?, ?)",
#                (crsid, debt))
#            if debt != 0:
#                g.db.execute(
#                        "INSERT INTO transactions (ts, crsid, debit, type, ncoffee) VALUES (datetime('now'), ?, ?, 'prevbalance', 0)",
#                        (crsid, debt))
#                res["added_init_transactions"] = True
#            g.db.commit()
#            return res
#        except sqlite3.IntegrityError as e:
#            return {"reason": f"User {crsid} already exists"}, 400
#        # this is a really, really bad idea...

    return app

