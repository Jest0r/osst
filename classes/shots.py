#!/usr/bin/env python3
import datetime
import os
import json
#from . import csv
#import math


# if a break is longer than 1 hour, it's counted as the next session
SESSION_BREAK = 3600 



class Shot():
    def __init__(self, shotdata, json=False):
        self.csvdata = None
        self.shooter = None
        self.date = None
        self.competition = None
        self.shotdata = None
        self.shot = None
        self.practice = True
        self.uid = None


        if json is True:
            self._get_shot_from_json(shotdata)
        else:
            self._get_shot_from_csv(shotdata)

    def _get_shot_from_json(self, raw_json_data):
        json_data = json.loads(raw_json_data)
        if json_data['MessageVerb'] == 'Shot':
            print(".bla")

            c = json_data['Objects'][0]
            self.shooter = c['Shooter']
            #self.date = datetime.datetime.strptime(c['ShotDateTime'], "%Y-%m-%d %H:%M:%S.000").isoformat()
            self.date = datetime.datetime.fromisoformat(c['ShotDateTime'])
    #            print(f"jsonshot: {self.shotdata}")
            self.competition = None
            self.shotdata = c
            self.shot = {}
            self.practice = True
            self.uuid = c['UUID'].lower()

            if type(self.shotdata) == list:
                for s in self.shotdata[1:-1]:
                    if "=" not in s:
                        continue
                    k,v = s.split("=")
                    self.shot.update({k:v.strip("\"")})
            else:
                self.practice = True
                self.shot['disktyp'] = self.shotdata['DiscType'].lower()
                self.shot['teiler'] = self.shotdata['Distance']
                self.shot['x'] = self.shotdata['X']
                self.shot['y'] = self.shotdata['Y']
                self.shot['shot'] = self.shotdata['Count']
                self.shot['full'] = self.shotdata['FullValue']
            self.shot['dec'] = self.shotdata['DecValue']

    def _get_shot_from_csv(self, csvdata):
        self.csvdata = csvdata
        self.shooter = csvdata.fidShooters
        self.date = datetime.datetime.fromisoformat(csvdata.shottimestamp)
        self.competition = csvdata.fidCompetitions
        if type(csvdata.shotdata) == str:
            self.shotdata = csvdata.shotdata.split()
        else:
            self.shotdata = csvdata.shotdata
        self.shot={}
        self.practice = False
        self.uuid = csvdata.uuid.lower()
# csvdata = 
#idShots;fidShooters;shotdata;fidCompetitions;shottimestamp;uuid;hash

# shotodata = 
# shootingrange=""1""   shootersid=""3""   shot=""11"" shotcount=""10"" run=""2"" isvalid=""true""
# ishot=""true"" iswarm=""false"" x=""-263"" y=""-1302"" teiler=""1328.2"" disktyp=""lp"" 
# weaponstype=""lp"" dummy=""false"" shotTime=""1665694986668"" tlstatus=""0"" tltime=""423377""
#  menuid=""1000_00100030006"" datetime=""13.10.2022 19:41:13"" isinnerten=""false"" commentvalid=""""
#  valuation="""" flexCompetitionId=""0"" innerten="""" winkel=""191""
#  uuid=""9e674ad5-5a68-4c43-971c-8bd699ca6fa4"" full=""9"" dec=""9,3"" remark="""">93</shot>

# json data = 
#  'shootingrange=""11""', 'shootersid=""38""', 'shot=""36""', 'shotcount=""35""', 'run=""2""',
#  'isvalid=""true""', 'ishot=""true""', 'iswarm=""false""', 'x=""276""', 'y=""273""', 'teiler=""388.2""',
#  'disktyp=""lg""', 'weaponstype=""lg""', 'dummy=""false""', 'shotTime=""1678394736572""',
#  'tlstatus=""0""', 'tltime=""5060065""', 'menuid=""1000_00100020006""', 'datetime=""09.03.2023',
#  '21:11:17""', 'isinnerten=""false""', 'commentvalid=""""', 'valuation=""""','flexCompetitionId=""0""',
#  'innerten=""""', 'winkel=""45""','uuid=""50efcbb5-8bd9-44f1-afb9-7e4296c86eda""', 'full=""9""', 
# 'dec=""9,4""', 'remark="""

        if type(self.shotdata) == list:
            for s in self.shotdata[1:-1]:
                if "=" not in s:
                    continue
                k,v = s.split("=")
                self.shot.update({k:v.strip("\"")})
        else:
            self.practice = True
#            print(f"jsonshot: {self.shotdata}")
            self.shot['disktyp'] = self.shotdata['DiscType'].lower()
            self.shot['teiler'] = self.shotdata['Distance']
            self.shot['x'] = self.shotdata['X']
            self.shot['y'] = self.shotdata['Y']
            self.shot['shot'] = self.shotdata['Count']
            self.shot['full'] = self.shotdata['FullValue']
            self.shot['dec'] = self.shotdata['DecValue']

#            for key in ['shootingrange']

    def __repr__(self):
        return f"Shot of {self.shooter} @ {self.date}: {self.shot['dec']}"
        
    def shooter(self):
        return self.shooter

    def full(self):
        return int(self.shot['full'])

    def dec(self):
        return float(self.shot['dec'].replace(",","."))

    def pos(self):
        return (self.shot['x'], self.shot['y'])
    
    def teiler(self):
        return float(self.shot['teiler'])

    def disktype(self):
        return self.shot['disktyp']
    
    def set_practice(self):
        self.practice = True
    
    def is_practice(self):
        return self.practice

    def __str__(self):
        return f"Shot of Shooter {self.shooter} @ {self.date}: #{self.shot['shot']}, Full: {self.shot['full']}, dec: {self.shot['dec']} - teiler: {self.shot['teiler']} Wettbewerb: {self.competition}"


class Shots():

    def __init__(self, shots_csv=None, user_shots=True):
        self.shots = []
        self.practice_shots = []   # all non-competition shots. no series or sessions recording
        self.sessions = []
        self.override_sessions = []
        self.series = []
        self.competitions = {}
        self.last = datetime.datetime.fromtimestamp(0)
        self.uuids = {}
        self.shots_csv = shots_csv
        self.usershots = user_shots

        if shots_csv is not None:
            self.csvdata = shots_csv
            for csvline in self.csvdata.lines:
                shot = Shot(csvline)
                self.add_shot(shot)


    def add_shot(self, shot):
        if shot.uuid in self.uuids:
            print("shot exists")
            return False


        # use new session
        if self.usershots:
            pause = (shot.date - self.last).total_seconds()
            if pause > SESSION_BREAK: 
                self.series.append([])
                self.sessions.append([])
            else:
                if len(self.sessions[-1]) >= 30:
                    shot.set_practice()

            self.last = shot.date

            if shot.is_practice(): 
                self.practice_shots.append(shot)

            else:
                if len(self.series[-1]) >= 10:
                    self.series.append([])

                if shot.competition not in self.competitions:
                    self.competitions[shot.competition] = [shot]
                else:
                    self.competitions[shot.competition].append(shot)

                

                if len(self.sessions[-1]) >= 30:
                    self.practice_shots.append(shot)
                
                self.shots.append(shot)
                self.series[-1].append(shot)
                self.sessions[-1].append(shot)
        else:
            self.shots.append(shot)
#        else:
#        self.uuids.update({shot.uuid: shot})
        
        # ToDo: change the hard coded 30
        # special Waldemar bescheiss prevention
#        print(self.sessions[-1])
#        self.sessions[-1] = self.sessions[-1][:30]

        return True

    def forecast_sessions(self, history_sessions=3, forecast_sessions=3, fc_type='shotbased'):
        if fc_type == 'simple':
            return self._simple_ses_forecast(history_sessions, forecast_sessions)
        elif fc_type == 'shotbased':
            return self._shotbased_ses_forecast(history_sessions, forecast_sessions)
        else:
            # default forecast
            return self._simple_ses_forecast(history_sessions, forecast_sessions)


    def _shotbased_ses_forecast(self, history_sessions, forecast_sessions):
        maxdec = 10.9
        # more complex
        # over history_sessions
        #   for all shots
        #     check evolution from shot before to current shot, based on max value (10.9)
        #     summarize and average per session

        # produce all the improvements
        ses_improvements = []
        for ses_no in range(1,len(self.sessions)):
            improvements = [0 for i in range(len(self.sessions[ses_no]))]
            for shot_no in range(len(self.sessions[ses_no])):
                curshot = self.sessions[ses_no][shot_no].dec()
                curshot_frac = curshot / maxdec
#                print(ses_no-1, shot_no)
                oldshot_frac = self.sessions[ses_no-1][shot_no].dec() / maxdec
                improvement = (maxdec * (curshot_frac - oldshot_frac))
                improvements[shot_no] = improvement
            ses_improvements.append(improvements)


        ses_sums = [sum([shot.dec() for shot in ses]) for ses in self.sessions]
        ses_index = len(self.sessions) - history_sessions

        # for every week to forecast
        for fc in range(forecast_sessions):
            # for every shot in the session
            cur_ses = self.sessions[ses_index]

            shots_imp = []
            shots_fc = []
            # for shot in current session
            print("sessin range:", ses_index, ses_index+history_sessions)
            for shot_no in range(len(cur_ses)):
                # average improvement for curent shot
                shot_imp = 0

                #  add up the shot improvements over the last sessions, and append the average iprovement per session
                for i in range(ses_index,ses_index+history_sessions):
                    shot_imp += ses_improvements[i-1][shot_no]
                shots_imp.append(shot_imp/history_sessions)

            ses_index += 1

            # add to list of ses_improvements, so it can be used iteratively after 
            ses_improvements.append(shots_imp)
            print([f"{i:.1f}" for i in shots_imp])
            print("avg shots improvement", sum(shots_imp)/len(shots_imp))

            # calculate average session over the sessions to look at
#            avg_ses = sum([ses_sums[i] for i in range (len(ses_sums)-history_sessions, len(ses_sums))]) / history_sessions

            # add to list of sessions sums
#            ses_sums.append(avg_ses + (sum(shots_imp)))
            ses_sums.append(ses_sums[-1] + sum(shots_imp) )
#            print(ses_sums)
#            print([sum(i) for i in ses_improvements])

        return ses_sums[-forecast_sessions:]
        


    def _simple_ses_forecast(self, history_sessions, forecast_sessions):
        # super simple for poc
        ses_sums = [self.session_dec(i) for i in range(len(self.sessions)-history_sessions, len(self.sessions))]

#        print("Len sums", len(ses_sums))
        # for the 
        for future in range(forecast_sessions):
            shot_sum = sum(ses_sums[-history_sessions:]) / history_sessions
            ses_sums.append(shot_sum)
        return ses_sums[-forecast_sessions:]

    def _relative_ses_forecast(self, history_sessions, forecast_sessions):
        # super simple for poc
        max_ses_sum = 10.9*30
        ses_sums = [self.session_dec(i) for i in range(len(self.sessions)-history_sessions, len(self.sessions))]

#        print("Len sums", len(ses_sums))
        # for the 
        for future in range(forecast_sessions):
            shot_sum = sum(ses_sums[-history_sessions:]) / history_sessions
            ses_sums.append(shot_sum)
        return ses_sums[-forecast_sessions:]


    def average(self, weeks=4):
        shot_avg=[0 for i in range(30)]
        for shotno in range(30):
            shot_avg[shotno] = sum([s[shotno].dec() for s in self.sessions[-weeks:]]) / weeks

        print([sum([shot.dec() for shot in s]) for s in self.sessions[-weeks:]])
        print(sum(shot_avg))
        print(shot_avg)

    def data_source_date(self):    
        return self.shots[-1].date
    
    def num_shots(self):
        return len(self.shots)

    def num_practice_shots(self):
        return len(self.practice_shots)

    def last_shot(self):
        return self.shots[-1].date

    def first_shot(self):
        return self.shots[0].date
    
    def session_dec(self, ses_no):
        return sum([shot.dec() for shot in self.sessions[ses_no]])

    def print_stats(self):
        if self.usershots:
            self.print_user_stats()
        else:
            print("Not implemented yet!")

    def add_override(self, sessions):
        self.override_sessions = sessions

    def get_best_sessions(self, limit=0):
        # ToDo - mark override sessions with a little (M) (manual)
        ses = sorted([sum([x.dec() for x in i]) for i in self.sessions] + self.override_sessions)


        if limit != 0:
            ses = ses[:limit]
        return ses


    def sort(self):
        self.shots.sort(key=lambda x: x.date)

    def print_user_stats(self):
        if len(self.shots) == 0:
            print ("Keine Schuesse.")
            return

        stats = {}
        alle = sorted([shot.dec() for shot in self.shots], reverse=True)
        best_shot = min([shot.teiler() for shot in self.shots])
        print (f"Erster Schuss: {self.first_shot()}        \t  Letzter Schuss: {self.last_shot()}")
        print (f"Anzahl Schüsse: {len(alle)}    \t  Bester Teiler: {best_shot}", end="\t")
        print (f"  Anz. Wettbewerbe: {len(self.sessions)}\t  Anzahl Serien: {len(self.series)}", end="\t")
        print (f"Anzahl Probeschüsse: {self.num_practice_shots()}")
        stats['shot'] = {'first': self.first_shot(),
                           'last': self.last_shot(),
                           'best_teiler': best_shot,
                           'best_dec': alle[0],
                           'worst_dec': alle[-1],
                           'avg_dec': sum(alle)/len(alle),
                           'count': len(alle),
                           'top10': alle[:10]}

        series_sum = [sum([x.dec() for x in i]) for i in self.series]
        series = sorted(series_sum)
        print (f"Serien:          ", end="\t")
        print (f"  Beste        : {series[-1]:.2f}", end="\t")
        print (f"  Schlechteste : {series[0]:.2f}", end="\t")
        print (f"  Durchschnitt : {sum(series)/len(series):.2f}", end="\t")
        print (f"  Top10 : {', '.join([f'{i:.1f}' for i in series[::-1][:10]])}")
        stats['series'] = {'best': series[-1],
                           'worst': series[0],
                           'count': len(self.series),
                           'avg': sum(series)/len(series),
                           'top10': [s for s in series[::-1][:10]]}

#        sessions_sum = [sum([x.dec() for x in i]) for i in self.sessions]
#        sessions_sum.extend(self.get_override_sessions())
        sessions= self.get_best_sessions()
#        sessions = sorted(sessions_sum)
        print (f"Wettbewerbe      ", end="\t")
        print (f"  Beste        : {sessions[-1]:.2f}", end="\t")
        print (f"  Schlechteste : {sessions[0]:.2f}", end="\t")
        print (f"  Durchschnitt : {sum(sessions)/len(sessions):.2f}", end="\t")
        print (f"  Liste : {', '.join([f'{i:.1f}' for i in sessions[::-1]])}")
        stats['sessions'] = {'best': sessions[-1],
                           'worst': sessions[0],
                           'count': len(self.sessions),
                           'avg': sum(sessions)/len(sessions),
                           'top10': [s for s in sessions[::-1]][:10]}

        print (f"Alle Treffer:        ", end="\t")
        print (f"  Bester       : {alle[0]}", end="\t")
        print (f"  Schlechtester: {alle[-1]}", end="\t")
        print (f"  Durchschnitt : {sum(alle)/len(alle):.2f}")

        # 95% percentile.
        ptile_num = len(alle)//20
        ptile = sorted([shot.dec() for shot in self.shots], reverse=True)[:min(-1,-ptile_num)]
        print (f"Oberes 90er Perzentil:", end="\t")
        print (f"  Bester       : {ptile[0]}", end="\t")
        print (f"  Schlechtester: {ptile[-1]}", end="\t")
        print (f"  Durchschnitt : {sum(ptile)/len(ptile):.2f}")

        ptile = ptile[ptile_num:]
        print (f"Volles 90er Perzentil:", end="\t")
        print (f"  Bester       : {ptile[0]}", end="\t")
        print (f"  Schlechtester: {ptile[-1]}", end="\t")
        print (f"  Durchschnitt : {sum(ptile)/len(ptile):.2f}")  

        deltas = []
        timings = [shot.date for shot in sorted(self.shots, key=lambda x: x.date)]
        for i in range(len(timings)-1):
            timediff = (timings[i+1] - timings[i]).total_seconds()
            # only for timings, eliminate pause between shootings
            if timediff < 3600:
                deltas.append(timediff)
        deltas = sorted(deltas)
        print (f"Timings:             ", end="\t")
        print (f"  Schnellster  : {deltas[0]}", end="\t")
        print (f"  Langsamster  : {deltas[-1]}", end="\t")
        print (f"  Durchschnitt : {sum(deltas)/len(deltas):.2f}")  
        stats['timings'] = {'fastest': deltas[0],
                            'slowest': deltas[-1],
                            'avg': sum(deltas)/len(deltas)}
        
        return stats

    def add_json_shot(self, rawline):
        json_data = json.loads(rawline)

        if json_data['MessageVerb'] == 'Shot':
            print(".bla")

            c = json_data['Objects'][0]
            if c['UUID'].lower() in self.uuids:
                return False
            shooter = c['Shooter']
            if shooter is None or shooter['Identification'] == '':
                return False
            # unsere competition is 'None' - wenn nicht, exit
            # ToDo
            if c['Competition'] is not None:
                return False
#            print(c)
            #idShots;fidShooters;shotdata;fidCompetitions;shottimestamp;uuid;hash
#            print(c['ShotDateTime'])
            shot_time = datetime.datetime.strptime(c['ShotDateTime'], "%Y-%m-%d %H:%M:%S.000").isoformat()
#            print(shot_time)
            csv_shot = { 'idShots': 0,
                        'fidShooters': int(c['Shooter']['Identification']),
                        'shotdata': c,
                        'fidCompetitions': None,
                        'shottimestamp': shot_time,
                        'uuid': c['UUID'].lower(),
                        'shot_source': 'json'}

            self.add_shot(Shot(csv.CSVLine(csv_shot)))


            if c['Shooter'] is not None:
                shooter_string = f"{c['Shooter']['Firstname']} {c['Shooter']['Lastname']} ({c['Shooter']['Identification']})"
            else:
                return
                shooter_string = "-anonym-"
            if c['MenuItem'] is not None:
                menu_string = f"{c['MenuItem']['MenuPointName']} {c['MenuItem']['MenuID']}"
            else:
                return
                menu_string = "-unbekannt-"
        else:
            return False
#        There are also message verbs 'Result' and 'Series', none of them are used by us
        # if json_data['MessageVerb'] == 'Result':
        #     return
        #     c = json_data['Objects'][0]
        #     if c['Competition'] is not None:
        #         print(f"Competition: {c['Competition']['Name']} Name: {c['Shooter']['Firstname']} {c['Shooter']['Lastname']} ({c['Shooter']['Club']['Name']}) Ergebnis: {c['DecimalValue']}")
        #     else:
        #         print(f"-Anonym- Ergebnis: {c['DecimalValue']}")
        # elif json_data['MessageVerb'] == 'Series':
        #     return
        #     c = json_data['Objects'][0]
        #     if c['Competition'] is not None:
        #         print(f"Serie Range:{json_data['Ranges']} Wettbewerb:{c['Competition']['Name']}, {c['Shooter']['Firstname']} {c['Shooter']['Lastname']} ({c['Shooter']['Club']['Name']}) Ergebnis:{c['DecimalValue']}")
        #     else:
        #         if c['Shooter'] is not None:
        #             print(f"Serie Range:{json_data['Ranges']} -kein Wettbewerb-, {c['Shooter']['Firstname']} {c['Shooter']['Lastname']} ({c['Shooter']['Club']['Name']}) Ergebnis:{c['DecimalValue']}")
        #         else:
        #             print(f"Serie Range:{json_data['Ranges']} -kein Wettbewerb-, -Anonymer Schuetze-, Ergebnis:{c['DecimalValue']}")