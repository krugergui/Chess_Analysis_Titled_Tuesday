import streamlit as st

st.title("Dashboard")

st.write("""
         ## Titled Tuesday

Over xxx players from all over the world competing every Tuesday on a 2 and half hours long fight for a money prize but most importantly, the bragging rights to be called the titled Tuesday champion.

In this dashboard I'll present some interesting facts and findings about the titled Tuesday Chess Event. This event happens every week on two editions, an early edition (17:00 CET) and late edition (23:00 CET).

If you'd like to know more about this project and how it works, you can check out the [GitHub repo](https://github.com/krugergui/Chess_Analysis_Titled_Tuesday).

## Most Sucessuful players

The players with most wins in the Titled Tuesday events are the follows:

#ToDo most Sucessuful players

## Who has played the most editions and games

Some players are more regulars than other in the event, the world reining champion Magnus Carlsen sits at the top positions with xxx played editions, but the winner is xxx.

#ToDo Who has played the most editions

## Biggest upset

An upset in chess is characterized by player with a higher rating losing to someone with a way lower rating. This rating can be used to calculate the probabilities of such an upset happening, according to the formula.

$$Pr(A) = \frac{1}{ 10^{ ELODIFF/400 } + 1 }$$

That being sad the bigged upset ever to happen was xxx with xxx on xxxx, with the other biggest upsets shown below.

Also interesting to see is that the top players also have huge upsets, as shown below.

#ToDo Biggest upset

## Number of games played for each edition

In total, over all the editions there were xxx games played, here we take a look on how many games were played over each edition: 

#ToDo Number of games played

#ToDo Conclusions on games played over time

## Difference of winning rate when playing as white

As the first move is always for the white player it is considered advantageous to play as white. Here we see the winning rate for players when playing as white.

#ToDo Difference of winning rate when playing as white.

#ToDo also winrate by difference of rating
         """)
