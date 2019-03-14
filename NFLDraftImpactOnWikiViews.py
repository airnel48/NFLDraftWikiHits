# -*- coding: utf-8 -*-
"""
Created on Sun Mar 10 10:23:21 2019

@author: Eric
"""

####1 SCRAPE DATA FROM PRO FOOTBALL REFERENCE.COM
#assistance from: http://savvastjortjoglou.com/nfl-draft.html#Web-Scraping

%matplotlib inline

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from urllib.request import urlopen
from bs4 import BeautifulSoup

# set the URL
draft_2018 = "https://www.pro-football-reference.com/years/2018/draft.htm"
# get html
html = urlopen(draft_2018)
# create the BeautifulSoup object
soup = BeautifulSoup(html, "lxml")

# Extract  necessary values for the column headers from the tableand store them as a list
headers = [th.getText() for th in soup.findAll('tr', limit=2)[1].findAll('th')]
# Add the two additional column headers for the player links
headers.extend(["Player_NFL_Link", "Player_NCAA_Link"])
# The data is found within the table rows of the element with id=draft
# We want the elements from the 3rd row and on
table_rows = soup.select("#drafts tr")[2:] 
type(table_rows)
type(table_rows[0])
table_rows[0] # take a look at the first row
player_list = [td.get_text() for td in row.find_all("th")]
player_list.extend([td.get_text() for td in row.find_all("td")])
def extract_player_data(table_rows):
    """
    Extract and return the the desired information from the td elements within the table rows.
    """
    # create the empty list to store the player data
    player_data = []
    
    for row in table_rows:  # for each row do the following

        # Get the text for each table data (td) element in the row
        # Some player names end with ' HOF'
        # if they do, get the text excluding those last 4 characters,
        # otherwise get all the text data from the table data
        #player_list = [td.get_text()[:-4] if td.get_text().endswith(" HOF") 
        #               else td.get_text() for td in row.find_all("td")]
        player_list = [td.get_text() for td in row.find_all("th")]
        player_list.extend([td.get_text() for td in row.find_all("td")])

        # there are some empty table rows, which are the repeated 
        # column headers in the table
        # we skip over those rows and and continue the for loop
        if not player_list:
            continue

        # Extracting the player links
        # Instead of a list we create a dictionary, this way we can easily
        # match the player name with their pfr url
        # For all "a" elements in the row, get the text
        # NOTE: Same " HOF" text issue as the player_list above
        links_dict = {(link.get_text()[:-4]   # exclude the last 4 characters
                       if link.get_text().endswith(" HOF")  # if they are " HOF"
                       # else get all text, set thet as the dictionary key 
                       # and set the url as the value
                       else link.get_text()) : link["href"] 
                       for link in row.find_all("a", href=True)}

        # The data we want from the dictionary can be extracted using the
        # player's name, which returns us their pfr url, and "College Stats"
        # which returns us their college stats page
    
        # add the link associated to the player's pro-football-reference page, 
        # or en empty string if there is no link
        player_list.append(links_dict.get(player_list[3], ""))

        # add the link for the player's college stats or an empty string
        # if ther is no link
        player_list.append(links_dict.get("College Stats", ""))

        # Now append the data to list of data
        player_data.append(player_list)
        
    return player_data
    
# extract the data we want
data = extract_player_data(table_rows)

# and then store it in a DataFrame
df_2018 = pd.DataFrame(data, columns=headers)
df_2018.head()

####1 IMPORT NFL DRAFT DATA FROM KAGGLE


import kaggle
!kaggle datasets list --tags american football
!kaggle datasets files ronaldjgrafjr/nfl-draft-outcomes
!kaggle datasets download ronaldjgrafjr/nfl-draft-outcomes -f nfl_draft.csv


##1a explore and clean dataset


#limit observations to the most recent year

import numpy as np
import pandas as pd
draft = pd.read_csv("nfl_draft.csv")
draft.head()
maxyear=draft.Year.max()
recentdraft=draft.loc[draft['Year']==draft.Year.max()]
recentdraft.head()

#cut unnecessary columns

recentdraft = recentdraft[['Player_Id','Year','Rnd','Pick','Tm','Player','Position Standard','Age','College/Univ']]
recentdraft.describe()
recentdraft.isna().sum()

#note - missing age for 8 players
#with 32 teams and 7 rounds we should have 224 total picks, but there are 256 in this dataset

pd.set_option('display.max_rows', 50)
pd.set_option('display.max_columns', 10)
tabs=['Year','Rnd','Tm','Position Standard','Age']
for column in tabs:
    tab = pd.crosstab(index=recentdraft[column],  # Make a crosstab
                              columns="count")      # Name the count column
    print(tab)
    
#apparently there are 32 picks in the first two rounds but later rounds have 35 - 41 picks
#note some positions, such as Punter, have only a single observation


####2 COLLECT WIKIPEDIA PAGE VIEWS FOR EACH PLAYER


import mwviews
from mwviews.api import PageviewsClient

# Sends a descriptive User-Agent header with every request
#p = PageviewsClient(user_agent="<ene> Selfie, Cat, and Dog analysis")

#2a retrieve page views for each player


#Error occurs as Kaggle and Wikipedia handle some initials inconsistently
#Manually correcting this issue

name_correction = {'A.J. Cann':'A. J. Cann',
                   'JJ Nelson':'J. J. Nelson',
                   'B.J. Dubose':'B. J. Dubose', 
                   'Rory \'Busta\' Anderson':'Rory Anderson'
                  }
recentdraft = recentdraft.replace(name_correction)

#2015 NFL draft took place from April 30 to May 2
#Collect more data than needed at beginning. Dates will be pared down after exploratory analysis

#build dataframe format
wiki_views = pd.DataFrame.from_dict(p.article_views('en.wikipedia', recentdraft.at[0,'Player'], granularity='daily', start='20140101', end='20151231'))
#set column name for players
wiki_views['Player'] = wiki_views.index
#remove data
wiki_views = wiki_views[0:0]

#populate table by with wikipedia stats for each player
for i in recentdraft.index:
    wiki_views = wiki_views.append(pd.DataFrame.from_dict(p.article_views('en.wikipedia', recentdraft.at[i,'Player'], granularity='daily', start='20140101', end='20151231')))

wiki_views = pd.melt(wiki_views, id_vars=["Player"],var_name="Date", value_name="Views")

#remove underscore that wikipedia enters into player names to ensure we can join tables together later on player name
wiki_views=wiki_views.replace('_', ' ', regex=True)
#fill NAs with 0s for Causal Impact model
wiki_views=wiki_views.fillna(0)

wiki_views.shape
wiki_views.head()
wiki_views.describe()
wiki_views.
wiki_views.groupby(['Player','Date'])['Views'].max()
wiki_views.index

#### 3 CONDUCT CAUSAL IMPACT MEASUREMENT TO IDENTIFY SIGNIFICANT LIFT


from causalimpact import CausalImpact
from statsmodels.tsa.arima_process import arma_generate_sample
import matplotlib
import seaborn as sns

wiki_views.plot(wiki_views['Views'])
wiki_views.plot()
plt.plot(Dates, Highs)


#based on exploration of the data, we will use a pre-period of x
pre_period = [0,69]
wiki_views[400]
wiki_views.loc[ ['c' , 'b'] ,['Age', 'Name'] ]

wiki_views.iloc[484, ]
wiki_views.iloc[545, ]
#based on exploration of the data, we will use a post-period of y
post_period = [71,99]

#### 4 JOIN KAGGLE AND CAUSAL IMPACT DATASETS


#probably don't have to do this until after the causal impact
#draftdata=pd.merge(recentdraft,wiki_views,on='Player')
#draftdata.head()