# -*- coding: utf-8 -*-
"""
Created on Sun May 30 15:47:37 2021

@author: user
"""
import pandas as pd
import numpy as np
import requests
from pandas.io.json import json_normalize
import time

"get 2010-2020 all games result"
# def gamesData(page):
#     start = time.time()
#     games = []
#     for num in range(1, page+1):
#         response = requests.get(
#                 'https://www.balldontlie.io/api/v1/games',
#                 params = {
#                         'page':num,
#                         'per_page':100,
#                         'seasons[]':[range(2010,2020)]
#                     }
            
#             )
#         data = response.json() #transfer data to json type
#         games.append(pd.DataFrame(json_normalize(data["data"], sep="_"))) #json_normalize JSON data into a flat table
#     print("download time: ", (time.time() - start)/60, "min")
#     df = pd.concat(games)
#     return df
# df = gamesData(128)
df = pd.read_csv(r".\data.csv")

"define win & loss team column, and build select win/loss team func"

def win(x):
    if x["home_team_score"] > x["visitor_team_score"]:
        return x["home_team_full_name"]
    elif x["home_team_score"] < x["visitor_team_score"]:
        return x["visitor_team_full_name"]
    else:
        return np.nan
def loss(x):
    if x["home_team_score"] < x["visitor_team_score"]:
        return x["home_team_full_name"]
    elif x["home_team_score"] > x["visitor_team_score"]:
        return x["visitor_team_full_name"]
    else:
        return np.nan
df["win_team"] = df.apply(win, axis = 1) #axis = 1 apply each row
df["loss_team"] = df.apply(loss, axis = 1)

"count each team win/loss games at each season"

def win_loss_count(df, playoff):
    #regular or playoff
    df = df[df["postseason"] == playoff]
    # Find teams at which conference 
    #.size() to count each group number
    team_conference = df.groupby(["home_team_conference", "home_team_full_name"]).size().reset_index().drop(columns = 0)
    
    # Calculate the count of win each team
    win_team_count = df.groupby(["season", "win_team"]).size().reset_index().rename(columns = {"win_team":"team", 0:"win_count"})
    
    # Calculate the count of loss each team
    loss_team_count = df.groupby(["season", "loss_team"]).size().reset_index().rename(columns = {"loss_team":"team", 0:"loss_count"})
    
    merge_win_loss = pd.merge(left=win_team_count, right=loss_team_count , on=['season', 'team']) #pd.merge(left, right, how....)
                        
    result = pd.merge(left=win_team_count, right=loss_team_count , on=['season', 'team']).\
            merge(team_conference, left_on='team', right_on='home_team_full_name')
    return result, team_conference, win_team_count, loss_team_count, merge_win_loss

df_regular_season = win_loss_count(df, playoff=False)[0]
df_post_season = win_loss_count(df, playoff=True)[0]


result, team_conference, win_team_count, loss_team_count, merge_win_loss = win_loss_count(df, playoff = False)


import dash # 建立dash
import dash_table # 要轉成資料框必用
from dash.dependencies import Input, Output # 在callback時使用
import dash_core_components as dcc # 製作Dashboard上的功能
import dash_html_components as html # 製作Dashboard網頁
import plotly.graph_objs as go # 畫各種圖

season_list = result["season"].unique().tolist()
team_list = result["team"].unique().tolist()
app = dash.Dash()
app.layout = html.Div([
    html.Div([
            dcc.Dropdown(
                id = "season_select",
                options = [{'label': i, 'value': i} for i in season_list],  #list of dicts
                placeholder = "select a year", #The placeholder property allows you to define default text shown when no value is selected
                searchable = False, #To prevent "searching" the dropdown value, just set the searchable property to False
                value = 2019, #The value of the input.
                ),
            dcc.Dropdown(
                id = "team_select",
                options = [{'label': i, 'value': i} for i in team_list],
                placeholder = "select a team", #The placeholder property allows you to define default text shown when no value is selected
                searchable = False, #To prevent "searching" the dropdown value, just set the searchable property to False
                value = 'Golden State Warriors',
                ),
            dcc.Graph(
                id = "home_guest_score"
                ),
            ], style = {'width':'45%', 'display':'inline-block'}),
    html.Div([
            dash_table.DataTable(
                id = "raw_data",
                columns = [{'name':i, 'id':i} for i in df_regular_season.drop(columns = ["home_team_full_name"], axis = 1)],
                data = df_regular_season.to_dict('records'),#‘records’ : list like [{column -> value}, … , {column -> value}]
                page_current = 0,
                page_size = 15,
                page_action = 'custom',
                style_cell={'height': 40},
                )],style = {'width': '50%', 'display': 'inline-block',  'float': 'right', 'height':'100%'})
        ])

@app.callback(
    Output('home_guest_score', 'figure'),
    [Input('season_select', 'value'),
    Input('team_select', 'value')])
def plot_chart(season, team):
    #fliter data - to find out selected team record no matter win or loss on specific season
    data_season_team = df[(df['season']==season) & ((df['home_team_full_name']==team) | (df['visitor_team_full_name']==team))]
    
    #plot fig
    figure = {
        'data':[
                go.Scatter(
                        x = data_season_team["home_team_score"],
                        y = data_season_team["visitor_team_score"],
                        text=['Home:{:30} Guest:{:30}'.format(home, guest) for home, guest in data_season_team[['home_team_full_name', 'visitor_team_full_name']].values],
                        mode='markers',
                        hovertemplate='<i>%{text}<i>'+
                                      '<i>%{x} v.s. %{y}<i>')],

        'layout':go.Layout(
                        xaxis = dict(range = [df['home_team_score'].min(), df['home_team_score'].max()], 
                                     title = 'Home team score'),
                        yaxis = dict(range = [df['visitor_team_score'].min(), df['visitor_team_score'].max()],
                                     title = 'guest team score'),
                        height=600                   
                    )                
        }
    return figure

@app.callback(
    Output('raw_data', 'data'),
    [Input('season_select', 'value'),
     Input('raw_data', 'page_current'),
     Input('raw_data', 'page_size')])
def season_table(value, page_current, page_size):
    data = df_regular_season[(df_regular_season['season'] == value)]
    data_season = data.groupby(['season', 'home_team_conference', 'team'], as_index=False)[['win_count', 'loss_count']].sum()
    data_season_conference = data_season.sort_values(['home_team_conference', 'win_count'], ascending=[True, False])
    # Find Season and Set Pages
    return data_season_conference.iloc[
        page_current*page_size: (page_current+1)*page_size
    ].to_dict('records')



# if __name__ == "__main__":
#     app.run_server()
app.run_server()
    
    
    
    
    
    
    
    
    
    
    
    



















