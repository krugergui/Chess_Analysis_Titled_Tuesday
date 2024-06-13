# landing_area

## games

| Column | Description                  | Data Type |
| ------ | ---------------------------- | --------- |
| \_id   | ID                           | ObjectID  |
| url    | URL that originated the data | string    |
| data   | Raw data                     | string    |

# silver

## games

| Column           | Description                                                                                                                                         | Data Type        |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| \_id             | ID                                                                                                                                                  | ObjectID         |
| url              | URL that originated the data                                                                                                                        | string           |
| source           | From which table of the database this data comes from                                                                                               | string           |
| processed_at     | Time of processing                                                                                                                                  | date             |
| Event            | Self explanatory                                                                                                                                    | string           |
| Site             | Which website does this data originate from                                                                                                         | string           |
| Date             | Self explanatory                                                                                                                                    | string           |
| Round            | Self explanatory                                                                                                                                    | string           |
| White            | Player playing white                                                                                                                                | string           |
| Black            | Player playing black                                                                                                                                | string           |
| Result           | Which player won - 1-0 for white, 0-1 for black or 1/2-1/2 for tie                                                                                  | string           |
| WhiteElo         | Elo of the white player                                                                                                                             | int              |
| BlackElo         | Elo of the black player                                                                                                                             | int              |
| TimeControl      | Time control in seconds (total time + increment)                                                                                                    | string           |
| EndTime          | When did the match ended                                                                                                                            | string           |
| Termination      | Human readable description how the game ended                                                                                                       | string           |
| moves_with_clock | All the moves including the clock                                                                                                                   | string           |
| TotalTime        | Initial time for the players in seconds                                                                                                             | int              |
| Increment        | Increment in the clock after each move in seconds                                                                                                   | int              |
| clock            | How many seconds was the clock displaying at the time of the move                                                                                   | array of ints    |
| move_times       | How long did the player took to make the move                                                                                                       | array of ints    |
| moves            | Chess notation description of the move                                                                                                              | array of strings |
| Upset            | Difference on the player rankings, positive numbers indicate that the weaker player won the game, i.e. an upset, negative numbers indicate no upset | int              |
|                  |                                                                                                                                                     |                  |

## events

| Column         | Description                                            | Data Type                                                     |
| -------------- | ------------------------------------------------------ | ------------------------------------------------------------- |
| \_id           | ID                                                     | ObjectID                                                      |
| date_processed | Date that the data was processed into the silver table | date                                                          |
| Event          | Name of the event                                      | string                                                        |
| results        | How many points did every player achieved              | object with "player name" as keys and "total points" as value |
