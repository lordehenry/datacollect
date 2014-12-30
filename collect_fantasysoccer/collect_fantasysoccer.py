#!/usr/bin/env python

# A command line tool to collect soccer and fantasy soccer data for the English Premier League.
# Tested in Python 3
#
# Sebastian Raschka, 2014 (http://sebastianraschka.com)
#
# Last updated: 12/29/2014
#
# This work is licensed under a GNU GENERAL PUBLIC LICENSE Version 3
# Please see the GitHub repository (https://github.com/rasbt/datacollect) for more details.
#
#
#
# For help, execute
# ./collect_fantasysoccer.py --help


import pandas as pd
from bs4 import BeautifulSoup
import bs4
import requests
import os
import time

class SoccerData(object):
    def __init__(self):
        self.df_general_stats = None
        self.df_team_standings = None
        self.df_injury_data = None
        self.home_away = None
        self.player_form = None
    
    def get_all(self):
        self.get_general_stats()
        self.get_team_standings()
        self.get_injury_data()
        self.get_home_away_data()
        self.get_player_form_data()
        
        
    def to_csv(self, target_dir, print_completed=True):
        data = [self.df_general_stats, self.df_team_standings, 
                self.df_injury_data, self.home_away, self.player_form]
        assert(df is not None for df in data)
        
        today = time.strftime('%Y%m%d')
        if not os.path.isdir(target_dir):
            os.mkdir(target_dir)
            
        names = ['dreamteamfc', 'espn', '365stats', 'transfermarkt', 'telegraph']    
            
        for df, name in zip(data, names):
            name = os.path.join(target_dir, '%s_%s.csv' %(name, today))
            df.to_csv(name, index=False)
            if print_completed:
                print('%s written' %name)
                
        return True
            
    
    def get_general_stats(self, print_out=True):
        
        if print_out:
            print('Getting general statistics from dreamteamfc.com ...')
        
        # Download general statistics
        player_dict = {}

        url = 'https://www.dreamteamfc.com/statistics/players/ALL/'
        r  = requests.get(url)
        soup = BeautifulSoup(r.text, 'html5lib') 
        # Note: html5lib deals better with broken html than lxml

        name_list = []

        for td in soup.findAll('td', { 'class' : "tabName" }):
            name = td.text.split('Statistics')[-1].strip()
            if name:
                name_list.append(name)
                res = [i.text for i in td.next_siblings if isinstance(i, bs4.element.Tag)]
                position, team, vfm, value, points = res
                value = value.strip('m')
                player_dict[name] = [name, position, team, vfm, value, points]
                
        df = pd.DataFrame.from_dict(player_dict, orient='index')
        df.columns = ['name', 'position', 'team', 'vfm', 'value', 'pts']
        df[['vfm','value']] = df[['vfm','value']].astype(float)
        df[['pts']] = df[['pts']].astype(int)
        
        # Add injury and card information
        
        df['status'] = pd.Series('', index=df.index)
        df['description'] = pd.Series('', index=df.index)
        df['returns'] = pd.Series('', index=df.index)
        
        url = 'https://www.dreamteamfc.com/statistics/injuries-and-cards/ALL/'
        r  = requests.get(url)
        soup = BeautifulSoup(r.text, 'html5lib')

        name_list = []

        for td in soup.findAll('td', { 'class' : 'tabName2' }):
            name = td.text.split('stats')[-1].strip()
            if name:
                name_list.append(name)
                res = [i.text for i in td.next_siblings if isinstance(i, bs4.element.Tag)]
                position, team, status, description, returns = res
                df.loc[df.index==name,['status', 'description', 'returns']] = status, description, returns
        
        
        # Add player form information
        
        df['month_pts'] = pd.Series(0, index=df.index)
        df['week_pts'] = pd.Series(0, index=df.index)
        
        url = 'https://www.dreamteamfc.com/statistics/form-guide/all'
        r  = requests.get(url)
        soup = BeautifulSoup(r.text, 'html5lib')

        name_list = []

        for td in soup.findAll('td', { 'class' : 'tabName' }):
            name = td.text.strip()
            if name:
                name_list.append(name)
        
                res = [i.text for i in td.next_siblings if isinstance(i, bs4.element.Tag)]
                try:
                    month_pts, week_pts = float(res[-2]), float(res[-1])
                    df.loc[df.index==name, ['month_pts', 'week_pts']] = month_pts, week_pts
                except ValueError:
                    pass
                    
        # Reordering the columns

        df = df[['name', 'position', 'team', 'vfm', 'value', 'pts', 'month_pts', 
                 'week_pts', 'status', 'description', 'returns']]
        
        self.df_general_stats = df
        
        return df
        
        
            
    def get_team_standings(self, print_out=True):
        
        if print_out:
            print('Getting team standings from espnfc.com ...')
        
        team_dict = {}

        url = 'http://www.espnfc.com/barclays-premier-league/23/table'
        r  = requests.get(url)
        soup = BeautifulSoup(r.text, 'html5lib') 
        # Note: html5lib deals better with broken html than lxml

        for td in soup.findAll('td', { 'class' : 'pos' }):
            rank = int(td.text)
            res = [i.text for i in td.next_siblings if isinstance(i, bs4.element.Tag) and i.text!='\xa0']
            team = res[0].strip()
            values = [int(i) for i in res[1:]]
            team_dict[team] = [rank] + values
        
        df = pd.DataFrame.from_dict(team_dict, orient='index')
        cols = ['Pos','P_ov','W_ov','D_ov','L_ov','F_ov','A_ov',
                    'W_hm','D_hm','L_hm','F_hm','A_hm', 'W_aw',
                    'D_aw','L_aw','F_aw','A_aw','GD','PTS']
        df.columns = cols
        df = df.sort('Pos')
        df['team'] = df.index
        df = df[['team']+cols] # reorder columns
        
        self.df_team_standings = df
        
        return df
        
        
        
    def get_injury_data(self, print_out=True):
    
        if print_out:
            print('Getting injury data from 365stats.com ...')
        
        injury_dict = {}

        url = 'http://365stats.com/football/injuries'
        r  = requests.get(url)
        soup = BeautifulSoup(r.text, 'html5lib') 
        # Note: html5lib deals better with broken html than lxml

        for td in soup.findAll('td', { 'nowrap' : 'nowrap' }):
            name = td.text.split()
            player_info = ['%s, %s' % (' '.join(name[1:]), name[0])]
            for i in td.next_siblings:
                if isinstance(i, bs4.Tag):
                    player_info.append(i.text)
            injury_dict[player_info[0]] = player_info[1:3]
            
        df = pd.DataFrame.from_dict(injury_dict, orient='index')
        df.columns=['injury', 'returns']
        df['name'] = df.index
        
        self.df_injury_data = df
        
        return df



    def get_home_away_data(self, print_out=True):
        if print_out:
            print('Getting home/away data from transfermarkt.com ...')
        
        
        # Downloading and parsing the data into a Python dict

        url = 'http://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1'
        r  = requests.get(url)
        soup = BeautifulSoup(r.text, 'html5lib') 
        # Note: html5lib deals better with broken html than lxml

        # Find tab for the upcoming fixtures
        tab = 'spieltagtabs-2'
        div = soup.find('div', { 'id' : tab })
        tit = div.findAll('a', { 'class' : 'ergebnis-link' })
        if len(tit) > 0:
            tab = 'spieltagtabs-3'

        # Get fixtures
        home = []
        away = []

        div = soup.find('div', { 'id' : tab })
        for t in div.findAll('td', { 'class' : 'text-right no-border-rechts no-border-links' }):
            team = t.text.strip()
            if team:
                home.append(team)
        for t in div.findAll('td', { 'class' : 'no-border-links no-border-rechts' }):
            team = t.text.strip()
            if team:
                away.append(team)

        df = pd.DataFrame(home, columns=['home'])
        df['away'] = away
        self.home_away = df
        return df


    def get_player_form_data(self, print_out=True):
        if print_out:
            print('Getting player form data from telegraph.co.uk ...')
        
        
        url = 'https://fantasyfootball.telegraph.co.uk/premierleague/players/'
        r  = requests.get(url)
        soup = BeautifulSoup(r.text, 'html5lib') 
        # Note: html5lib deals better with broken html than lxml

        player_dict = {}

        for t in soup.findAll('td', { 'class' : 'first' }):
            player = t.text.strip()
            player_dict[player] = []
            for s in t.next_siblings:
                if isinstance(s, bs4.Tag):
                    player_dict[player].append(s.text)

        # parse the player dictionary
        df = pd.DataFrame.from_dict(player_dict, orient='index')

        # make name column
        df['name'] = df.index

        # assign column names and reorder columns
        df.columns = ['team', 'salary', 'pts/salary', 'week_pts', 'total_pts', 'name']
        df = df[['name', 'team', 'salary', 'pts/salary', 'week_pts', 'total_pts']]

        # parse data into the right format
        df['salary'] = df['salary'].apply(lambda x: x.strip('£').strip(' m'))
        df[['salary', 'pts/salary']] = df[['salary', 'pts/salary']].astype(float)
        df[['week_pts', 'total_pts']] = df[['week_pts', 'total_pts']].astype(float)
    
    
        url = 'https://fantasyfootball.telegraph.co.uk/premierleague/formguide/'
        r  = requests.get(url)
        soup = BeautifulSoup(r.text, 'html5lib') 
        # Note: html5lib deals better with broken html than lxml

        df['6week_pts'] = pd.Series(0, index=df.index)

        for t in soup.findAll('td', { 'class' : 'first' }):
            player = t.text.strip()
            if player:
                week6 = t.parent.find('td', { 'class' : 'sixth last' })
                df.loc[df['name'] == player, '6week_pts'] = week6.text
    

        self.player_form = df
        return df

        
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
            description='A command line tool to download current Premier League (Fantasy) Soccer data.',
            formatter_class=argparse.RawTextHelpFormatter,
    epilog='Example:\n'\
                './collect_fantasysoccer.py -o ~/Desktop/matchday_17')

    parser.add_argument('-o', '--output', help='Output directory.', required=True, type=str)
    parser.add_argument('-v', '--version', action='version', version='v. 1.0')
    
    args = parser.parse_args()

    epl_data = SoccerData()
    epl_data.get_all()
    epl_data.to_csv(args.output)
    
