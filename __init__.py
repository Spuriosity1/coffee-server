from flask import Flask, g, request, current_app
import json
import os
from datetime import datetime as dt
app = Flask(__name__)


# The factory function
def create_app(test_config=None):

    app = Flask(__name__, instance_relative_config=True)

    # Defaults to be overridden
    app.config.from_mapping(
            PRIMARYDB=os.path.join(app.instance_path, 'testDB1.sqlite'),
            SECONDARYDB=os.path.join(app.instance_path, 'testDB2.sqlite')
            )

    if test_config is None:
        app.config.from_file("config.json", load=json.load)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from beanbot import auth
    app.register_blueprint(auth.bp)

    from beanbot.db import init_app
    init_app(app)

    @app.route('/userstats/<crsid>',defaults={'begin':'2023-01-01T00-00-00'})
    @app.route('/userstats/<crsid>/<begin>')
    def user_stats(crsid, begin):
        # humantime to unix time
        # note: assumes begin is in UTC 
        # actually fine, we are in the UK haha 
        g.db.open_db()
        begin_posix = dt.strptime(begin,"%Y-%m-%dT%H-%M-%S").strftime('%s')
        total_shots = g.db.execute(
                "SELECT sum(ncoffee) FROM transactions WHERE crsid=? AND ts > ?",
                (crsid, begin_posix)).fetchone()
        totals = g.db.execute(
                "SELECT type,count(ts) FROM transactions WHERE crsid=? AND ts > ? GROUP BY type",
                (crsid, begin_posix)).fetchall()
        return {            
                "total_shots": total_shots,
                "totals": { r[0] : r[1] for r in totals }
                }
    
    
    @app.route('/api/timeseries', defaults={'crsid':None})
    @app.route('/api/timeseries/<crsid>')
    def get_timeseries(crsid):
        g.db.open_db()
        hdr = ["timestamp", "type"]
        if crsid is None:
            r = g.db.execute(
                "SELECT ts, type, crsid FROM transactions")
            hdr += ['crsid']
        else:
            r = g.db.execute(
                    "SELECT ts, type FROM transactions WHERE crsid=?", (crsid,))
        return { 
                "headers": hdr,
                "table": r.fetchall()
                }
    
    @app.route('/existsuser/<crsid>')
    def exists_user(crsid):
        # check if user exists at all
        g.db.open_db()
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
#    
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
#                    
#        # this is a really, really bad idea...
    
    return app    

