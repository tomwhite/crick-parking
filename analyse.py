import datetime
import pandas as pd
import re
import traces

# def get_ticket_duration(tariff_description):
#     m = re.match(".+(1 Hour|2 Hour|4 Hour|All Day)", tariff_description)
#     return m.group(1) if m else None


def read_entries_df(csv_file):
    """
    Read entries from CSV exported from Nightscout
    :param csv_file: a CSV file with columns dateString, type, sgv and/or mgb
    :return: a Pandas dataframe with columns ts, type, bg
    """
    entries_df = pd.read_csv(csv_file, parse_dates=["dateString"])
    # create a new 'bg' column that uses either 'sgv' or 'mbg' column, and turns into mmol/l
    entries_df["bg"] = (
            np.where(pd.notna(entries_df["sgv"]), entries_df["sgv"], entries_df["mbg"])
            / 18.0
    )
    # rename, reorder, drop columns
    entries_df = entries_df.rename(columns={"dateString": "ts"})
    entries_df = entries_df[["ts", "type", "bg"]]
    # sort by timestamp, since data from device may not be in chronological order
    entries_df = entries_df.sort_values(by=["ts"])
    return entries_df

df = pd.read_csv("~/Downloads/Transaction Report 010119 to 310519.csv", parse_dates=["Date"])
df = df.sort_values(by=["Date"])
#df = df[["Date", "Tariff"]]
#print(df)
print(df.info())

# filter out overnight
df = df[~df['Tariff'].isin(['105DA', '105M', '105U'])]

# add ticket duration
df['duration'] = df['Description.1'].str.extract('(1 Hour|2 Hour|4 Hour|All Day)', expand=True)

start_date = pd.Timestamp(2019, 2, 1)
end_date = pd.Timestamp(2019, 2, 2)
mask = (df['Date'] >= start_date) & (df['Date'] < end_date)
df2 = df[mask]
print(df2)

x = df.groupby(['duration']).size().reset_index(name='counts')
print(x)


def get_ticket_end(ticket_start, ticket_duration_str):
    if ticket_duration_str == '1 Hour':
        ticket_end = ticket_start + pd.Timedelta(hours=1)
    elif ticket_duration_str == '2 Hour':
        ticket_end = ticket_start + pd.Timedelta(hours=2)
    elif ticket_duration_str == '4 Hour':
        ticket_end = ticket_start + pd.Timedelta(hours=4)
    elif ticket_duration_str == 'All Day':
        ticket_end = ticket_start.replace(hour=18, minute=0)
        print(ticket_start, ticket_end)
    else:
        return None
    ticket_end_of_day = ticket_start.replace(hour=18, minute=0)
    if ticket_end > ticket_end_of_day:
        ticket_end = ticket_end_of_day
    return ticket_end


per_car_timeseries = []
for x in df2[["Date", "duration"]].values:
    ts = traces.TimeSeries(default=0)
    ticket_start = x[0]
    ticket_end = get_ticket_end(ticket_start, x[1])
    # count_at_start = ts[ticket_start] if ts[ticket_start] is not None else 0
    # count_at_end = ts[ticket_end] if ts[ticket_end] is not None else 0
    ts[ticket_start] = 1
    ts[ticket_end] = 0
    per_car_timeseries.append(ts)

ts = traces.TimeSeries.merge(per_car_timeseries, operation=sum, compact=True)

print(ts)

dist = ts.distribution(normalized=False)
print("mean", dist.mean())
print("max", dist.max())

x = ts.sample(
    sampling_period=datetime.timedelta(minutes=1),
    interpolate="previous"
)
print(x)
y = list(zip(*x))
print(list(zip(*x)))

idx = pd.DatetimeIndex(y[0])

series = pd.Series(y[1], idx)

print(series)

series.plot()

import matplotlib.pyplot as plt

plt.show()

# TODO
# turn x into pandas series and then plot DONE
# pull out ticket duration DONE
# find day with max
# what is average occupancy over opening times?
