# -*- coding: utf-8 -*-
"""
Created on Sun Mar 10 10:23:21 2019

@author: Eric
"""

#import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from urllib.request import urlopen
from bs4 import BeautifulSoup
import mwviews
from mwviews.api import PageviewsClient
from causalimpact import CausalImpact
from statsmodels.tsa.arima_process import arma_generate_sample
import matplotlib
%matplotlib inline
matplotlib.rcParams['figure.figsize'] = (15, 6)


####1 SCRAPE DATA FROM PRO FOOTBALL REFERENCE.COM
#scraping assistance from: http://savvastjortjoglou.com/nfl-draft.html#Web-Scraping


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
#player_list = [td.get_text() for td in row.find_all("th")]
#player_list.extend([td.get_text() for td in row.find_all("td")])
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
#cut unnecessary columns
df_2018.columns
df_2018 = df_2018[['Rnd','Pick','Tm','Player','Pos','College/Univ']]
#explore data
df_2018.head()
df_2018.isna().sum()
df_2018.describe()
#only 257 unique names and most common is 'Player'. Is there a data issue?
#with 32 teams and 7 rounds we should have 224 total picks, but there are 256 in this dataset
tabs=['Rnd','Pick','Tm','Pos']
for column in tabs:
    tab = pd.crosstab(index=df_2018[column],  # Make a crosstab
                              columns="count")      # Name the count column
    print(tab)
#apparently there are 32 picks in the first two rounds but later rounds have 36 - 44 picks
#note some positions such as LS and Kicker only have 1 or 2 observations
df_2018[df_2018.Player == 'Player']
#rows 32, 65, 102, 140, 178, and 223 contain header descriptions instead of unique values. 
#need to remove these observations
df_2018=df_2018[(df_2018.Player!='Player')]
#now let's explore the data again
df_2018[df_2018.Player=='Player']
#counts for each value of Rnd, PIck, Tm, and Position
for column in tabs:
    tab = pd.crosstab(index=df_2018[column],  # Make a crosstab
                              columns="count")      # Name the count column
    print(tab)
df_2018.describe()
#that looks better


####2 COLLECT WIKIPEDIA PAGE VIEWS FOR EACH PLAYER


# Sends a descriptive User-Agent header with every request
p = PageviewsClient(user_agent="<ene> NFL draft analysis")

#2a retrieve page views for each player


#Error occurs as ProFootballReference and Wikipedia handle some initials inconsistently
#Manually correcting this issue

name_correction = {'M.J. Stewart':'M. J. Stewart',
                   'P.J. Hall':'P. J. Hall',
                   'R.J. McIntosh':'R. J. McIntosh'
                  }
df_2018 = df_2018.replace(name_correction)

#2018 NFL draft took place from April 26 to April 28
#Collect more data than needed at beginning. Dates will be pared down after exploratory analysis

#build dataframe format
#wiki_views_t = pd.DataFrame.from_dict(p.article_views('en.wikipedia', df_2018.at[0,'Player'], granularity='daily', start='20170101', end='20181231'))
#Use Jonathan Taylor as a control. 
#He is a top performing freshman from Wisconsin who is not eligible for the draft until 2019
#Considered using a combination of other college players as control, but most do not have a Wiki page
wiki_views_c = pd.DataFrame.from_dict(p.article_views('en.wikipedia', 'Jonathan Taylor (American football)', granularity='daily', start='20170101', end='20181231'))

#remove data
wiki_views_t = wiki_views_c[0:0]

#populate table by with wikipedia stats for each player
for i in df_2018.index:
    wiki_views_t = wiki_views_t.append(pd.DataFrame.from_dict(p.article_views('en.wikipedia', df_2018.at[i,'Player'], granularity='daily', start='20170101', end='20181231')))

#set column name for players
wiki_views_t['Player'] = wiki_views_t.index
wiki_views_c['Player'] = wiki_views_c.index
  
wiki_views_t = pd.melt(wiki_views_t, id_vars=["Player"],var_name="Date", value_name="Views")
wiki_views_c = pd.melt(wiki_views_c, id_vars=["Player"],var_name="Date", value_name="Views")

#remove underscore that wikipedia enters into player names to ensure we can join tables together later on player name
wiki_views_t=wiki_views_t.replace('_', ' ', regex=True)
wiki_views_c=wiki_views_c.replace('_', ' ', regex=True)
#fill NAs with 0s for Causal Impact model
wiki_views_t=wiki_views_t.fillna(0)
wiki_views_c=wiki_views_c.fillna(0)

wiki_views_t.shape
wiki_views_c.shape
wiki_views_t.head()
wiki_views_c.head()
wiki_views_t.describe()
wiki_views_c.describe()


#### 3 PREPARE DATA FOR CAUSAL IMPACT MODELING

draft_round=df_2018[['Player','Rnd']]
wiki_views_ts = pd.merge(wiki_views_t,draft_round,on='Player',how='left')
wiki_views_t1 = wiki_views_ts[wiki_views_ts['Rnd']=='1'].groupby('Date',as_index=False)['Views'].mean()
wiki_views_t2 = wiki_views_ts[wiki_views_ts['Rnd']=='2'].groupby('Date',as_index=False)['Views'].mean()
wiki_views_t3 = wiki_views_ts[wiki_views_ts['Rnd']=='3'].groupby('Date',as_index=False)['Views'].mean()
wiki_views_t4 = wiki_views_ts[wiki_views_ts['Rnd']=='4'].groupby('Date',as_index=False)['Views'].mean()
wiki_views_t5 = wiki_views_ts[wiki_views_ts['Rnd']=='5'].groupby('Date',as_index=False)['Views'].mean()
wiki_views_t6 = wiki_views_ts[wiki_views_ts['Rnd']=='6'].groupby('Date',as_index=False)['Views'].mean()
wiki_views_t7 = wiki_views_ts[wiki_views_ts['Rnd']=='7'].groupby('Date',as_index=False)['Views'].mean()

wiki_views_c=wiki_views_c[['Date','Views']]

inputs1 = pd.merge(wiki_views_t1,wiki_views_c,on='Date',how='left')
inputs2 = pd.merge(wiki_views_t2,wiki_views_c,on='Date',how='left')
inputs3 = pd.merge(wiki_views_t3,wiki_views_c,on='Date',how='left')
inputs4 = pd.merge(wiki_views_t4,wiki_views_c,on='Date',how='left')
inputs5 = pd.merge(wiki_views_t5,wiki_views_c,on='Date',how='left')
inputs6 = pd.merge(wiki_views_t6,wiki_views_c,on='Date',how='left')
inputs7 = pd.merge(wiki_views_t7,wiki_views_c,on='Date',how='left')


#### 4 CONDUCT CAUSAL IMPACT MEASUREMENT TO IDENTIFY SIGNIFICANT LIFT


#draft is april 26 - april 28
pre_period = [pd.to_datetime(date) for date in ["2018-02-05", "2018-04-19"]]
post_period = [pd.to_datetime(date) for date in ["2018-04-26", "2018-05-05"]]
impact = CausalImpact(inputs1, pre_period, post_period)
impact.run()
impact <- CausalImpact(inputs1, pre.period, post.period)
plot(impact)
inputs1['Date']


#error message "upper y"
pd.__version__
statsmodels.__version__
import statsmodels.api as sm 
sm.version.version 
CausalImpact.
df = pd.DataFrame(
    {'y': [150, 200, 225, 150, 175],
     'x1': [150, 249, 150, 125, 325],
     'x2': [275, 125, 249, 275, 250]
    }
)
ci = CausalImpact(df, [0,2], [3,4])
ci.run()


#### 5 CONDUCT ANCOVA UNTIL RESOLUTION IS FOUND FOR THE CAUSAL IMPACT PACKAGE
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from statsmodels.graphics.factorplots import interaction_plot
import matplotlib.pyplot as plt
from scipy import stats

#wiki_views_ts = pd.merge(wiki_views_t,draft_round,on='Player',how='left')

#wiki_views_ts['Date'] = wiki_views_ts.to_datetime(wiki_views_ts['Date'])  

pre = (wiki_views_ts['Date'] >= '2018-02-05') & (wiki_views_ts['Date'] <= '2018-04-19')
post = (wiki_views_ts['Date'] >= '2018-04-26') & (wiki_views_ts['Date'] <= '2018-05-05')

df = df.loc[mask]

predata=wiki_views_ts[['Player','Views','Rnd']].loc[pre].rename(index=str,columns={"Views":"Pre_views"})
predata=predata.groupby(['Player','Rnd'],as_index=False)['Pre_views'].mean()
postdata=wiki_views_ts[['Player','Views','Rnd']].loc[post].rename(index=str,columns={"Views":"Post_views"})
postdata=postdata.groupby(['Player'],as_index=False)['Post_views'].mean()
totdata=pd.merge(predata,postdata,on='Player',how='left')
totdata=totdata.drop(columns='Player')

matplotlib.pyplot.scatter(totdata['Pre_views'], totdata['Post_views'])
matplotlib.pyplot.scatter(totdata[totdata.Rnd=='1']['Pre_views'], totdata[totdata.Rnd=='1']['Post_views'])
matplotlib.pyplot.scatter(totdata[totdata.Rnd=='2']['Pre_views'], totdata[totdata.Rnd=='2']['Post_views'])
matplotlib.pyplot.scatter(totdata[totdata.Rnd=='3']['Pre_views'], totdata[totdata.Rnd=='3']['Post_views'])
matplotlib.pyplot.scatter(totdata[totdata.Rnd=='4']['Pre_views'], totdata[totdata.Rnd=='4']['Post_views'])
matplotlib.pyplot.scatter(totdata[totdata.Rnd=='5']['Pre_views'], totdata[totdata.Rnd=='5']['Post_views'])
matplotlib.pyplot.scatter(totdata[totdata.Rnd=='6']['Pre_views'], totdata[totdata.Rnd=='6']['Post_views'])
matplotlib.pyplot.scatter(totdata[totdata.Rnd=='7']['Pre_views'], totdata[totdata.Rnd=='7']['Post_views'])

formula = 'Post_views ~ Pre_views + Rnd'
lm = ols(formula, totdata).fit()
print(lm.summary())

#RESULTS
#Post_views = 3,024 + 7.2*Pre_views + Rnd
#Rnd2-7 have values of -2320 to -3000 
#Conclusion: all drafted players see a 7x increase in Wiki hits the week after the draft
#First round draft picks see a major additional boost of ~3,000 per day for the week after the draft
#There is no clear difference in results for draft picks between rounds 2 and 7 outside of the 7x of pre wiki hits








pre_period = [pd.to_datetime(date) for date in ["2018-02-05", "2018-04-19"]]

wiki_views_t1 = wiki_views_ts[wiki_views_ts['Rnd']=='1'].groupby('Date',as_index=False)['Views'].mean()

pre1=inputs1[['Views_x']].iloc[400:474,:]
post1=inputs1[['Views_x']].iloc[480:490,:]
test1=pd.merge(pre1,post1,on='Player',how='left')

inputs1=inputs1[['Date','Views_x']]
inputs1['Treatment']='t1'
inputs2=inputs2[['Date','Views_x']]
inputs2['Treatment']='t2'
test12=inputs1.append(inputs2)

matplotlib.pyplot.scatter(inputs1[['Views_x']].iloc[400:474,:], inputs2[['Views_x']].iloc[400:474,:], )
matplotlib.pyplot.scatter(inputs1[['Views_x']].iloc[400:474,:], inputs2[['Views_x']].iloc[400:474,:], )

results = lm(Sale ~ Presale + Treatment)

anova(results)

inputs1[] 
#average of wiki views in pre-period between 2018-02-05 and 2018-04-19
pre1=inputs1[['Views_x']].iloc[400:474,:].mean(axis=0)

#average of wiki views in pre-period between 2018-04-26 and 2018-05-05
post1=inputs1[['Views_x']].iloc[480:490,:].mean(axis=0)

